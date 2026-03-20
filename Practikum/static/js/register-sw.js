/**
 * Registers the Service Worker and triggers offline pack fetch.
 * Include this script in base.html.
 */
(async function () {
  if (!('serviceWorker' in navigator)) return;

  try {
    const reg = await navigator.serviceWorker.register('/static/js/sw.js', { scope: '/' });
    console.log('[SW] Registered', reg.scope);

    // Wait for SW to be active, then request offline pack
    const sw = reg.active || await new Promise(resolve => {
      reg.addEventListener('updatefound', () => {
        const newSw = reg.installing;
        newSw.addEventListener('statechange', () => {
          if (newSw.state === 'activated') resolve(newSw);
        });
      });
    });

    // Fetch and cache the offline pack
    const channel = new MessageChannel();
    channel.port1.onmessage = e => {
      if (e.data.success) {
        console.log('[SW] Offline pack cached successfully');
      }
    };
    navigator.serviceWorker.controller?.postMessage(
      { type: 'FETCH_OFFLINE_PACK' },
      [channel.port2]
    );
  } catch (err) {
    console.warn('[SW] Registration failed:', err);
  }
})();
