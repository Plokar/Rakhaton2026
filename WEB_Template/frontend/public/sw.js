/* MDTcore service worker (T-383): instalace na plochu, čtení dnešního zasedání bez signálu, push oznámení.
 *
 * Zásady (osobní údaje pacientů v telefonu):
 * - API se do mezipaměti NEUKLÁDÁ samo. Jen když lékař na stránce „Živě na MDT“ výslovně zapne „Uložit pro čtení
 *   bez signálu“, uloží se odpovědi pro pacienty dnešního zasedání (`mdt-offline`).
 * - Uložená data platí 12 hodin, pak se smažou; odhlášení je smaže hned (zpráva `clear`).
 * - Bez signálu se uložená odpověď vrátí s hlavičkou `X-MDT-Offline: 1`, aby UI ukázalo „bez signálu“.
 */
const SHELL = 'mdt-shell-v1';
const OFFLINE = 'mdt-offline';
const MAX_AGE_MS = 12 * 60 * 60 * 1000;

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(['/offline.html', '/icon-192.png'])).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(keys.filter((k) => k.startsWith('mdt-shell-') && k !== SHELL).map((k) => caches.delete(k)));
      await expireOffline();
      await self.clients.claim();
    })(),
  );
});

async function expireOffline() {
  const cache = await caches.open(OFFLINE);
  const stamp = await cache.match('/__mdt_offline_saved_at');
  if (stamp && Date.now() - Number(await stamp.text()) > MAX_AGE_MS) await caches.delete(OFFLINE);
}

self.addEventListener('message', (event) => {
  const data = event.data || {};
  if (data.type === 'clear') {
    event.waitUntil(caches.delete(OFFLINE));
  } else if (data.type === 'save' && Array.isArray(data.urls)) {
    // stránka posílá jen adresy API pacientů dnešního zasedání; ukládá se odpověď se session cookie lékaře
    event.waitUntil(
      (async () => {
        await caches.delete(OFFLINE);
        const cache = await caches.open(OFFLINE);
        let saved = 0;
        for (const url of data.urls) {
          try {
            const response = await fetch(url, { credentials: 'include' });
            if (response.ok) {
              await cache.put(url, response);
              saved += 1;
            }
          } catch {
            /* bez signálu nic */
          }
        }
        await cache.put('/__mdt_offline_saved_at', new Response(String(Date.now())));
        if (event.source) event.source.postMessage({ type: 'saved', saved, total: data.urls.length });
      })(),
    );
  }
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  // statické soubory Next.js: nejdřív mezipaměť (mají v názvu otisk obsahu)
  if (url.pathname.startsWith('/_next/static/')) {
    event.respondWith(
      caches.open(SHELL).then(async (cache) => {
        const hit = await cache.match(request);
        if (hit) return hit;
        const response = await fetch(request);
        if (response.ok) cache.put(request, response.clone());
        return response;
      }),
    );
    return;
  }

  // API: vždy síť; bez signálu jen to, co lékař výslovně uložil (stream zasedání nikdy)
  if (url.pathname.startsWith('/api/')) {
    if (url.pathname.endsWith('/stream/')) return;
    event.respondWith(
      fetch(request).catch(async () => {
        await expireOffline();
        const cache = await caches.open(OFFLINE);
        const hit = await cache.match(url.pathname + url.search);
        if (!hit) throw new Error('offline');
        const body = await hit.blob();
        const headers = new Headers(hit.headers);
        headers.set('X-MDT-Offline', '1');
        return new Response(body, { status: hit.status, headers });
      }),
    );
    return;
  }

  // stránky: síť, bez signálu poslední stažená verze, jinak stránka „bez signálu“
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok && url.pathname.startsWith('/dashboard/live')) {
            const copy = response.clone();
            caches.open(SHELL).then((cache) => cache.put(url.pathname, copy));
          }
          return response;
        })
        .catch(async () => (await caches.match(url.pathname, { cacheName: SHELL })) || caches.match('/offline.html')),
    );
  }
});

// ── Push oznámení (T-383): „váš pacient je další / na projektoru“ ───────────────────────────────────────────────
self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch {
    data = { title: 'MDTcore', body: event.data ? event.data.text() : '' };
  }
  event.waitUntil(
    self.registration.showNotification(data.title || 'MDTcore', {
      body: data.body || '',
      icon: '/icon-192.png',
      badge: '/icon-192.png',
      tag: data.tag || 'mdt',
      data: { url: data.url || '/dashboard/live' },
    }),
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.url) || '/dashboard/live';
  event.waitUntil(
    (async () => {
      const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true });
      for (const client of windows) {
        if ('focus' in client) {
          await client.navigate(target);
          return client.focus();
        }
      }
      return self.clients.openWindow(target);
    })(),
  );
});
