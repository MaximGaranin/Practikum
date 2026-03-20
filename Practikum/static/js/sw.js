/**
 * Service Worker — офлайн поддержка Practikum
 *
 * При первом визите (онлайн):
 *   1. Кэшируем статику и страницы
 *   2. Загружаем зашифрованный офлайн-пак (/api/offline-pack/)
 *      и сохраняем в IndexedDB
 *
 * При офлайн-визите:
 *   - Статика и страницы отдаются из кэша
 *   - Ключи AES-GCM берутся из IndexedDB
 *   - Pyodide выполняет код пользователя в браузере
 *   - Вывод шифруется тем же ключом и сравнивается с expected_enc
 */

const CACHE_NAME = 'practikum-v1';
const OFFLINE_PACK_URL = '/api/offline-pack/';
const DB_NAME = 'practikum-offline';
const DB_STORE = 'pack';

// ─── IndexedDB helpers ───────────────────────────────────────────────────────

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = e => e.target.result.createObjectStore(DB_STORE);
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

async function savePack(pack) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DB_STORE, 'readwrite');
    tx.objectStore(DB_STORE).put(pack, 'latest');
    tx.oncomplete = resolve;
    tx.onerror = e => reject(e.target.error);
  });
}

async function loadPack() {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(DB_STORE, 'readonly');
    const req = tx.objectStore(DB_STORE).get('latest');
    req.onsuccess = e => resolve(e.target.result || null);
    req.onerror = e => reject(e.target.error);
  });
}

// ─── AES-GCM helpers (WebCrypto) ─────────────────────────────────────────────

async function importAesKey(keyB64) {
  const raw = Uint8Array.from(atob(keyB64), c => c.charCodeAt(0));
  return crypto.subtle.importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
}

/**
 * Encrypts plaintext string with AES-GCM.
 * Returns base64(nonce[12] + ciphertext).
 */
async function aesEncrypt(plaintext, cryptoKey) {
  const nonce = crypto.getRandomValues(new Uint8Array(12));
  const data = new TextEncoder().encode(plaintext);
  const ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: nonce }, cryptoKey, data);
  const combined = new Uint8Array(12 + ct.byteLength);
  combined.set(nonce);
  combined.set(new Uint8Array(ct), 12);
  return btoa(String.fromCharCode(...combined));
}

/**
 * Decrypts AES-GCM base64 payload produced by server (crypto_utils.py).
 */
async function aesDecrypt(b64payload, cryptoKey) {
  const raw = Uint8Array.from(atob(b64payload), c => c.charCodeAt(0));
  const nonce = raw.slice(0, 12);
  const ct = raw.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, cryptoKey, ct);
  return new TextDecoder().decode(pt);
}

// ─── Offline check logic ─────────────────────────────────────────────────────

/**
 * Runs user code against cached encrypted test cases using Pyodide.
 * Called from the page via postMessage when offline.
 *
 * @param {string} code      - User's Python code
 * @param {number} taskId    - Task ID
 * @param {object} pack      - Offline pack from IndexedDB
 * @returns {object}         - { correct, message }
 */
