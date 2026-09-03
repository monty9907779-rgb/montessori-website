/* زر واتساب عائم بحركات لفت انتباه — يحقن نفسه في أي صفحة عامة.
   الاستخدام: <script src="/assets/wa-fab.js" defer></script>
   متصل بقمع المبيعات والوكيل الذكي: أي ضغطة = محادثة جديدة. */
(function () {
  if (document.getElementById('mk-wa')) return;
  var WA = '966541558173';
  var MSG = 'السلام عليكم، أرغب بالاستفسار عن روضة كوكب الطفل الحر';

  var css = '' +
    '#mk-wa{position:fixed;bottom:22px;inset-inline-end:20px;z-index:9500;font-family:inherit}' +
    '#mk-wa-fab{position:relative;width:62px;height:62px;border-radius:50%;background:#25D366;' +
      'display:flex;align-items:center;justify-content:center;box-shadow:0 6px 22px rgba(0,0,0,.28);' +
      'cursor:pointer;text-decoration:none;animation:mk-wa-bounce 2.6s ease-in-out infinite}' +
    '#mk-wa-fab svg{width:34px;height:34px;fill:#fff}' +
    '#mk-wa-fab::before,#mk-wa-fab::after{content:"";position:absolute;inset:0;border-radius:50%;' +
      'background:#25D366;z-index:-1;animation:mk-wa-ring 2.2s ease-out infinite}' +
    '#mk-wa-fab::after{animation-delay:1.1s}' +
    '#mk-wa-badge{position:absolute;top:-4px;inset-inline-start:-4px;width:20px;height:20px;border-radius:50%;' +
      'background:#ef4444;color:#fff;font-size:12px;font-weight:800;display:flex;align-items:center;' +
      'justify-content:center;border:2px solid #fff;animation:mk-wa-pop 3s ease-in-out infinite}' +
    '#mk-wa-tip{position:absolute;bottom:8px;inset-inline-end:74px;background:#fff;color:#184e3e;' +
      'border-radius:14px;padding:10px 14px;box-shadow:0 6px 22px rgba(0,0,0,.18);font-size:13.5px;' +
      'font-weight:700;white-space:nowrap;opacity:0;transform:translateX(10px);pointer-events:none;' +
      'transition:opacity .35s,transform .35s;direction:rtl}' +
    '#mk-wa-tip.show{opacity:1;transform:translateX(0)}' +
    '#mk-wa-tip::after{content:"";position:absolute;top:50%;inset-inline-end:-6px;margin-top:-6px;' +
      'border:6px solid transparent;border-inline-start-color:#fff}' +
    '#mk-wa-tip b{color:#25D366}' +
    '@keyframes mk-wa-ring{0%{transform:scale(1);opacity:.55}100%{transform:scale(2.1);opacity:0}}' +
    '@keyframes mk-wa-bounce{0%,88%,100%{transform:translateY(0)}92%{transform:translateY(-9px)}96%{transform:translateY(-4px)}}' +
    '@keyframes mk-wa-pop{0%,70%,100%{transform:scale(1)}80%{transform:scale(1.25)}}' +
    '@media (prefers-reduced-motion:reduce){#mk-wa-fab,#mk-wa-fab::before,#mk-wa-fab::after,#mk-wa-badge{animation:none}}' +
    '@media (max-width:600px){#mk-wa{bottom:16px;inset-inline-end:14px}#mk-wa-fab{width:56px;height:56px}#mk-wa-fab svg{width:30px;height:30px}}';

  var st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  var path = 'M16 3C9 3 3.5 8.5 3.5 15.5c0 2.4.7 4.6 1.8 6.5L3 29l7.2-2.2c1.8 1 3.9 1.6 6 1.6 7 0 12.5-5.5 12.5-12.5S23 3 16 3zm0 22.7c-1.9 0-3.7-.5-5.2-1.4l-.4-.2-4.3 1.3 1.3-4.2-.2-.4c-1-1.6-1.5-3.4-1.5-5.3 0-5.6 4.6-10.2 10.3-10.2S26.3 9.9 26.3 15.5 21.7 25.7 16 25.7zm5.7-7.7c-.3-.2-1.8-.9-2.1-1s-.5-.2-.7.2-.8 1-.9 1.2-.3.2-.6.1c-1.7-.8-2.8-1.5-3.9-3.4-.3-.5.3-.5.8-1.5.1-.2 0-.4 0-.5s-.7-1.7-1-2.3c-.3-.6-.5-.5-.7-.5h-.6c-.2 0-.5.1-.8.4-.3.3-1 1-1 2.5s1.1 2.9 1.2 3.1c.2.2 2.1 3.3 5.2 4.6 2.9 1.2 2.9.8 3.5.8.5-.1 1.8-.7 2-1.4.2-.7.2-1.3.2-1.4-.1-.2-.3-.2-.6-.4z';
  var href = 'https://wa.me/' + WA + '?text=' + encodeURIComponent(MSG);
  var wrap = document.createElement('div');
  wrap.id = 'mk-wa';
  wrap.innerHTML =
    '<div id="mk-wa-tip">💬 عندك سؤال؟ <b>راسلينا الآن</b></div>' +
    '<a id="mk-wa-fab" aria-label="تواصلي معنا على واتساب" target="_blank" rel="noopener" href="' + href + '">' +
      '<span id="mk-wa-badge">1</span>' +
      '<svg viewBox="0 0 32 32"><path d="' + path + '"/></svg>' +
    '</a>';
  document.body.appendChild(wrap);

  var tip = document.getElementById('mk-wa-tip');
  function flash() { if (!tip) return; tip.classList.add('show'); setTimeout(function () { tip.classList.remove('show'); }, 4500); }
  setTimeout(flash, 3500); setInterval(flash, 18000);

  var fab = document.getElementById('mk-wa-fab');
  if (fab) fab.addEventListener('click', function () {
    try { if (window.gtag) gtag('event', 'whatsapp_click', { event_category: 'lead' }); } catch (e) {}
  });
})();
