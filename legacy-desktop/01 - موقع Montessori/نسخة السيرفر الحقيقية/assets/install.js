/* روضة كوكب الطفل الحر — مثبت PWA موحد للاندرويد والآيفون */
(function () {
  return;

  var ua = navigator.userAgent || '';
  var isIOS = /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isAndroid = /Android/i.test(ua);
  var standalone = window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  var qs = location.search || '';
  var forceIOS = /[?&]install=ios/.test(qs);
  var forceAndroid = /[?&]install=android/.test(qs);
  var deferred = null;

  /* Register from every public page so a shared homepage can be installed too. */
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
  }

  if (standalone) return;

  function addStyle() {
    if (document.getElementById('mk-install-style')) return;
    var st = document.createElement('style');
    st.id = 'mk-install-style';
    st.textContent =
      '#mk-install-btn,#mk-install-fallback{position:fixed;inset-inline-start:14px;inset-block-end:calc(14px + env(safe-area-inset-bottom));z-index:99999;font-family:inherit;direction:rtl}' +
      '#mk-install-btn{background:#184e3e;color:#fff;border:0;border-radius:14px;padding:13px 19px;font-size:15px;font-weight:800;box-shadow:0 10px 26px rgba(24,78,62,.34);cursor:pointer;touch-action:manipulation}' +
      '#mk-install-fallback,#mk-ios-banner{max-width:min(420px,calc(100vw - 24px));background:#fff;color:#22302a;border:1px solid #eadfce;border-radius:16px;box-shadow:0 12px 34px rgba(0,0,0,.18)}' +
      '#mk-install-fallback{padding:13px 15px;font-size:13.5px;line-height:1.7}' +
      '#mk-ios-banner{position:fixed;inset-inline:12px;inset-block-end:calc(14px + env(safe-area-inset-bottom));z-index:99999;padding:14px 15px;font-family:inherit;direction:rtl}' +
      '.mk-install-row{display:flex;gap:11px;align-items:center}.mk-install-icon{width:44px;height:44px;border-radius:12px;flex:none}.mk-install-text{flex:1;font-size:13.5px;line-height:1.7}' +
      '.mk-install-x{border:0;background:#f4ecdd;color:#59655d;border-radius:10px;width:30px;height:30px;font-size:16px;flex:none;cursor:pointer}' +
      '@keyframes mk-pop{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}' +
      '#mk-install-btn,#mk-install-fallback,#mk-ios-banner{animation:mk-pop .28s ease}';
    document.head.appendChild(st);
  }

  function remove(id) {
    var el = document.getElementById(id);
    if (el) el.remove();
  }

  function androidButton() {
    addStyle();
    remove('mk-install-fallback');
    var b = document.getElementById('mk-install-hero') || document.getElementById('mk-install-btn');
    if (!b) {
      b = document.createElement('button');
      b.id = 'mk-install-btn';
      b.type = 'button';
      document.body.appendChild(b);
    }
    b.textContent = '📲 ثبّت التطبيق على جوالك';
    b.style.display = 'block';
    b.setAttribute('aria-live', 'polite');
    b.onclick = function () {
      if (!deferred) {
        androidFallback();
        return;
      }
      deferred.prompt();
      deferred.userChoice.finally(function () {
        deferred = null;
        if (b.id === 'mk-install-btn') b.remove();
        else b.style.display = 'none';
      });
    };
  }

  function androidFallback() {
    if ((!isAndroid && !forceAndroid) || deferred || document.getElementById('mk-install-fallback')) return;
    addStyle();
    var box = document.createElement('div');
    box.id = 'mk-install-fallback';
    box.innerHTML = '<div class="mk-install-row"><div class="mk-install-text">من Chrome اضغط قائمة الثلاث نقاط، ثم اختر <b>تثبيت التطبيق</b> أو <b>إضافة إلى الشاشة الرئيسية</b>.</div><button class="mk-install-x" type="button" aria-label="إغلاق">×</button></div>';
    document.body.appendChild(box);
    box.querySelector('.mk-install-x').onclick = function () { box.remove(); };
  }

  function iosBanner() {
    if (document.getElementById('mk-ios-banner')) return;
    addStyle();
    var w = document.createElement('div');
    w.id = 'mk-ios-banner';
    w.innerHTML =
      '<div class="mk-install-row">' +
        '<img class="mk-install-icon" src="/apple-touch-icon.png" alt=""/>' +
        '<div class="mk-install-text">لتثبيت التطبيق على آيفون: افتح الرابط في <b>Safari</b>، اضغط <b>زر المشاركة</b>، ثم اختر <b>إضافة إلى الشاشة الرئيسية</b>.</div>' +
        '<button id="mk-ios-x" class="mk-install-x" type="button" aria-label="إغلاق">×</button>' +
      '</div>';
    document.body.appendChild(w);
    document.getElementById('mk-ios-x').onclick = function () {
      w.remove();
      try { localStorage.setItem('mk_ios_hint', '1'); } catch (e) {}
    };
  }

  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
    if (!isIOS) androidButton();
  });

  window.addEventListener('appinstalled', function () {
    deferred = null;
    remove('mk-install-btn');
    var hero = document.getElementById('mk-install-hero');
    if (hero) hero.style.display = 'none';
    remove('mk-install-fallback');
  });

  if ((isIOS || forceIOS) && !forceAndroid) {
    var seen = false;
    try { seen = !!localStorage.getItem('mk_ios_hint'); } catch (e) {}
    if (forceIOS || !seen) setTimeout(iosBanner, 650);
  } else if (isAndroid || forceAndroid) {
    setTimeout(androidFallback, 2200);
  }
})();
