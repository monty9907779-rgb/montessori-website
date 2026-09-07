// روضة كوكب الطفل الحر — service worker خفيف للتثبيت والسرعة والإشعارات
const CACHE = 'mk-shell-v25';
self.addEventListener('install', (e) => {
  // Never pre-cache authenticated pages or API responses.
  e.waitUntil(caches.open(CACHE).then((c) => c.add('/offline.html')).then(() => self.skipWaiting()));

});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k.startsWith('mk-shell-') && k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim()));

});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((response) => {
          return response;
        })
        .catch(() => caches.match('/offline.html'))
    );
    return;
  }

  // Revalidate even old version URLs retained by an already-open page.
  if (/\.(?:css|js)$/.test(url.pathname)) {
    e.respondWith(fetch(e.request, { cache: 'no-cache' }));
  }

});

self.addEventListener('push', (e) => {
  let d = {};
  try { d = e.data ? e.data.json() : {}; } catch (_) { d = { body: e.data && e.data.text() }; }
  const title = d.title || 'روضة كوكب الطفل الحر';
  e.waitUntil(clients.matchAll({ type: 'window', includeUncontrolled: true })
    .then((ls) => ls.forEach((c) => { try { c.postMessage({ type: 'push', payload: d }); } catch (_) {} }))
    .catch(() => {}));
  e.waitUntil(self.registration.showNotification(title, {
    body: d.body || '',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    dir: 'rtl',
    lang: 'ar',
    tag: (d.data && d.data.conversationId) ? 'conv-' + d.data.conversationId : undefined,
    renotify: !!(d.data && d.data.conversationId),
    data: d.data || {},
  }));

});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const conv = e.notification.data && e.notification.data.conversationId;
  const target = conv ? '/login/?conv=' + encodeURIComponent(conv) + '&src=push' : '/login/?src=push';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((list) => {
      for (const c of list) {
        if (new URL(c.url).origin === location.origin && 'focus' in c) {
          if ('navigate' in c) { c.navigate(target).catch(() => {}); }
          return c.focus();
        }
      }
      return clients.openWindow(target);
    })
  );

});
