/* ============================================================================
   Home page runtime for / and /en/ (loaded with `defer`, no inline handlers).
   Self-contained: the home page no longer loads app.js.
   1. applies the non-blocking stylesheet   5. gallery (Odoo feed, lazy)
   2. GA4 (lazy) + conversion events        6. Google reviews (lazy)
   3. drawer + back-to-top                  7. parents form (validation + POST)
   4. lightbox                              8. owner-only live visitor counter
   ========================================================================== */
(function () {
  'use strict';
  var doc = document, root = doc.documentElement;
  var EN = (root.lang || '').toLowerCase().indexOf('en') === 0;
  var T = EN ? {
    galEmpty: 'Photos are on their way. Follow us on Instagram for the latest moments.',
    galAlt: ['Children playing at the nursery', 'A hands-on activity', 'A celebration at the nursery', 'Children at work',
      'Outdoor play', 'An art moment', 'Morning circle', 'The prepared classroom'],
    galOpen: 'Open photo', lbLabel: 'Photo viewer', lbClose: 'Close', lbPrev: 'Previous photo', lbNext: 'Next photo',
    reviews: ' reviews on Google', readAll: 'Read all reviews on Google', stars: ' out of 5',
    reqChild: 'Enter your child’s name.', badEmail: 'Enter a valid email, like name@example.com',
    badPhone: 'Use the format 05xxxxxxxx', fix: 'Please fix the highlighted fields.',
    sending: 'Sending…', ok: 'Thank you. We received the details for ', okEnrolled: ' is already enrolled with us; the team will link your account.',
    okNext: 'Next: sign in with Google using ', okNext2: '.', signIn: 'Sign in with Google',
    fail: 'We could not send the form right now. ', failWa: 'Message us on WhatsApp instead', waText: 'Hello, I would like to register my child at the nursery.'
  } : {
    galEmpty: 'الصور في الطريق. تابعنا على إنستغرام لأحدث اللحظات.',
    galAlt: ['أطفال يلعبون في الروضة', 'نشاط عملي للأطفال', 'مناسبة في الروضة', 'طفل يعمل بتركيز على نشاطه',
      'لعب في الهواء الطلق', 'لحظة فنية', 'حلقة الصباح', 'الفصل المُعدّ'],
    galOpen: 'افتح الصورة', lbLabel: 'عارض الصور', lbClose: 'إغلاق', lbPrev: 'الصورة السابقة', lbNext: 'الصورة التالية',
    reviews: ' مراجعة على Google', readAll: 'اقرأ كل المراجعات على Google', stars: ' من ٥',
    reqChild: 'اكتب اسم الطفل.', badEmail: 'اكتب بريدًا إلكترونيًا صحيحًا، مثل name@example.com',
    badPhone: 'اكتب الرقم بصيغة 05xxxxxxxx', fix: 'راجع الحقول المميّزة.',
    sending: 'جارٍ الإرسال…', ok: 'شكرًا لك. استلمنا بيانات ', okEnrolled: ' من طلابنا بالفعل، وستربط الإدارة حسابك بصفحته.',
    okNext: 'الخطوة التالية: ادخل بحساب Google بالبريد ', okNext2: '.', signIn: 'الدخول بحساب Google',
    fail: 'تعذّر إرسال النموذج الآن. ', failWa: 'راسلنا على واتساب مباشرة', waText: 'مرحبًا، أرغب بتسجيل طفلي في الروضة.'
  };
  function $(id) { return doc.getElementById(id); }
  function esc(s) { var d = doc.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML.replace(/"/g, '&quot;').replace(/'/g, '&#39;'); }
  function idle(fn) { ('requestIdleCallback' in window) ? requestIdleCallback(fn, { timeout: 2500 }) : setTimeout(fn, 1200); }
  function near(el, fn) {
    if (!el) return;
    if (!('IntersectionObserver' in window)) { fn(); return; }
    var io = new IntersectionObserver(function (es) {
      if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); fn(); }
    }, { rootMargin: '600px 0px' });
    io.observe(el);
  }
  var reduceMotion = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---- 1. full stylesheet (loaded as media=print so it never blocks paint) ---- */
  var css = $('home-css') || $('app-css');
  if (css) css.media = 'all';

  /* ---- 2. analytics: GA4 loads after the first interaction or 8s after load ---- */
  var GA_ID = 'G-H0856C2N0T';
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function () { dataLayer.push(arguments); };
  gtag('js', new Date());
  gtag('config', GA_ID);
  var gaLoaded = false;
  function loadGA() {
    if (gaLoaded) return; gaLoaded = true;
    var s = doc.createElement('script'); s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    doc.head.appendChild(s);
  }
  ['pointerdown', 'keydown', 'touchstart', 'scroll'].forEach(function (t) {
    addEventListener(t, loadGA, { once: true, passive: true });
  });
  addEventListener('load', function () { setTimeout(loadGA, 8000); }, { once: true });

  function srcOf(href) { var m = /[?&]src=([^&#]+)/.exec(href || ''); return m ? decodeURIComponent(m[1]) : ''; }
  /* Events (GA4):
     whatsapp_click  {link_location, link_url}  click on any /wa/ or wa.me link (intent; the chat itself happens in WhatsApp)
     book_visit_click {link_location}           click on an in-page "book a visit" link (#register)
     phone_click      {link_location}           click on a tel: link
     generate_lead    {form_id, enrolled}        ONLY after register-visit confirms ok:true */
  doc.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[href]');
    if (!a) return;
    var h = a.getAttribute('href') || '';
    var where = a.getAttribute('data-cta') || srcOf(h) || (a.closest('header') ? 'nav' : a.closest('footer') ? 'footer' : 'body');
    if (h.indexOf('/wa/') === 0 || h.indexOf('wa.me') > -1 || h.indexOf('api.whatsapp.com') > -1) {
      loadGA();
      var sameTab = !a.target && !e.metaKey && !e.ctrlKey && !e.shiftKey && !e.altKey && e.button === 0;
      if (sameTab) {
        /* give the beacon a moment before leaving the page (max ~0.8s) */
        e.preventDefault();
        var went = false, go = function () { if (!went) { went = true; location.href = a.href; } };
        gtag('event', 'whatsapp_click', { link_location: where, link_url: h, transport_type: 'beacon', event_callback: go, event_timeout: 800 });
        setTimeout(go, 900);
      } else {
        gtag('event', 'whatsapp_click', { link_location: where, link_url: h, transport_type: 'beacon' });
      }
    } else if (h === '#register') {
      gtag('event', 'book_visit_click', { link_location: where });
    } else if (h.indexOf('tel:') === 0) {
      gtag('event', 'phone_click', { link_location: where, transport_type: 'beacon' });
    }
  }, true);

  /* ---- 3. drawer + back to top ---- */
  var drawer = $('drawer'), burger = $('burger'), closeBtn = $('drawer-close');
  function focusables() { return [].slice.call(drawer.querySelectorAll('a[href],button')); }
  function openD() { drawer.classList.add('open'); doc.body.classList.add('no-scroll'); burger.setAttribute('aria-expanded', 'true'); closeBtn.focus(); }
  function closeD(restore) { drawer.classList.remove('open'); doc.body.classList.remove('no-scroll'); burger.setAttribute('aria-expanded', 'false'); if (restore) burger.focus(); }
  if (drawer && burger && closeBtn) {
    burger.addEventListener('click', openD);
    closeBtn.addEventListener('click', function () { closeD(true); });
    drawer.addEventListener('click', function (e) { if (e.target.closest('[data-close]')) closeD(false); });
    doc.addEventListener('keydown', function (e) {
      if (!drawer.classList.contains('open')) return;
      if (e.key === 'Escape') { closeD(true); return; }
      if (e.key === 'Tab') {
        var f = focusables(), first = f[0], last = f[f.length - 1];
        if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    });
  }
  var totop = $('totop');
  if (totop) {
    var ticking = false;
    addEventListener('scroll', function () {
      if (ticking) return; ticking = true;
      requestAnimationFrame(function () { totop.classList.toggle('show', scrollY > 900); ticking = false; });
    }, { passive: true });
    totop.addEventListener('click', function () {
      scrollTo({ top: 0, behavior: reduceMotion ? 'auto' : 'smooth' });
      var t = $('main'); if (t) { t.setAttribute('tabindex', '-1'); t.focus({ preventScroll: true }); }
    });
  }

  /* ---- 4. lightbox ---- */
  function lightbox(urls, start, alts) {
    var i = start || 0, opener = doc.activeElement;
    var lb = doc.createElement('div');
    lb.className = 'lightbox'; lb.setAttribute('role', 'dialog'); lb.setAttribute('aria-modal', 'true'); lb.setAttribute('aria-label', T.lbLabel);
    var btn = function (cls, label, icon) {
      return '<button type="button" class="' + cls + '"><svg class="k-ic" aria-hidden="true"><use href="#' + icon + '"/></svg><span class="sr-only">' + label + '</span></button>';
    };
    lb.innerHTML = btn('lb-close', T.lbClose, 'i-close') +
      (urls.length > 1 ? btn('lb-nav lb-prev', T.lbPrev, 'i-up') + btn('lb-nav lb-next', T.lbNext, 'i-up') : '') + '<img alt=""/>';
    doc.body.appendChild(lb); doc.body.classList.add('no-scroll');
    var img = lb.querySelector('img'), btns = [].slice.call(lb.querySelectorAll('button'));
    function show() { img.src = urls[i]; img.alt = (alts && alts[i]) || T.galAlt[i % T.galAlt.length]; }
    function step(d) { i = (i + d + urls.length) % urls.length; show(); }
    function close() {
      lb.classList.remove('show'); doc.removeEventListener('keydown', key); doc.body.classList.remove('no-scroll');
      setTimeout(function () { lb.remove(); if (opener && opener.focus) opener.focus(); }, reduceMotion ? 0 : 250);
    }
    function key(e) {
      if (e.key === 'Escape') close();
      else if (e.key === 'ArrowLeft') step(EN ? -1 : 1);
      else if (e.key === 'ArrowRight') step(EN ? 1 : -1);
      else if (e.key === 'Tab') {
        var first = btns[0], last = btns[btns.length - 1];
        if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
        else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    }
    lb.querySelector('.lb-close').addEventListener('click', close);
    lb.addEventListener('click', function (e) { if (e.target === lb) close(); });
    var pv = lb.querySelector('.lb-prev'), nx = lb.querySelector('.lb-next');
    if (pv) pv.addEventListener('click', function () { step(-1); });
    if (nx) nx.addEventListener('click', function () { step(1); });
    doc.addEventListener('keydown', key);
    show();
    requestAnimationFrame(function () { lb.classList.add('show'); btns[0].focus(); });
  }

  /* ---- 5. gallery: photo IDs come from the Odoo feed (the owner manages them there).
     The feed only answers montessori-ksa.com (CORS), so other hosts and failures use
     the last known list. Hero photos are self-hosted and skipped here. ---- */
  var ODOO = 'https://odoo.montessori-ksa.com';
  var KNOWN = ['1tOy85z8eimnAXtmOaa061NYhIdv_NemA', '18AmxJGSzkXFACqG4pA2qasufXmQMXXHK', '1DVZt47s2WO7SraNoyjcmrD60Nu9fdUID',
    '1VMJOmDnqr3niyLeye2SAtyQExXYTj4ns', '1gM7V8dojY3a_3qXf9_UlSi4H1nX7FFKo', '1cNkIXcn45SF2iG0P09muLu0d4zmEEaVq',
    '14_F8xmy-Q5FD3NULeGho8hFBOlP1BTD-', '1zELC2MRvcmIJ3F2uubH8dFCVSRYeUo_5', '1aer3_z4PBR-LiL1bv6yzxCeRgRgXh6Et', '1zqh4XFDEzMEPLyf1PGg-wzcaF9W8vFeD'];
  function thumb(id, w) { return 'https://lh3.googleusercontent.com/d/' + encodeURIComponent(id) + '=w' + w; }
  /* feed photos already self-hosted in /assets/img/ (value = file-name prefix); others load from Drive */
  var LOCAL = {
    '1tOy85z8eimnAXtmOaa061NYhIdv_NemA': '', '18AmxJGSzkXFACqG4pA2qasufXmQMXXHK': '', '1X4ke_GBVBaE5dqFJ8ACfAKeoNNzssFNQ': '',
    '1VMJOmDnqr3niyLeye2SAtyQExXYTj4ns': '', '1_lh7XoF9FqgyROroAHGmOb7HRh1MuEaQ': '', '1cNkIXcn45SF2iG0P09muLu0d4zmEEaVq': '',
    '1aer3_z4PBR-LiL1bv6yzxCeRgRgXh6Et': 'home-', '1zqh4XFDEzMEPLyf1PGg-wzcaF9W8vFeD': 'home-',
    '1DVZt47s2WO7SraNoyjcmrD60Nu9fdUID': 'home-', '14_F8xmy-Q5FD3NULeGho8hFBOlP1BTD-': 'home-',
    'wa1103-05': 'home-', 'wa1103-08': 'home-'
  };
  /* the owner's newest photos (WhatsApp, 2026-11-03), self-hosted at 3:4 and shown before the feed.
     The other six from that set are on the hero and the day timeline, so they are not repeated here. */
  var NEW = ['wa1103-05', 'wa1103-08'];
  var ALT = {
    'wa1103-05': ['طفلة بتاج وقفازين زرقاوين تحمل كوبًا على طاولة مزيّنة بالأميرات',
      'A girl in a tiara and blue gloves holding a cup at a princess-themed table'],
    'wa1103-08': ['طفلة بفستان بنفسجي لامع ونظارة «2026» ترفع عصا لعبة أمام لوحة «Back to School»',
      'A girl in a sparkly lilac dress and “2026” glasses raising a toy wand at the Back to School board']
  };
  function altOf(id, n) { return ALT[id] ? ALT[id][EN ? 1 : 0] : T.galAlt[n % T.galAlt.length]; }
  function isLocal(id) { return Object.prototype.hasOwnProperty.call(LOCAL, id); }
  function local(id, w, ext) { return '/assets/img/' + LOCAL[id] + id + '-' + w + '.' + ext; }
  function set(id, ext) { return local(id, 480, ext) + ' 480w, ' + local(id, 800, ext) + ' 800w'; }
  var gal = $('gal');
  function renderGallery(ids) {
    var skip = (gal.getAttribute('data-hero') || '').split(',');
    ids = NEW.concat(ids).filter(function (id, k, all) { return id && skip.indexOf(id) < 0 && all.indexOf(id) === k; }).slice(0, 6);
    if (!ids.length) { gal.outerHTML = '<p class="k-gal-note">' + esc(T.galEmpty) + '</p>'; return; }
    var full = ids.map(function (id) { return isLocal(id) ? local(id, 1200, 'webp') : thumb(id, 1400); });
    var alts = ids.map(altOf);
    gal.innerHTML = ids.map(function (id, n) {
      var alt = esc(alts[n]), sizes = n === 0 ? '(min-width: 760px) 560px, 100vw' : '(min-width: 760px) 280px, 50vw';
      var img = isLocal(id)
        ? '<picture><source type="image/avif" srcset="' + set(id, 'avif') + '" sizes="' + sizes + '"/><img loading="lazy" decoding="async" width="480" height="' + (ALT[id] ? 640 : 480) + '" alt="' +
          alt + '" src="' + local(id, 800, 'webp') + '" srcset="' + set(id, 'webp') + '" sizes="' + sizes + '"/></picture>'
        : '<img loading="lazy" decoding="async" width="480" height="480" alt="' + alt + '" src="' + thumb(id, n === 0 ? 900 : 500) + '"/>';
      return '<button type="button" class="cell" data-i="' + n + '">' + img + '<span class="sr-only">' + esc(T.galOpen) + '</span></button>';
    }).join('');
    /* a Drive photo that fails to load leaves the bento rather than showing a broken image */
    [].forEach.call(gal.querySelectorAll('img'), function (im) {
      im.addEventListener('error', function () { var c = im.closest('.cell'); if (c) c.hidden = true; });
    });
    gal.addEventListener('click', function (e) {
      var c = e.target.closest('.cell'); if (c) lightbox(full, +c.getAttribute('data-i'), alts);
    });
  }
  near(gal, function () {
    if (location.hostname !== 'montessori-ksa.com' && location.hostname !== 'www.montessori-ksa.com') { renderGallery(KNOWN); return; }
    fetch(ODOO + '/site/photos?limit=12', { credentials: 'omit' })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) { var p = d && d.photos || []; renderGallery(p.length ? p : KNOWN); })
      .catch(function () { renderGallery(KNOWN); });
  });

  /* ---- 6. Google reviews (/assets/reviews.json: all reviews, unfiltered, shown as written) ---- */
  var revSec = $('reviews-sec');
  near(gal || revSec, function () {
    fetch('/assets/reviews.json').then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (d) {
      /* every review in the file, in its original order; no rating filter */
      var list = (d && d.reviews || []).filter(function (r) { return r && r.text; });
      if (!list.length) return;
      var star = '<svg aria-hidden="true"><use href="#i-star"/></svg>';
      function stars(n) { var h = ''; n = Math.round(+n || 0); for (var k = 0; k < n; k++) h += star; return h; }
      /* no aggregate rating or count in our own copy: link to the reviews on Google instead */
      $('g-rating').innerHTML = d.url && /^https:\/\//.test(d.url) ? '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">' + esc(T.readAll) + '</a>' : '';
      $('reviews-grid').innerHTML = list.map(function (r) {
        return '<figure class="k-quote"><span class="k-stars" role="img" aria-label="' + esc((r.rating || '') + T.stars) + '">' + stars(r.rating) + '</span>' +
          '<blockquote><p>' + esc(r.text) + '</p></blockquote><footer><b>' + esc(r.name) + '</b> · ' + esc(r.when || '') + '</footer></figure>';
      }).join('');
      revSec.hidden = false;
    }).catch(function () { /* keep the section hidden */ });
  });

  /* ---- 7. parents form → https://odoo.montessori-ksa.com/register-visit ---- */
  var form = $('regform');
  if (form) {
    var msg = $('reg-msg'), btn = $('reg-submit');
    // ٠-٩ and ۰-۹ from Arabic keyboards -> 0-9, for validation and for what Odoo receives
    function latinDigits(v) { return v.replace(/[\u0660-\u0669\u06F0-\u06F9]/g, function (c) { return String(c.charCodeAt(0) & 15); }); }
    var fields = {
      child_name: function (v) { return v ? '' : T.reqChild; },
      parent_email: function (v) { return /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(v) ? '' : T.badEmail; },
      parent_phone: function (v) { return !v || /^0?5\d{8}$/.test(latinDigits(v).replace(/[\s-]/g, '')) ? '' : T.badPhone; }
    };
    function check(name) {
      var input = form.elements[name], wrap = input.closest('.k-field'), err = fields[name](input.value.trim());
      wrap.classList.toggle('is-invalid', !!err);
      input.setAttribute('aria-invalid', err ? 'true' : 'false');
      if (err) wrap.querySelector('.k-err').textContent = err;
      return !err;
    }
    Object.keys(fields).forEach(function (n) {
      form.elements[n].addEventListener('blur', function () { if (this.value.trim() || this.getAttribute('aria-invalid') === 'true') check(n); });
      form.elements[n].addEventListener('input', function () { if (this.getAttribute('aria-invalid') === 'true') check(n); });
    });
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      if (btn.getAttribute('aria-busy') === 'true') return;
      var bad = Object.keys(fields).filter(function (n) { return !check(n); });
      msg.className = 'k-form-status';
      if (bad.length) { msg.classList.add('is-error'); msg.textContent = T.fix; form.elements[bad[0]].focus(); return; }
      var child = form.elements.child_name.value.trim(), email = form.elements.parent_email.value.trim();
      form.elements.parent_phone.value = latinDigits(form.elements.parent_phone.value);
      btn.setAttribute('aria-busy', 'true'); btn.disabled = true; msg.textContent = T.sending;
      fetch(form.action, {
        method: 'POST', credentials: 'omit',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
        body: new URLSearchParams(new FormData(form))
      }).then(function (r) { return r.json(); }).then(function (x) {
        if (!x || !x.ok) throw { app: x && x.error };
        loadGA();
        gtag('event', 'generate_lead', { form_id: 'regform', enrolled: !!x.enrolled });
        var name = esc(x.child || child);
        form.innerHTML = '<p class="k-form-status is-ok" role="status" tabindex="-1">' +
          (x.enrolled ? name + esc(T.okEnrolled) : esc(T.ok) + name + '.') + '</p><p>' + esc(T.okNext) + '<bdi dir="ltr">' + esc(email) + '</bdi>' + esc(T.okNext2) +
          '</p><a class="k-btn k-btn--primary k-btn--block k-mt" href="/login/" rel="nofollow">' + esc(T.signIn) + '</a>';
        form.querySelector('[role=status]').focus();
      }).catch(function (e) {
        btn.removeAttribute('aria-busy'); btn.disabled = false;
        msg.classList.add('is-error');
        msg.innerHTML = esc((e && e.app) ? e.app + ' ' : T.fail) +
          '<a href="/wa/?src=form_fallback" data-cta="form_fallback">' + esc(T.failWa) + '</a>';
      });
    });
  }

  /* ---- 8. owner-only live visitor count in the tab title (opt-in key, unchanged behaviour) ---- */
  idle(function () {
    try {
      var q = new URLSearchParams(location.search);
      if (q.get('live') === 'a7f3live9x') localStorage.setItem('ns_live', '1');
      if (q.get('live') === '0') localStorage.removeItem('ns_live');
      if (localStorage.getItem('ns_live') !== '1') return;
    } catch (e) { return; }
    var base = doc.title;
    function upd() {
      fetch('/live.json?_=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (d) {
        var n = (d && d.now) || 0;
        var AR = { Jeddah: 'جدة', Riyadh: 'الرياض', Makkah: 'مكة', Mecca: 'مكة', Madinah: 'المدينة', Medina: 'المدينة', Dammam: 'الدمام', Taif: 'الطائف', Khobar: 'الخبر', Abha: 'أبها', Dubai: 'دبي', Cairo: 'القاهرة' };
        var city = d && d.city ? (EN ? d.city : (AR[d.city] || d.city)) : '';
        doc.title = (n > 0 ? '👥 ' + n + (city ? ' · ' + city : '') + ' – ' : '') + base;
      }).catch(function () {});
    }
    upd(); setInterval(upd, 60000);
  });
})();