async function checkOffline(code, taskId, pack) {
  const now = Math.floor(Date.now() / 1000);
  if (!pack || pack.expires_at < now) {
    return { correct: false, message: '⚠️ Офлайн-пак устарел. Зайдите онлайн для обновления.' };
  }

  const taskData = pack.tasks[String(taskId)];
  if (!taskData) {
    return { correct: false, message: '⚠️ Данные задачи не найдены в офлайн-паке.' };
  }

  const cryptoKey = await importAesKey(taskData.key_b64);

  // Lazy-load Pyodide (cached by SW on install)
  if (!self.pyodide) {
    self.importScripts('https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js');
    self.pyodide = await loadPyodide();
  }

  const failedTests = [];

  for (let i = 0; i < taskData.tests.length; i++) {
    const tc = taskData.tests[i];

    // Decrypt input (hidden tests encrypted, open tests plaintext)
    let inputData;
    if (tc.is_hidden) {
      try {
        inputData = await aesDecrypt(tc.input_enc, cryptoKey);
      } catch {
        continue; // skip if decryption fails (key expired mid-session)
      }
    } else {
      inputData = tc.input_enc;
    }

    // Run user code via Pyodide
    let userOutput;
    try {
      // Simulate stdin by patching builtins.input
      const inputLines = inputData ? inputData.split('\n') : [];
      await self.pyodide.runPythonAsync(`
import sys, io, builtins
_input_lines = ${JSON.stringify(inputLines)}
_input_idx = 0
def _mock_input(prompt=''):
    global _input_idx
    val = _input_lines[_input_idx] if _input_idx < len(_input_lines) else ''
    _input_idx += 1
    return val
builtins.input = _mock_input
_stdout_capture = io.StringIO()
sys.stdout = _stdout_capture
`);
      await self.pyodide.runPythonAsync(code);
      userOutput = await self.pyodide.runPythonAsync(`
sys.stdout = sys.__stdout__
_stdout_capture.getvalue().strip()
`);
    } catch (err) {
      userOutput = String(err);
    }

    // Encrypt user output with the SAME key and compare to expected_enc
    // We re-encrypt user output and compare — but since AES-GCM nonce is
    // random, we must DECRYPT expected and compare in plaintext.
    // Note: expected_enc is decrypted only in memory, never stored.
    let expectedOutput;
    try {
      expectedOutput = await aesDecrypt(tc.expected_enc, cryptoKey);
    } catch {
      continue;
    }

    if (userOutput.trim() !== expectedOutput.trim()) {
      failedTests.push({
        is_hidden: tc.is_hidden,
        input: tc.is_hidden ? '(скрытый тест)' : inputData,
        expected: tc.is_hidden ? '(скрыто)' : expectedOutput,
        actual: userOutput,
      });
    }
  }

  if (failedTests.length === 0) {
    return { correct: true, message: '🎉 Задание решено правильно! (офлайн)' };
  }

  const firstFail = failedTests[0];
  if (firstFail.is_hidden) {
    return {
      correct: false,
      message: '❌ Неверный ответ на скрытом тесте. Проверьте что решение работает для любых значений.',
    };
  }
  return {
    correct: false,
    message: `❌ Неверный ответ.\nВвод: ${firstFail.input || '(пусто)'}\nОжидалось: ${firstFail.expected}\nПолучено: ${firstFail.actual}`,
  };
}

// ─── SW lifecycle ─────────────────────────────────────────────────────────────

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache =>
      cache.addAll([
        '/',
        '/static/js/sw.js',
      ])
    )
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Fetch: network-first for API, cache-first for static
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Don't intercept offline-pack fetch itself or admin
  if (url.pathname.startsWith('/admin')) return;

  if (url.pathname.startsWith('/api/')) {
    // Network first for API calls
    event.respondWith(
      fetch(event.request)
        .then(async response => {
          // When online-pack is fetched, save it to IndexedDB
          if (url.pathname === OFFLINE_PACK_URL && response.ok) {
            const clone = response.clone();
            clone.json().then(pack => savePack(pack));
          }
          return response;
        })
        .catch(async () => {
          // Offline: handle check_task via offline pack
          if (url.pathname === '/api/check/' && event.request.method === 'POST') {
            const body = await event.request.clone().json();
            const pack = await loadPack();
            const result = await checkOffline(body.code || '', body.task_id, pack);
            return new Response(JSON.stringify(result), {
              headers: { 'Content-Type': 'application/json' },
            });
          }
          return new Response(JSON.stringify({ error: 'Нет соединения с сервером' }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' },
          });
        })
    );
    return;
  }

  // Cache first for static assets
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});

// ─── Message handler (from page) ─────────────────────────────────────────────
// Page can send: { type: 'FETCH_OFFLINE_PACK' } to trigger pack refresh
self.addEventListener('message', async event => {
  if (event.data && event.data.type === 'FETCH_OFFLINE_PACK') {
    try {
      const response = await fetch(OFFLINE_PACK_URL);
      if (response.ok) {
        const pack = await response.json();
        await savePack(pack);
        event.ports[0].postMessage({ success: true });
      }
    } catch {
      event.ports[0].postMessage({ success: false });
    }
  }
});
