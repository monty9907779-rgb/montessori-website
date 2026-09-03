/* Montessori deterministic FAQ bot.
 * Local static menu with no network requests.
 */
(function () {
  'use strict';

  if (window.__MONTESSORI_STATIC_FAQ__) return;
  window.__MONTESSORI_STATIC_FAQ__ = true;

  var ADMIN_FALLBACK =
    'سيتم الرد من خلال الإدارة في مواعيد العمل الرسمية.';

  var FAQ = {
    '1': {
      question: 'مواعيد الدوام',
      answer: 'مواعيد الدوام من الأحد إلى الخميس، من ٨:٠٠ صباحًا حتى ١:٠٠ ظهرًا. الجمعة والسبت إجازة.'
    },
    '2': {
      question: 'الأعمار المستقبلة',
      answer: 'نستقبل الأطفال من عمر سنتين إلى ٥ سنوات.'
    },
    '3': {
      question: 'رسوم العام الدراسي ٢٠٢٦–٢٠٢٧',
      answer: 'هذه صورة رسوم العام الدراسي ٢٠٢٦–٢٠٢٧. تؤكد الإدارة توفر المقاعد والتفاصيل الحالية.',
      image: '/assets/fees-2026-2027.jpeg',
      imageAlt: 'رسوم روضة كوكب الطفل الحر للعام الدراسي ٢٠٢٦–٢٠٢٧'
    },
    '4': {
      question: 'آلية التسجيل',
      answer: [
        'للتسجيل:',
        '١. اكتب اسم الطفل والبريد الإلكتروني في نموذج «سجّل ابنك» بالصفحة الرئيسية.',
        '٢. ادخل بحساب Google باستخدام البريد نفسه.',
        '٣. تراجع الإدارة الطلب وتربط حساب ولي الأمر بصفحة الطفل.',
        'التسجيل لا يُعد مؤكدًا إلا بعد تأكيد الإدارة.'
      ].join('\n')
    },
    '5': {
      question: 'موقع الحضانة',
      answer: 'موقع الحضانة: 8603 شارع محمد عبدالكريم، حي الفيصلية، جدة 23447.',
      links: [
        { label: 'فتح الموقع على Google Maps', url: 'https://maps.app.goo.gl/M8cnBRL89M9ppDJY7' }
      ]
    },
    '6': {
      question: 'دخول الأهالي والفريق',
      answer: 'من صفحة «الدخول» يمكن الدخول بحساب Google أو بالبريد الإلكتروني وكلمة المرور. تظهر صفحة الطفل لولي الأمر بعد ربط الحساب من الإدارة.'
    },
    '7': {
      question: 'روابط التواصل والسوشيال ميديا',
      answer: 'هذه روابط التواصل الرسمية المتاحة:',
      links: [
        { label: 'Instagram: @montessori_nursery', url: 'https://www.instagram.com/montessori_nursery/' },
        { label: 'WhatsApp عبر الموقع', url: '/wa/?src=site' },
        { label: 'الموقع الإلكتروني', url: 'https://montessori-ksa.com/' }
      ]
    },
    '8': {
      question: 'آراء Google Maps',
      answer: [
        'تقييم Google Maps وقت التحديث: ٤٫٧ من ٥ بناءً على ٧٠ مراجعة.',
        'من أبرز آراء أولياء الأمور:',
        '• تحسن واضح في مستوى الأطفال ورضا عن مستوى التعليم.',
        '• أنشطة عملية مميزة وبيئة نظيفة ومهتمة بالأطفال.',
        '• معلمات ومربيات متعاونات واهتمام جيد بالتعلم والسلامة.',
        '• تواصل سريع من الفريق عند الحاجة.',
        'يمكنك فتح Google Maps للاطلاع على جميع الآراء المحدثة.'
      ].join('\n'),
      links: [
        { label: 'عرض الموقع والآراء على Google Maps', url: 'https://maps.google.com/?cid=12601466599204157435' }
      ]
    },
    '9': {
      question: 'حجز زيارة للحضانة',
      answer: 'لحجز زيارة، افتح نموذج «احجز زيارة» في الصفحة الرئيسية وأدخل اسم الطفل والبريد الإلكتروني. تراجع الإدارة الطلب وتتواصل معك لتأكيد موعد الزيارة.',
      links: [
        { label: 'فتح نموذج حجز الزيارة', url: '/#register' }
      ]
    },
    '10': {
      question: 'استفسارات أخرى',
      answer: ADMIN_FALLBACK
    }
  };

  var ARABIC_DIGITS = {
    '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
    '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9'
  };

  function normalizeInput(value) {
    return String(value || '')
      .trim()
      .replace(/[٠-٩]/g, function (digit) { return ARABIC_DIGITS[digit]; });
  }

  function menuText() {
    return [
      'مرحبًا بك في روضة كوكب الطفل الحر.',
      'اكتب رقم السؤال فقط:',
      '١. مواعيد الدوام',
      '٢. الأعمار المستقبلة',
      '٣. رسوم العام الدراسي ٢٠٢٦–٢٠٢٧',
      '٤. آلية التسجيل',
      '٥. موقع الحضانة',
      '٦. دخول الأهالي والفريق',
      '٧. روابط التواصل والسوشيال ميديا',
      '٨. آراء Google Maps',
      '٩. حجز زيارة للحضانة',
      '١٠. استفسارات أخرى',
      '٠. عرض القائمة'
    ].join('\n');
  }

  function getItem(input) {
    var key = normalizeInput(input);
    if (key === '0') return { answer: menuText() };
    if (Object.prototype.hasOwnProperty.call(FAQ, key)) return FAQ[key];
    return { answer: ADMIN_FALLBACK + '\n\n' + menuText() };
  }

  function getReply(input) {
    return getItem(input).answer;
  }

  window.MontessoriFAQ = {
    faq: FAQ,
    menu: menuText,
    reply: getReply,
    item: getItem,
    fallback: ADMIN_FALLBACK
  };

  function mount() {
    if (!document.body || document.getElementById('mk-faq-widget')) return;

    var style = document.createElement('style');
    style.textContent =
      '#mk-faq-widget{position:fixed;left:20px;bottom:20px;z-index:9400;font-family:inherit;direction:rtl}' +
      '#mk-faq-toggle{width:58px;height:58px;border:0;border-radius:50%;background:#7c3aed;color:#fff;' +
      'font-size:25px;cursor:pointer;box-shadow:0 8px 24px rgba(0,0,0,.24)}' +
      '#mk-faq-panel{display:none;position:absolute;left:0;bottom:70px;width:min(360px,calc(100vw - 28px));' +
      'max-height:520px;background:#fff;border:1px solid #e5e7eb;border-radius:18px;overflow:hidden;' +
      'box-shadow:0 18px 50px rgba(0,0,0,.22)}' +
      '#mk-faq-panel.open{display:flex;flex-direction:column}' +
      '#mk-faq-title{padding:14px 16px;background:#7c3aed;color:#fff;font-weight:800}' +
      '#mk-faq-log{padding:14px;overflow:auto;min-height:220px;max-height:360px;background:#fafafa}' +
      '.mk-faq-msg{white-space:pre-line;margin:0 0 10px;padding:10px 12px;border-radius:12px;line-height:1.65}' +
      '.mk-faq-bot{background:#fff;border:1px solid #ede9fe;color:#292524}' +
      '.mk-faq-user{background:#7c3aed;color:#fff;margin-right:42px}' +
      '#mk-faq-form{display:flex;gap:8px;padding:10px;background:#fff;border-top:1px solid #eee}' +
      '#mk-faq-input{flex:1;min-width:0;border:1px solid #d1d5db;border-radius:10px;padding:10px;font:inherit}' +
      '#mk-faq-send{border:0;border-radius:10px;background:#f59e0b;color:#fff;padding:0 16px;font-weight:800;cursor:pointer}';
    document.head.appendChild(style);

    var wrap = document.createElement('div');
    wrap.id = 'mk-faq-widget';
    wrap.innerHTML =
      '<button id="mk-faq-toggle" type="button" aria-label="فتح الأسئلة الشائعة">؟</button>' +
      '<section id="mk-faq-panel" aria-label="الأسئلة الشائعة">' +
        '<div id="mk-faq-title">الأسئلة الشائعة</div>' +
        '<div id="mk-faq-log"></div>' +
        '<form id="mk-faq-form">' +
          '<input id="mk-faq-input" inputmode="numeric" autocomplete="off" placeholder="اكتب رقم السؤال فقط">' +
          '<button id="mk-faq-send" type="submit">إرسال</button>' +
        '</form>' +
      '</section>';
    document.body.appendChild(wrap);

    var panel = document.getElementById('mk-faq-panel');
    var log = document.getElementById('mk-faq-log');
    var input = document.getElementById('mk-faq-input');

    function addMessage(text, kind) {
      var item = document.createElement('div');
      item.className = 'mk-faq-msg ' + kind;
      item.textContent = text;
      log.appendChild(item);
      log.scrollTop = log.scrollHeight;
    }

    function addMedia(item) {
      if (item.image) {
        var image = document.createElement('img');
        image.src = item.image;
        image.alt = item.imageAlt || '';
        image.loading = 'lazy';
        image.style.cssText = 'display:block;width:100%;height:auto;border-radius:12px;margin:0 0 10px';
        log.appendChild(image);
      }
      if (item.links && item.links.length) {
        var links = document.createElement('div');
        links.className = 'mk-faq-msg mk-faq-bot';
        item.links.forEach(function (link, index) {
          var anchor = document.createElement('a');
          anchor.href = link.url;
          anchor.target = '_blank';
          anchor.rel = 'noopener';
          anchor.textContent = link.label;
          anchor.style.cssText = 'display:block;color:#6d28d9;font-weight:700;margin:' +
            (index ? '8px' : '0') + ' 0 0;text-decoration:underline';
          links.appendChild(anchor);
        });
        log.appendChild(links);
      }
      log.scrollTop = log.scrollHeight;
    }

    addMessage(menuText(), 'mk-faq-bot');

    document.getElementById('mk-faq-toggle').addEventListener('click', function () {
      panel.classList.toggle('open');
      if (panel.classList.contains('open')) input.focus();
    });

    document.getElementById('mk-faq-form').addEventListener('submit', function (event) {
      event.preventDefault();
      var value = input.value.trim();
      if (!value) return;
      addMessage(value, 'mk-faq-user');
      var item = getItem(value);
      addMessage(item.answer, 'mk-faq-bot');
      addMedia(item);
      input.value = '';
      input.focus();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
}());
