// روضة كوكب الطفل الحر — service worker خفيف للتثبيت والسرعة والإشعارات
const CACHE = 'mk-shell-v24';
const SHELL = [
  '/',
  '/offline.html',
  '/app/',
  '/login/',
  '/dashboard/',
  '/dashboard/index.html',
  '/classes/',
  '/classes/index.html',
  '/whatsapp/',
  '/assets/app-admin.css?v=4',
  '/assets/fonts.css?v=2',
  '/assets/app.js?v=49',
  '/assets/bot.js',
  '/assets/install.js?v=3',
  '/assets/whatsapp-admin.css?v=1',
  '/assets/whatsapp-admin.js?v=1',
  '/dashboard/dashboard-inline-1.js?v=1',
  '/dashboard/dashboard-inline-2.js?v=2',
  '/manifest.webmanifest',
  '/logo.png',
  '/apple-touch-icon.png',
  '/icon-192.png',
  '/icon-512.png',
  '/icon-maskable-512.png'
];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();

});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.map((k) => caches.delete(k))).then(() => self.registration.unregister())));
  self.clients.claim();

});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;

  if (e.request.mode === 'navigate') {
    e.respondWith(
      fetch(e.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(e.request, copy)).catch(() => {});
          return response;
        })
        .catch(() => caches.match(e.request).then((r) => r || caches.match('/login/')).then((r) => r || caches.match('/offline.html')))
    );
    return;
  }

  if (url.pathname === '/assets/app.js' || url.pathname === '/assets/install.js' || url.pathname === '/sw.js') {
    e.respondWith(
      fetch(e.request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(url.pathname, copy)).catch(() => {});
        return response;
      }).catch(() => caches.match(e.request).then((r) => r || caches.match(url.pathname)))
    );
    return;
  }

  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));

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
