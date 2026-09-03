/* حضانة مونتيسوري — مُثبّت ذكي (بديل أفضل من مشاركة الصفحة)
   • أندرويد: زر «ثبّت التطبيق» بضغطة واحدة (native prompt) — بلا شير
   • آيفون: بانر إرشادي بسهم متحرّك نحو زر المشاركة (آبل لا تتيح تثبيتاً برمجياً)
   يُحمَّل على صفحات الأدوار وصفحة /app. لا يظهر شيء لو التطبيق مثبّت أصلاً. */
(function () {
  var ua = navigator.userAgent || '';
  var isIOS = /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var standalone = window.matchMedia('(display-mode: standalone)').matches ||
    window.navigator.standalone === true;
  var qs = location.search || '';
  var forceIOS = /[?&]install=ios/.test(qs);
  var forceAndroid = /[?&]install=android/.test(qs);

  if (standalone) return; // مثبّت بالفعل — لا نزعج المستخدم

  // ---------- أندرويد: زر تثبيت بضغطة واحدة ----------
  var deferred = null;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault();
    deferred = e;
    androidBtn();
  });
  function androidBtn() {
    if (document.getElementById('mk-install-btn')) return;
    var b = document.createElement('button');
    b.id = 'mk-install-btn';
    b.type = 'button';
    b.innerHTML = '📲 ثبّت التطبيق';
    b.style.cssText = 'position:fixed;inset-inline-start:16px;inset-block-end:16px;z-index:99999;' +
      'background:#184e3e;color:#fff;border:0;border-radius:14px;padding:13px 20px;font-size:15px;' +
      'font-weight:800;box-shadow:0 8px 24px rgba(24,78,62,.4);font-family:inherit;cursor:pointer;' +
      'animation:mk-pop .3s ease';
    b.onclick = function () {
      if (!deferred) return;
      deferred.prompt();
      deferred.userChoice.finally(function () { deferred = null; b.remove(); });
    };
    document.body.appendChild(b);
  }

  // ---------- آيفون: بانر إرشادي بسهم ----------
  function iosBanner() {
    if (document.getElementById('mk-ios-banner')) return;
    var w = document.createElement('div');
    w.id = 'mk-ios-banner';
    w.style.cssText = 'position:fixed;inset-inline:12px;inset-block-end:14px;z-index:99999;background:#fff;' +
      'border:1px solid #eadfce;border-radius:18px;padding:14px 16px;box-shadow:0 12px 34px rgba(0,0,0,.2);' +
      'font-family:inherit;direction:rtl;animation:mk-pop .35s ease';
    w.innerHTML =
      '<div style="display:flex;gap:11px;align-items:center">' +
        '<img src="/apple-touch-icon.png" alt="" style="width:46px;height:46px;border-radius:12px;flex:none"/>' +
        '<div style="flex:1;font-size:13.5px;color:#22302a;line-height:1.7">لتثبيت التطبيق على آيفون: اضغط ' +
          '<b>زر المشاركة</b> <span style="display:inline-block">􀈂</span> بالأسفل ثم اختر ' +
          '<b>«إضافة إلى الشاشة الرئيسية»</b>.</div>' +
        '<button id="mk-ios-x" aria-label="إغلاق" style="border:0;background:#f4ecdd;color:#79857c;' +
          'border-radius:10px;width:30px;height:30px;font-size:15px;flex:none;cursor:pointer">✕</button>' +
      '</div>' +
      '<div style="position:absolute;inset-inline-start:50%;inset-block-end:-15px;transform:translateX(50%);' +
        'font-size:22px;animation:mk-bounce 1s infinite" aria-hidden="true">⬇️</div>';
    document.body.appendChild(w);
    document.getElementById('mk-ios-x').onclick = function () {
      w.remove();
      try { localStorage.setItem('mk_ios_hint', '1'); } catch (e) {}
    };
  }

  var st = document.createElement('style');
  st.textContent =
    '@keyframes mk-bounce{0%,100%{transform:translateX(50%) translateY(0)}50%{transform:translateX(50%) translateY(7px)}}' +
    '@keyframes mk-pop{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}';
  document.head.appendChild(st);

  if ((isIOS || forceIOS) && !forceAndroid) {
    var seen = false;
    try { seen = !!localStorage.getItem('mk_ios_hint'); } catch (e) {}
    if (forceIOS || !seen) setTimeout(iosBanner, 600);
  }
})();
