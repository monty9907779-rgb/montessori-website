// حضانة مونتيسوري — service worker خفيف (يفعّل التثبيت على أندرويد)
const CACHE = 'mk-shell-v1';
const SHELL = ['/app/', '/assets/app.css?v=10', '/assets/fonts.css?v=2', '/logo.png'];
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(SHELL)).catch(() => {}));
  self.skipWaiting();
});
self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url);
  // لا نتدخّل أبداً في نداءات أودو أو أي دومين آخر أو الطلبات غير GET
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  // الصفحات: الشبكة أولاً ثم الكاش (عشان البيانات دايماً حديثة)
  if (e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request).then((r) => r || caches.match('/app/'))));
    return;
  }
  // الأصول الثابتة: كاش أولاً
  e.respondWith(caches.match(e.request).then((r) => r || fetch(e.request)));
});
