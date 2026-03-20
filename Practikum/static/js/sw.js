/**
 * Service Worker — офлайн поддержка Practikum
 *
 * При первом визите (онлайн):
 *   1. Кэшируем статику, страницы и Pyodide (~10MB)
 *   2. Загружаем зашифрованный офлайн-пак (/api/offline-pack/)
 *      и сохраняем в IndexedDB
 *
 * При офлайн-визите:
 *   - Статика и страницы отдаются из кэша
 *   - Pyodide грузится из кэша (не из CDN)
 *   - Ключи AES-GCM берутся из IndexedDB
 *   - Pyodide выполняет код пользователя в браузере
 *   - Вывод сравнивается с расшифрованным expected_enc
 */

const CACHE_NAME = 'practikum-v2';
const OFFLINE_PACK_URL = '/api/offline-pack/';
const DB_NAME = 'practikum-offline';
const DB_STORE = 'pack';

const PYODIDE_BASE = 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/';

// Файлы Pyodide которые нужно закэшировать для офлайн-работы
const PYODIDE_FILES = [
  'pyodide.js',
  'pyodide.asm.wasm',
  'pyodide.asm.js',
  'python_stdlib.zip',
];

// ─── IndexedDB helpers ────────────────────────────────────────────────────────

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

// ─── AES-GCM helpers (WebCrypto) ──────────────────────────────────────────────

async function importAesKey(keyB64) {
  const raw = Uint8Array.from(atob(keyB64), c => c.charCodeAt(0));
  return crypto.subtle.importKey('raw', raw, { name: 'AES-GCM' }, false, ['encrypt', 'decrypt']);
}

async function aesDecrypt(b64payload, cryptoKey) {
  const raw = Uint8Array.from(atob(b64payload), c => c.charCodeAt(0));
  const nonce = raw.slice(0, 12);
  const ct = raw.slice(12);
  const pt = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, cryptoKey, ct);
  return new TextDecoder().decode(pt);
}

// ─── Offline check logic ──────────────────────────────────────────────────────

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

  // Загружаем Pyodide из кэша SW (не с CDN)
  if (!self.pyodide) {
    try {
      self.importScripts(PYODIDE_BASE + 'pyodide.js');
      self.pyodide = await loadPyodide({ indexURL: PYODIDE_BASE });
    } catch (err) {
      return {
        correct: false,
        message: '⚠️ Pyodide не загружен. Откройте сайт онлайн хотя бы один раз для кэширования.',
      };
    }
  }

  const failedTests = [];

  for (let i = 0; i < taskData.tests.length; i++) {
    const tc = taskData.tests[i];

    let inputData;
    if (tc.is_hidden) {
      try {
        inputData = await aesDecrypt(tc.input_enc, cryptoKey);
      } catch {
        continue;
      }
    } else {
      inputData = tc.input_enc;
    }

    let userOutput;
    try {
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
    (async () => {
      const cache = await caches.open(CACHE_NAME);

      // Кэшируем основные страницы
      await cache.addAll(['/']);

      // Кэшируем Pyodide — по одному файлу, чтобы не падать если один недоступен
      for (const file of PYODIDE_FILES) {
        try {
          await cache.add(PYODIDE_BASE + file);
          console.log('[SW] Cached Pyodide:', file);
        } catch (e) {
          console.warn('[SW] Failed to cache Pyodide file:', file, e);
        }
      }
    })()
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

// Fetch: Pyodide CDN — из кэша, API — network-first, статика — cache-first
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith('/admin')) return;

  // Pyodide файлы — всегда из кэша если есть
  if (url.href.startsWith(PYODIDE_BASE)) {
    event.respondWith(
      caches.match(event.request).then(cached =>
        cached || fetch(event.request).then(response => {
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
      )
    );
    return;
  }

  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(async response => {
          // Сохраняем офлайн-пак в IndexedDB при успешном получении
          if (url.pathname === OFFLINE_PACK_URL && response.ok) {
            const clone = response.clone();
            clone.json().then(pack => savePack(pack)).catch(() => {});
          }
          return response;
        })
        .catch(async () => {
          // Офлайн: /api/offline-pack/ — отдаём закэшированный пак из IndexedDB
          if (url.pathname === OFFLINE_PACK_URL) {
            const pack = await loadPack();
            if (pack) {
              return new Response(JSON.stringify(pack), {
                headers: { 'Content-Type': 'application/json' },
              });
            }
            return new Response(JSON.stringify({ error: 'Офлайн-пак не найден. Зайдите онлайн для загрузки.' }), {
              status: 503,
              headers: { 'Content-Type': 'application/json' },
            });
          }

          // Офлайн: /api/check/
          if (url.pathname === '/api/check/' && event.request.method === 'POST') {
            const body = await event.request.clone().json();
            const pack = await loadPack();
            const result = await checkOffline(body.code || '', body.task_id, pack);
            return new Response(JSON.stringify(result), {
              headers: { 'Content-Type': 'application/json' },
            });
          }

          // Офлайн: /api/analyze/
          if (url.pathname === '/api/analyze/' && event.request.method === 'POST') {
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

  // Статика — cache-first
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

// ─── Message handler ──────────────────────────────────────────────────────────
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
