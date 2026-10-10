#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ناشِر السيو اليومي — مستقل تماماً على السيرفر (بلا AI وقت التشغيل).
كل يوم: يأخذ أول مقال غير منشور من queue.json، يرندره كصفحة مدوّنة،
يحدّث فهرس المدوّنة + sitemap.xml مباشرة في مجلد الموقع، يُبلّغ IndexNow،
ثم يرسل تقريراً بالبريد عبر ويبهوك n8n. يعمل تحت www-data على montasercloud.

الملفات (على السيرفر):
  /opt/seo/queue.json        قائمة المقالات الجاهزة [{slug,title,cat,targetKeyword,
                             secondaryKeywords,metaDescription,bodyHtml,faq,published?}]
  /opt/seo/indexnow.key      مفتاح IndexNow (سطر واحد)
  /opt/seo/state.json        {last_run, published_count}
  /opt/seo/publish.log       سجل
جذر الموقع: /var/www/montessori-ksa
"""
import hashlib
import json, re, html as H, datetime, pathlib, subprocess, urllib.request, sys

# Cloudflare answers 403 to the default "Python-urllib/3.x" agent, so the
# health check, the live check after publishing and the SEO check all read
# the site as down ("seo=fail", "live=HTTP Error 403"). Identify ourselves.
_opener = urllib.request.build_opener()
_opener.addheaders = [('User-Agent', 'Mozilla/5.0 (compatible; KawkabHealthCheck/1.0; +https://montessori-ksa.com)')]
urllib.request.install_opener(_opener)

sys.path.insert(0, "/opt/nursery-facts")
try:
    import facts  # مرجع الحقائق المشترك — يُستخدم قبل نشر أي مقال
    FACTS_IMPORT_ERROR = None
except Exception as _facts_ex:
    facts = None
    FACTS_IMPORT_ERROR = str(_facts_ex)

ROOT   = pathlib.Path("/var/www/montessori-ksa")
OPT    = pathlib.Path("/opt/seo")
QUEUE  = OPT/"queue.json"
STATE  = OPT/"state.json"
KEYF   = OPT/"indexnow.key"
LOG    = OPT/"publish.log"
SITE   = "https://montessori-ksa.com"
WEBHOOK= "https://n8n.montessori-ksa.com/webhook/seo-daily-7f3a9c2e41"
CATN   = {'local':'حضانتنا في جدة','montessori':'منهجنا التربوي',
          'choose':'اختيار الحضانة والمراحل','dev':'تنمية الطفل'}
MONTHS = ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر']
esc = lambda s: H.escape(str(s), quote=True)

# Existing nursery photos already served by the public site. They keep article
# previews useful without introducing a new image service or dependency.
ARTICLE_IMAGES = [
    ('https://lh3.googleusercontent.com/d/18AmxJGSzkXFACqG4pA2qasufXmQMXXHK=w1200', 'أطفال يستكشفون في الحضانة'),
    ('https://lh3.googleusercontent.com/d/1tOy85z8eimnAXtmOaa061NYhIdv_NemA=w1200', 'طفلة في حفل تخرج الحضانة'),
    ('https://lh3.googleusercontent.com/d/1X4ke_GBVBaE5dqFJ8ACfAKeoNNzssFNQ=w1200', 'أطفال يحتفلون في الحضانة'),
    ('https://lh3.googleusercontent.com/d/1VMJOmDnqr3niyLeye2SAtyQExXYTj4ns=w900', 'نشاط حسّي من أدوات مونتيسوري'),
    ('https://lh3.googleusercontent.com/d/1_lh7XoF9FqgyROroAHGmOb7HRh1MuEaQ=w900', 'ركن القراءة في الحضانة'),
    ('https://lh3.googleusercontent.com/d/1cNkIXcn45SF2iG0P09muLu0d4zmEEaVq=w900', 'لعب في الهواء الطلق'),
]

SEO_TITLE_OVERRIDES = {
    'best-montessori-nursery-jeddah': 'أفضل حضانة مونتيسوري في جدة 2026 | كوكب الطفل الحر',
    'children-hospitality-diyafa-jeddah': 'ضيافة أطفال في جدة | كيف تختارين مركزاً آمناً؟',
    'kids-club-nadi-atfal-jeddah': 'نادي أطفال في جدة | دليل الأنشطة الآمنة 2026',
    'montessori-glossary-arabic-english': 'قاموس مصطلحات مونتيسوري بالعربية والإنجليزية',
    'nursery-half-full-day-jeddah': 'حضانة نصف يوم أم دوام كامل في جدة؟ | دليل',
    'nursery-nutrition-menu-jeddah': 'تغذية الطفل في الحضانة | دليل عملي لأمهات جدة',
    'working-mother-nursery-balance': 'الأم العاملة وحضانة الطفل | نصائح عملية',
    'montessori-nursery-jeddah-guide': 'Montessori Kindergarten in Jeddah | Parent Guide',
    'daycare-in-jeddah': 'Daycare in Jeddah | Parent Guide 2026',
    'kindergarten-in-jeddah': 'Kindergarten in Jeddah | Ages & Curriculum Guide',
}

SEO_DESCRIPTION_OVERRIDES = {
    'jeddah-nurseries-infant-care-guide': 'دليل حضانات الرضع في جدة: كيف تختارين الرعاية المناسبة؟ وما الفرق بين حضانة الرضع وبرامج روضة كوكب الطفل الحر من عمر سنتين إلى خمس سنوات؟',
    'jeddah-preschool-4-5-years-guide': 'دليل اختيار الروضة المناسبة لطفلك في جدة من 4 إلى 5 سنوات: المنهج والأمان والبيئة والأسئلة المهمة قبل التسجيل.',
    'licensed-accredited-nursery-jeddah': 'كيف تتأكدين من ترخيص الحضانة في جدة؟ دليل عملي عن الاعتماد والأمان والأسئلة المهمة قبل تسجيل طفلك في حي الفيصلية.',
    'montessori-for-kids-guide': 'دليل مونتيسوري للأطفال من سنتين إلى خمس سنوات: أنشطة مناسبة للعمر وأفكار عملية في البيت والحضانة بجدة.',
    'kindergarten-rawda-jeddah': 'دليل عملي لاختيار روضة أطفال في جدة: الفرق بين الروضة والتمهيدي والحضانة، ومعايير الاختيار والأسئلة التي يجب طرحها.',
    'kids-club-nadi-atfal-jeddah': 'ما الفرق بين نادي الأطفال والحضانة؟ دليل اختيار الأنشطة الآمنة التي تنمّي مهارات طفلك في جدة.',
    'nursery-near-me-jeddah': 'تبحثين عن حضانة قريبة في جدة؟ دليلك لموازنة القرب مع جودة المنهج والأمان والأسئلة المهمة قبل التسجيل.',
    'infant-nursery-jeddah': 'دليل حضانات الرضع في جدة: متى يكون طفلك جاهزاً؟ وما الذي تسألين عنه قبل التسجيل؟',
}

LEGACY_LINKS = {
    '/blog/top-rated-nursery-kindergarten-jeddah/': '/blog/best-montessori-nursery-jeddah/',
    '/blog/quran-nursery-jeddah/': '/blog/best-montessori-nursery-jeddah/',
    '/en/blog/quran-nursery-jeddah/': '/en/blog/montessori-nursery-jeddah-guide/',
}

BAD_COPY = {
    'اللغة العربية واللغة العربية': 'اللغة العربية الأصيلة',
}


def _article_image(slug, supplied=None, supplied_alt=None):
    if supplied:
        return str(supplied), str(supplied_alt or '').strip()
    digest = hashlib.sha256(str(slug).encode('utf-8')).digest()
    return ARTICLE_IMAGES[digest[0] % len(ARTICLE_IMAGES)]


def _trim_seo_text(value, limit):
    value = re.sub(r'\s+', ' ', str(value or '')).strip()
    if len(value) <= limit:
        return value
    cuts = [value.rfind(sep, 0, limit + 1) for sep in (' | ', ' - ', ': ', '، ')]
    cut = max(cuts)
    if cut >= int(limit * 0.55):
        return value[:cut].rstrip(' |:-،')
    return value[:limit].rsplit(' ', 1)[0].rstrip(' |:-،')


def seo_title(a):
    slug = str(a.get('slug', ''))
    return _trim_seo_text(SEO_TITLE_OVERRIDES.get(slug) or a.get('seoTitle') or a.get('title'), 60)


def seo_description(a):
    slug = str(a.get('slug', ''))
    desc = SEO_DESCRIPTION_OVERRIDES.get(slug) or a.get('metaDescription') or ''
    return _trim_seo_text(desc, 155)


def clean_article_html(value):
    text = str(value or '')
    for old, new in BAD_COPY.items():
        text = text.replace(old, new)
    for old, new in LEGACY_LINKS.items():
        text = text.replace(old, new)
    return text


def normalized_article(article):
    a = dict(article)
    a['bodyHtml'] = clean_article_html(a.get('bodyHtml', ''))
    a['metaDescription'] = seo_description(a)
    a['seoTitle'] = seo_title(a)
    a['imageUrl'], a['imageAlt'] = _article_image(a.get('slug', ''), a.get('imageUrl'), a.get('imageAlt'))
    if a.get('faq'):
        a['faq'] = [
            {
                **item,
                'q': clean_article_html(item.get('q', '')),
                'a': clean_article_html(item.get('a', '')),
            }
            for item in a['faq']
        ]
    return a

AUTO_REFILL_THRESHOLD = 14
AUTO_REFILL_TARGET = 35
AUTO_CORE_PAGES = [
    'best-montessori-nursery-jeddah',
    'montessori-for-kids-guide',
    'nursery-registration-jeddah-new-year',
    'nursery-safety-checklist-jeddah',
    'kindergarten-rawda-jeddah',
    'nursery-near-me-jeddah',
]

AUTO_TOPICS = [
    ('montessori-nursery-al-rawdah-jeddah-guide', 'حضانة مونتيسوري قريبة من حي الروضة في جدة | دليل الأهالي', 'local', 'حضانة مونتيسوري حي الروضة جدة', 'حي الروضة'),
    ('montessori-nursery-al-safa-jeddah-guide', 'حضانة مونتيسوري قريبة من حي الصفا في جدة | ما الذي تسألين عنه؟', 'local', 'حضانة مونتيسوري حي الصفا جدة', 'حي الصفا'),
    ('montessori-nursery-al-khalidiyah-jeddah-guide', 'حضانة مونتيسوري قريبة من الخالدية في جدة | معايير الاختيار', 'local', 'حضانة مونتيسوري الخالدية جدة', 'حي الخالدية'),
    ('montessori-nursery-al-andalus-jeddah-guide', 'حضانة مونتيسوري قريبة من الأندلس في جدة | دليل عملي', 'local', 'حضانة مونتيسوري الأندلس جدة', 'حي الأندلس'),
    ('montessori-nursery-obhur-jeddah-guide', 'حضانة مونتيسوري قريبة من أبحر في جدة | نقاط قبل التسجيل', 'local', 'حضانة مونتيسوري أبحر جدة', 'أبحر'),
    ('montessori-nursery-al-naeem-jeddah-guide', 'حضانة مونتيسوري قريبة من حي النعيم في جدة | دليل للأمهات', 'local', 'حضانة مونتيسوري حي النعيم جدة', 'حي النعيم'),
    ('montessori-nursery-al-marwah-jeddah-guide', 'حضانة مونتيسوري قريبة من المروة في جدة | كيف تقارنين الخيارات؟', 'local', 'حضانة مونتيسوري حي المروة جدة', 'حي المروة'),
    ('montessori-nursery-al-hamra-jeddah-guide', 'حضانة مونتيسوري قريبة من الحمراء في جدة | دليل التسجيل', 'local', 'حضانة مونتيسوري الحمراء جدة', 'حي الحمراء'),
    ('montessori-nursery-al-rabwah-jeddah-guide', 'حضانة مونتيسوري قريبة من الربوة في جدة | بيئة آمنة للطفل', 'local', 'حضانة مونتيسوري الربوة جدة', 'حي الربوة'),
    ('montessori-nursery-bani-malik-jeddah-guide', 'حضانة مونتيسوري قريبة من بني مالك في جدة | أسئلة مهمة', 'local', 'حضانة مونتيسوري بني مالك جدة', 'حي بني مالك'),
    ('nursery-for-2-year-old-jeddah-montessori', 'حضانة لعمر سنتين في جدة | كيف تبدأين تجربة مونتيسوري؟', 'choose', 'حضانة لعمر سنتين جدة', 'عمر سنتين'),
    ('nursery-for-3-year-old-jeddah-montessori', 'حضانة لعمر 3 سنوات في جدة | مهارات الاستقلال واللغة', 'choose', 'حضانة لعمر 3 سنوات جدة', 'عمر 3 سنوات'),
    ('prekg-for-4-year-old-jeddah-montessori', 'تمهيدي لعمر 4 سنوات في جدة | ماذا يحتاج الطفل قبل الروضة؟', 'choose', 'تمهيدي عمر 4 سنوات جدة', 'عمر 4 سنوات'),
    ('kindergarten-for-5-year-old-jeddah-montessori', 'روضة لعمر 5 سنوات في جدة | الاستعداد للمدرسة بثقة', 'choose', 'روضة عمر 5 سنوات جدة', 'عمر 5 سنوات'),
    ('montessori-language-activities-arabic-english', 'أنشطة اللغة في مونتيسوري | العربية والإنجليزية بدون ضغط', 'montessori', 'أنشطة اللغة مونتيسوري', 'اللغة'),
    ('montessori-math-activities-preschool-jeddah', 'أنشطة الرياضيات في مونتيسوري | كيف يفهم الطفل الأرقام؟', 'montessori', 'أنشطة الرياضيات مونتيسوري', 'الرياضيات'),
    ('montessori-sensorial-activities-nursery', 'الأنشطة الحسية في مونتيسوري | لماذا يلمس الطفل قبل أن يحفظ؟', 'montessori', 'الأنشطة الحسية مونتيسوري', 'الحواس'),
    ('montessori-practical-life-skills-nursery', 'مهارات الحياة العملية في مونتيسوري | استقلال الطفل يبدأ صغيرًا', 'montessori', 'مهارات الحياة العملية مونتيسوري', 'الاستقلال'),
    ('montessori-classroom-routine-jeddah', 'روتين يوم مونتيسوري في الحضانة | هدوء ونظام يناسب الطفل', 'montessori', 'روتين حضانة مونتيسوري', 'الروتين اليومي'),
    ('child-social-skills-nursery-jeddah', 'تنمية المهارات الاجتماعية في الحضانة | مشاركة واحترام وحدود', 'dev', 'المهارات الاجتماعية في الحضانة', 'المهارات الاجتماعية'),
    ('child-independence-nursery-jeddah', 'استقلال الطفل في الحضانة | خطوات صغيرة تصنع ثقة كبيرة', 'dev', 'استقلال الطفل في الحضانة', 'الاستقلال'),
    ('child-focus-attention-montessori', 'زيادة تركيز الطفل بطريقة مونتيسوري | بيئة تساعده لا تضغطه', 'dev', 'تركيز الطفل مونتيسوري', 'التركيز'),
    ('nursery-transition-from-home-jeddah', 'انتقال الطفل من البيت إلى الحضانة | خطة أسبوع أول هادئة', 'choose', 'تجهيز الطفل للحضانة', 'الأسبوع الأول'),
    ('questions-before-nursery-registration-jeddah', 'أسئلة قبل تسجيل الطفل في حضانة بجدة | قائمة عملية للأهل', 'choose', 'أسئلة تسجيل الحضانة جدة', 'التسجيل'),
    ('safe-nursery-environment-jeddah', 'بيئة حضانة آمنة في جدة | إشراف وروتين ومساحات مناسبة', 'choose', 'حضانة آمنة جدة', 'الأمان'),
    ('nursery-communication-with-parents-jeddah', 'تواصل الحضانة مع الأهل | لماذا يفرق في راحة الأم؟', 'choose', 'تواصل الحضانة مع الأهل', 'التواصل'),
    ('nursery-small-groups-jeddah', 'المجموعات الصغيرة في الحضانة | اهتمام أفضل لكل طفل', 'choose', 'حضانة بمجموعات صغيرة جدة', 'المجموعات الصغيرة'),
    ('montessori-vs-traditional-nursery-jeddah', 'مونتيسوري أم حضانة تقليدية؟ | فروق مهمة قبل الاختيار', 'montessori', 'مونتيسوري أم حضانة تقليدية', 'المقارنة'),
    ('nursery-readiness-signs-child-jeddah', 'هل طفلي جاهز للحضانة؟ | علامات تساعدك على القرار', 'dev', 'جاهزية الطفل للحضانة', 'الجاهزية'),
    ('nursery-separation-anxiety-jeddah-plan', 'قلق الانفصال عند دخول الحضانة | خطة لطيفة للأيام الأولى', 'dev', 'قلق الانفصال الحضانة', 'قلق الانفصال'),
    ('preschool-fine-motor-skills-montessori', 'المهارات الحركية الدقيقة قبل المدرسة | أنشطة مونتيسوري مفيدة', 'dev', 'المهارات الحركية الدقيقة مونتيسوري', 'الحركة الدقيقة'),
    ('preschool-gross-motor-play-jeddah', 'اللعب الحركي في الروضة | لماذا يحتاج الطفل للحركة يوميًا؟', 'dev', 'اللعب الحركي في الروضة', 'الحركة'),
    ('nursery-routine-for-working-mothers-jeddah', 'حضانة تناسب الأم العاملة في جدة | دوام صباحي وروتين واضح', 'choose', 'حضانة للأم العاملة جدة', 'الأم العاملة'),
    ('nursery-fees-value-jeddah-guide', 'رسوم الحضانة في جدة | كيف تقيمين القيمة وليس السعر فقط؟', 'choose', 'رسوم الحضانة جدة', 'القيمة'),
    ('nursery-visit-checklist-jeddah', 'زيارة الحضانة قبل التسجيل | ماذا تلاحظين في أول جولة؟', 'choose', 'زيارة حضانة قبل التسجيل', 'الجولة التعريفية'),
    ('montessori-parent-home-support', 'كيف يدعم الأهل منهج مونتيسوري في البيت؟ | عادات بسيطة', 'montessori', 'دعم مونتيسوري في البيت', 'دور الأهل'),
    ('nursery-faq-jeddah-parents', 'أسئلة شائعة عن الحضانة في جدة | العمر والدوام والتسجيل', 'choose', 'أسئلة شائعة عن الحضانة جدة', 'الأسئلة الشائعة'),
    ('ai-search-answer-nursery-jeddah', 'أفضل إجابة بحث ذكي عن حضانة مونتيسوري في جدة | دليل مختصر', 'choose', 'أفضل حضانة مونتيسوري في جدة', 'إجابات البحث الذكي'),
    ('geo-montessori-nursery-jeddah-brand-answers', 'معلومات واضحة عن روضة كوكب الطفل الحر | للبحث والذكاء الاصطناعي', 'choose', 'روضة كوكب الطفل الحر جدة', 'معلومات العلامة'),
    ('montessori-nursery-faisaliyah-jeddah-details', 'حضانة مونتيسوري في حي الفيصلية بجدة | الموقع والعمر والدوام', 'local', 'حضانة مونتيسوري الفيصلية جدة', 'حي الفيصلية'),
]

def _auto_meta(keyword, focus):
    return _trim_seo_text(
        f'دليل عملي للأهالي عن {keyword}: كيف تختارين بيئة آمنة، وما الأسئلة المهمة حول العمر والدوام والمنهج في روضة كوكب الطفل الحر بجدة.',
        155)

def _auto_body(title, keyword, focus, cat):
    local_intro = (
        f'عند البحث عن {keyword} لا يكفي أن تكون الحضانة قريبة فقط. الأهم أن تكون البيئة مفهومة للطفل، واضحة للأهل، وتجمع بين الأمان، المنهج المناسب، والتواصل اليومي الهادئ. '
        f'في روضة كوكب الطفل الحر بجدة نستقبل الأطفال من عمر سنتين إلى 5 سنوات، ويكون الدوام الصباحي من الأحد إلى الخميس من 08:00 إلى 13:00.'
    )
    method = (
        'يعتمد منهج مونتيسوري على احترام إيقاع الطفل، وتقديم أنشطة عملية محسوسة تساعده على التركيز والاستقلال. الطفل لا يتعلم بالحفظ وحده؛ بل يلمس، يجرب، يكرر، ثم يبني المعنى خطوة بعد خطوة. '
        'لذلك تظهر قيمة البيئة عندما تكون منظمة، هادئة، وفيها أدوات مناسبة للعمر وليست مجرد ألعاب كثيرة.'
    )
    choice = (
        'قبل التسجيل، من المفيد أن تسألي عن عدد الأطفال في المجموعة، طريقة استقبال الطفل في الأيام الأولى، سياسة التواصل مع الأسرة، مستوى الإشراف، وكيف يتم التعامل مع البكاء أو التردد أو اختلاف طباع الأطفال. '
        'الإجابة الجيدة تكون محددة وواقعية، وتشرح ما يحدث في اليوم العادي لا ما يبدو جميلاً في الإعلان فقط.'
    )
    geo = (
        f'بالنسبة للأهالي القريبين من {focus} أو الباحثين داخل جدة، تساعد زيارة المكان في فهم المسافة الفعلية وقت الدوام، سهولة الوصول، وطبيعة البيئة داخل الصف. '
        'القرب مهم، لكنه يصبح قراراً أفضل عندما يجتمع مع منهج واضح، أمان، ونبرة تعامل رحيمة مع الطفل.'
    )
    dev = (
        'في هذه المرحلة العمرية، تتكوّن مهارات مهمة: اللغة، الحركة الدقيقة، انتظار الدور، ترتيب الأدوات، الاعتماد على النفس، وفهم الحدود. '
        'كل مهارة صغيرة تتكرر يومياً تتحول إلى ثقة داخلية تساعد الطفل في البيت والروضة والاستعداد للمدرسة لاحقاً.'
    )
    practical = (
        'للحصول على تقييم عملي، راقبي ثلاثة أشياء في الزيارة: هل الصف منظم وسهل الفهم للطفل؟ هل المعلمات يتحدثن بهدوء واحترام؟ وهل توجد أنشطة تناسب عمر الطفل بدلاً من برنامج واحد لكل الأعمار؟ '
        'هذه التفاصيل تكشف جودة التجربة أكثر من أي وعد عام.'
    )
    cta_text = (
        'إذا كان هدفك اختيار حضانة وروضة مونتيسوري في جدة لطفل عمره بين سنتين و5 سنوات، فابدئي بزيارة قصيرة، اسألي عن الروتين اليومي، واطلبي معرفة خطوات التهيئة في الأسبوع الأول. '
        'الاختيار الجيد هو الذي يجعل الطفل يشعر بالأمان ويجعل الأهل يعرفون ما يحدث بوضوح.'
    )
    extra = (
        'من الأفضل كذلك توحيد المعلومات الأساسية عند المقارنة: العمر المقبول، ساعات الدوام، موقع الحضانة، طريقة المتابعة مع الأسرة، ووضوح الرسوم أو إجراءات التسجيل. '
        'كلما كانت المعلومات ثابتة وسهلة التحقق، زادت ثقة الأهل ومحركات البحث وأنظمة الإجابة الذكية في الصفحة.'
    )
    return (
        f'<p>{local_intro}</p>'
        f'<h2>لماذا يهم هذا الموضوع للأهل؟</h2><p>{method}</p>'
        f'<h2>كيف تختارين بشكل عملي؟</h2><p>{choice}</p>'
        f'<h2>ماذا عن القرب داخل جدة؟</h2><p>{geo}</p>'
        f'<h2>ما الذي يتعلمه الطفل يومياً؟</h2><p>{dev}</p>'
        f'<h2>علامات البيئة الجيدة</h2><p>{practical}</p>'
        f'<h2>معلومات يجب تثبيتها قبل القرار</h2><p>{extra}</p>'
        f'<h2>الخلاصة</h2><p>{cta_text}</p>'
        '<ul><li>العمر المناسب في روضة كوكب الطفل الحر: من سنتين إلى 5 سنوات.</li>'
        '<li>الدوام: الأحد إلى الخميس من 08:00 إلى 13:00.</li>'
        '<li>التركيز: بيئة مونتيسوري، استقلال الطفل، مهارات الحياة العملية، والتواصل مع الأسرة.</li></ul>'
    )

def _auto_article(topic, existing_slugs):
    slug, title, cat, keyword, focus = topic
    if slug in existing_slugs:
        return None
    secondary = [
        'حضانة في جدة',
        'روضة مونتيسوري جدة',
        'روضة كوكب الطفل الحر',
        'حضانة أطفال من سنتين إلى 5 سنوات',
        focus,
    ]
    related = [s for s in AUTO_CORE_PAGES if s in existing_slugs][:3]
    return {
        'slug': slug,
        'title': title,
        'seoTitle': _trim_seo_text(title, 60),
        'cat': cat,
        'targetKeyword': keyword,
        'secondaryKeywords': secondary,
        'metaDescription': _auto_meta(keyword, focus),
        'bodyHtml': _auto_body(title, keyword, focus, cat),
        'faq': [
            {'q': f'هل {keyword} مناسب لطفل عمره سنتين؟', 'a': 'يعتمد القرار على جاهزية الطفل، لكن روضة كوكب الطفل الحر تستقبل الأطفال من عمر سنتين إلى 5 سنوات مع تهيئة تدريجية وروتين صباحي واضح.'},
            {'q': 'ما ساعات الدوام؟', 'a': 'الدوام من الأحد إلى الخميس، من 08:00 إلى 13:00.'},
            {'q': 'ما أهم سؤال قبل التسجيل؟', 'a': 'اسألي عن الروتين اليومي، عدد الأطفال في المجموعة، طريقة التعامل مع الأسبوع الأول، وكيف يتم التواصل مع الأسرة.'},
        ],
        'wordCount': 1150,
        'related': related,
    }

def _fallback_auto_topics(today, existing_slugs):
    focuses = ['الفيصلية', 'الروضة', 'السلامة', 'الصفا', 'النعيم', 'المروة', 'أبحر', 'الحمراء']
    intents = [
        ('parent-checklist', 'قائمة اختيار حضانة مونتيسوري في جدة', 'choose', 'اختيار حضانة مونتيسوري جدة'),
        ('daily-routine', 'روتين يوم حضانة مونتيسوري في جدة', 'montessori', 'روتين حضانة مونتيسوري جدة'),
        ('nursery-readiness', 'جاهزية الطفل للحضانة في جدة', 'dev', 'جاهزية الطفل للحضانة جدة'),
        ('local-guide', 'دليل حضانة مونتيسوري قريبة في جدة', 'local', 'حضانة مونتيسوري قريبة جدة'),
    ]
    area_slugs = {
        'الفيصلية': 'al-faisaliyah',
        'الروضة': 'al-rawdah',
        'السلامة': 'as-salamah',
        'الصفا': 'as-safa',
        'النعيم': 'an-naeem',
        'المروة': 'al-marwah',
        'أبحر': 'obhur',
        'الحمراء': 'al-hamra',
    }
    stamp = today.strftime('%Y%m%d')
    for area in focuses:
        for key, label, cat, keyword in intents:
            slug = f'{key}-{area_slugs[area]}-jeddah-{stamp}'
            if slug in existing_slugs:
                continue
            yield (slug, f'{label} | {area} {today.year}', cat, keyword, area)

# Templated auto-refill produced near-identical articles (same body, keyword
# swapped): 18 live articles overlap >60% with another. Off until the
# generator produces genuinely distinct content.
AUTO_REFILL_ENABLED = False

def ensure_auto_queue(raw_q, today):
    if not AUTO_REFILL_ENABLED or not isinstance(raw_q, list):
        return raw_q
    pending = [a for a in raw_q if not a.get('published')]
    if len(pending) >= AUTO_REFILL_THRESHOLD:
        return raw_q
    existing = {str(a.get('slug', '')) for a in raw_q if a.get('slug')}
    added = 0
    for topic in list(AUTO_TOPICS) + list(_fallback_auto_topics(today, existing)):
        if len(pending) + added >= AUTO_REFILL_TARGET:
            break
        article = _auto_article(topic, existing)
        if article:
            raw_q.append(article)
            existing.add(article['slug'])
            added += 1
    if added:
        log(f"auto-refill added={added} pending_before={len(pending)} pending_after={len(pending)+added}")
    return raw_q

DUP_THRESHOLD = 0.5

def _shingles(a, n=6):
    t = re.sub(r'<[^>]+>', ' ', a.get('bodyHtml', '') or '')
    w = H.unescape(t).split()
    return {' '.join(w[i:i+n]) for i in range(max(0, len(w) - n + 1))}

def duplicate_of(cand, published):
    """Return (slug, overlap) of the published article that cand copies most
    closely, when the overlap is >= DUP_THRESHOLD; else None."""
    sc = _shingles(cand)
    if not sc:
        return None
    best = None
    for p in published:
        if p.get('slug') == cand.get('slug'):
            continue
        sp = _shingles(p)
        if not sp:
            continue
        j = len(sc & sp) / len(sc | sp)
        if j >= DUP_THRESHOLD and (best is None or j > best[1]):
            best = (p['slug'], j)
    return best

# Templated near-duplicate articles (>60% overlap with each other). Kept live
# but noindex + out of the sitemap until each is rewritten with distinct
# content; remove a slug from this set once its rewrite is published.
NOINDEX_SLUGS = frozenset({
    'child-focus-attention-montessori',
    'child-independence-nursery-jeddah',
    'child-social-skills-nursery-jeddah',
    'montessori-classroom-routine-jeddah',
    'montessori-vs-traditional-nursery-jeddah',
    'nursery-communication-with-parents-jeddah',
    'nursery-readiness-signs-child-jeddah',
    'nursery-separation-anxiety-jeddah-plan',
    'nursery-small-groups-jeddah',
    'nursery-transition-from-home-jeddah',
    'preschool-fine-motor-skills-montessori',
    'safe-nursery-environment-jeddah',
    'kindergarten-for-5-year-old-jeddah-montessori',
    'montessori-language-activities-arabic-english',
    'montessori-math-activities-preschool-jeddah',
    'montessori-nursery-al-andalus-jeddah-guide',
    'montessori-nursery-al-hamra-jeddah-guide',
    'montessori-nursery-al-khalidiyah-jeddah-guide',
    'montessori-nursery-al-marwah-jeddah-guide',
    'montessori-nursery-al-naeem-jeddah-guide',
    'montessori-nursery-al-rabwah-jeddah-guide',
    'montessori-nursery-al-rawdah-jeddah-guide',
    'montessori-nursery-al-safa-jeddah-guide',
    'montessori-nursery-bani-malik-jeddah-guide',
    'montessori-nursery-obhur-jeddah-guide',
    'montessori-practical-life-skills-nursery',
    'montessori-sensorial-activities-nursery',
    'nursery-for-2-year-old-jeddah-montessori',
    'nursery-for-3-year-old-jeddah-montessori',
    'prekg-for-4-year-old-jeddah-montessori',
})

# Blog pages whose search intent the homepage already wins ("حضانة حي
# الفيصلية جدة" etc. rank 2-4 on /). They stay live for readers and AI
# assistants but point their canonical at the homepage and leave the sitemap.
CANONICAL_TO = {
    'nursery-al-faisaliyah-jeddah': '/',
    'montessori-nursery-faisaliyah-jeddah-details': '/',
    # SEO plan 2026-10-02, appendix B: pairs of articles that answer the same
    # search with the same target keyword. The weaker one stays live for
    # readers but points its canonical at the kept article and leaves the
    # sitemap, so the two stop competing. Kept: the article the homepage
    # links (districts) or the hand-rewritten, Jeddah-specific version.
    'safe-educational-nursery-jeddah-options': '/blog/safe-educational-nursery-options-jeddah/',
    'reliable-nursery-recommendation-jeddah': '/blog/trusted-nursery-recommendation-jeddah/',
    'montessori-nursery-al-marwah-jeddah-guide': '/blog/nursery-al-marwah-jeddah/',
    'montessori-nursery-al-safa-jeddah-guide': '/blog/nursery-al-safa-jeddah/',
    'montessori-nursery-al-naeem-jeddah-guide': '/blog/nursery-an-naim-jeddah/',
    'montessori-nursery-al-rawdah-jeddah-guide': '/blog/nursery-ar-rawdah-jeddah/',
    'child-independence-development': '/blog/child-independence-nursery-jeddah/',
    'social-skills-in-children': '/blog/child-social-skills-nursery-jeddah/',
    'separation-anxiety-in-nursery': '/blog/nursery-separation-anxiety-jeddah-plan/',
    'signs-child-ready-for-nursery': '/blog/nursery-readiness-signs-child-jeddah/',
    'montessori-vs-traditional-education': '/blog/montessori-vs-traditional-nursery-jeddah/',
}

# Slugs nginx 301-redirects to another article (ops/nginx/montessori-ksa.conf).
# A redirecting URL must not sit in the sitemap (Search Console: "Page with
# redirect"), be linked from the blog index or related cards, or be published.
REDIRECTED = {
    'questions-before-nursery-registration-jeddah': 'nursery-registration-documents-jeddah',
}

REWRITES = OPT/"rewrites.json"
_REWRITE_APPLIED = []

def is_noindex(a):
    return a.get('slug') in NOINDEX_SLUGS and not a.get('rewritten')

def apply_rewrites(raw_q):
    """Swap in hand-written replacements (/opt/seo/rewrites.json, shipped from
    the repo by self-update.sh) for templated articles, published or pending. Each one must
    pass the facts gate and the duplicate gate first; the article then drops
    out of NOINDEX handling. Idempotent: a rewrite is re-applied only when its
    content changes."""
    if facts is None or not isinstance(raw_q, list):
        return raw_q
    try:
        rw = json.loads(REWRITES.read_text(encoding='utf-8'))
    except Exception:
        return raw_q
    fields = ('title', 'seoTitle', 'metaDescription', 'bodyHtml', 'faq', 'wordCount')
    by_slug = {a.get('slug'): a for a in raw_q}
    for slug, new in (rw or {}).items():
        if not isinstance(new, dict):
            continue
        a = by_slug.get(slug)
        if a is None and new.get('new') and new.get('cat') and new.get('targetKeyword'):
            # A brand-new article shipped from the repo: queue it as pending;
            # the publish loop still runs the facts and duplicate gates.
            a = {'slug': slug, 'cat': new['cat'], 'targetKeyword': new['targetKeyword'],
                 'secondaryKeywords': new.get('secondaryKeywords') or [],
                 'related': new.get('related') or []}
            # ahead of older pending entries: shipped articles target gaps
            first = next((i for i, x in enumerate(raw_q) if not x.get('published')), len(raw_q))
            raw_q.insert(first, a); by_slug[slug] = a
            log(f"queued new article {slug}")
        if not a:
            continue
        tag = hashlib.sha1(json.dumps(new, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()[:12]
        if a.get('rewritten') == tag:
            continue
        cand = dict(a); cand.update({k: new[k] for k in fields if k in new})
        why = facts.check_article(cand)
        dup = duplicate_of(cand, [x for x in raw_q if x.get('published') and x.get('slug') != slug])
        if why or dup:
            log(f"rewrite rejected {slug}: {'; '.join(why) if why else 'duplicate of %s (%.2f)' % dup}")
            continue
        a.update({k: new[k] for k in fields if k in new})
        a['rewritten'] = tag
        if a.get('published'):
            a['modified'] = datetime.date.today().isoformat()
        _REWRITE_APPLIED.append(slug)
        log(f"rewrite applied {slug}")
    return raw_q

_DATED_AUTO = re.compile(r'-20\d{6}$')

# One-off wording fixes for published articles written before the official
# stage ladder (2026-09-13): our programmes named «التمهيدي والروضة», or an
# official name next to the wrong ages in a form the gate could not read.
# Applied to bodyHtml and FAQ after the rewrites; a slug whose result fails
# the facts gate is left untouched. Idempotent: an absent old string is a no-op.
TEXT_FIXES = {
 "bilingual-education-benefits-children": [
  [
   "وتقدّم برامج ما قبل التمهيدي (Pre-KG) والتمهيدي والروضة والبرنامج الصيفي",
   "وتقدّم مراحل ما قبل الروضة (سنتان–٣) والمستوى الأول (٣–٤) والمستوى الثاني (٤–٥) والتمهيدي (٥–٦) والبرنامج الصيفي"
  ],
  [
   "ولهذا تُعدّ سنوات الحضانة (من عام إلى عامين)، ثم التمهيدي (من عامين إلى أربعة)، والروضة (من أربعة إلى ستة) أنسب الأوقات على الإطلاق للبدء. وهذه بالضبط هي المراحل الثلاث التي نغطّيها",
   "ولهذا تُعدّ السنوات من سنتين إلى ٥ سنوات أنسب الأوقات على الإطلاق للبدء. وهذه بالضبط هي المراحل التي نغطّيها"
  ],
  [
   "ولهذا تُعدّ سنوات الحضانة والتمهيدي والروضة أنسب وقت للبدء.",
   "ولهذا تُعدّ سنوات ما قبل الروضة والمستوى الأول والمستوى الثاني أنسب وقت للبدء."
  ]
 ],
 "nursery-al-safa-jeddah": [
  [
   "<li><strong>ما قبل التمهيدي (سنتان):</strong> رعاية دافئة وأنشطة حسّية وحركية تناسب أولى خطوات الاستقلال.</li>\n<li><strong>التمهيدي (من ثلاث إلى أربع سنوات):</strong> مرحلة تفتّح اللغة والفضول، بأنشطة الحياة العملية والتمهيد للقراءة والحساب.</li>\n<li><strong>الروضة (من أربع إلى خمس سنوات):</strong> إعداد حقيقي للمدرسة: قراءة وكتابة ورياضيات محسوسة ومهارات اجتماعية.</li>",
   "<li><strong>ما قبل الروضة (سنتان–٣):</strong> رعاية دافئة وأنشطة حسّية وحركية تناسب أولى خطوات الاستقلال.</li>\n<li><strong>المستوى الأول (٣–٤):</strong> مرحلة تفتّح اللغة والفضول، بأنشطة الحياة العملية والتمهيد للقراءة والحساب.</li>\n<li><strong>المستوى الثاني (٤–٥):</strong> إعداد حقيقي للمدرسة: قراءة وكتابة ورياضيات محسوسة ومهارات اجتماعية.</li>"
  ]
 ],
 "picky-eater-child": [
  [
   "نقدّم برامج الحضانة والتمهيدي والروضة بمنهج منتسوري",
   "نقدّم مراحل ما قبل الروضة والمستوى الأول والمستوى الثاني والتمهيدي بمنهج مونتيسوري للأطفال من سنتين إلى ٥ سنوات"
  ]
 ],
 "nursery-ash-shati-jeddah": [
  [
   "برنامج الروضة لدينا يهيّئ الطفل للمدرسة الابتدائية بثقة",
   "مرحلة التمهيدي (٥–٦) لدينا تهيّئ الطفل للمدرسة الابتدائية بثقة"
  ]
 ],
 "is-nursery-good-for-child": [
  [
   "في برنامج الروضة لدينا",
   "في المستوى الثاني (٤–٥) والتمهيدي (٥–٦) لدينا"
  ]
 ],
 "jeddah-nurseries-infant-care-guide": [
  [
   "بالإضافة إلى برامج التمهيدي والروضة الأساسية",
   "بالإضافة إلى مراحلنا الأساسية (ما قبل الروضة والمستوى الأول والمستوى الثاني والتمهيدي)"
  ]
 ],
 "jeddah-preschool-4-5-years-guide": [
  [
   "في مرحلتي التمهيدي والروضة.",
   "في مرحلة المستوى الثاني (٤–٥) وما يليها."
  ]
 ],
 "trusted-nursery-recommendation-jeddah": [
  [
   "<strong>برنامج التمهيدي:</strong> مخصص للأطفال من عمر ٣ إلى ٤ سنوات",
   "<strong>برنامج المستوى الأول (٣–٤):</strong> مخصص للأطفال من عمر ٣ إلى ٤ سنوات"
  ],
  [
   "<strong>برنامج الروضة:</strong> مخصص للأطفال من عمر ٤ إلى ٥ سنوات",
   "<strong>برنامج المستوى الثاني (٤–٥):</strong> مخصص للأطفال من عمر ٤ إلى ٥ سنوات"
  ]
 ],
 "best-quality-price-nursery-jeddah": [
  [
   "يجمع بين برامج الروضة والتمهيدي المتميزة",
   "يجمع بين مراحله المتميزة (ما قبل الروضة والمستوى الأول والمستوى الثاني والتمهيدي)"
  ]
 ],
 "safe-educational-nursery-options-jeddah": [
  [
   "برامج مخصصة تشمل التمهيدي والروضة والضيافة بالساعة",
   "مراحل ما قبل الروضة والمستوى الأول والمستوى الثاني والتمهيدي، إضافة إلى الضيافة بالساعة"
  ]
 ],
 "child-care-hourly-jeddah": [
  [
   "فئاتنا العمرية الثلاث نفسها",
   "مراحلنا نفسها"
  ],
  [
   "<ul>\n<li><strong>الحضانة:</strong> من سنة إلى سنتين، برعاية فائقة تناسب الأعمار الصغيرة.</li>\n<li><strong>التمهيدي:</strong> من سنتين إلى أربع سنوات، مع أنشطة تمهيدية ولغوية.</li>\n<li><strong>الروضة:</strong> من أربع إلى ست سنوات، بمهارات ما قبل المدرسة.</li>\n</ul>",
   "<ul>\n<li><strong>ما قبل الروضة (سنتان–٣):</strong> رعاية دافئة وأنشطة حسّية وحركية تناسب أولى خطوات الاستقلال.</li>\n<li><strong>المستوى الأول (٣–٤):</strong> أنشطة الحياة العملية واللغة والتمهيد للقراءة والحساب.</li>\n<li><strong>المستوى الثاني (٤–٥):</strong> مهارات ما قبل المدرسة: قراءة وكتابة ورياضيات محسوسة.</li>\n</ul>"
  ],
  [
   "نحن حضانة معتمدة نالت تقييم",
   "نحن حضانة نالت تقييم"
  ],
  [
   "ضيافة أطفال في جدة | حضانة بالساعة آمنة بحي الفيصلية",
   "حضانة بالساعة في جدة | ضيافة أطفال مرنة للموظفات بحي الفيصلية"
  ],
  [
   "تبحثين عن ضيافة اطفال جدة؟ روضة كوكب الطفل الحر بالساعة في حي الفيصلية",
   "تبحثين عن حضانة بالساعة في جدة؟ روضة كوكب الطفل الحر تقدّم ضيافة أطفال بالساعة في حي الفيصلية"
  ],
  [
   "<strong>ضيافة اطفال جدة</strong> هي الحل الآمن",
   "<strong>حضانة بالساعة في جدة</strong> هي الحل الآمن"
  ]
 ],
 "nursery-entry-age-guide": [
  [
   "<h2>المستوى الأول والمستوى الثاني من 3 إلى 5 سنوات</h2>",
   "<h2>المستوى الأول (٣–٤) والمستوى الثاني (٤–٥)</h2>"
  ]
 ]
}

def apply_text_fixes(raw_q):
    if facts is None or not isinstance(raw_q, list):
        return raw_q
    for a in raw_q:
        pairs = TEXT_FIXES.get(a.get('slug'))
        if not pairs or not a.get('published'):
            continue
        cand = json.loads(json.dumps(a, ensure_ascii=False))
        hit = 0
        for old, new in pairs:
            for k in ('bodyHtml', 'title', 'seoTitle', 'metaDescription'):
                if old in (cand.get(k) or ''):
                    cand[k] = cand[k].replace(old, new); hit += 1
            for item in cand.get('faq') or []:
                for k in ('q', 'a'):
                    if isinstance(item, dict) and old in (item.get(k) or ''):
                        item[k] = item[k].replace(old, new); hit += 1
        if not hit:
            continue
        why = facts.check_article(cand)
        if why:
            log(f"text fix rejected {a['slug']}: {'; '.join(why)}")
            continue
        a.update(cand)
        a['modified'] = datetime.date.today().isoformat()
        _REWRITE_APPLIED.append(a['slug'])
        log(f"text fix applied {a['slug']} ({hit} replacement(s))")
    return raw_q

def prune_templated_pending(raw_q):
    """Drop unpublished entries made by the old dated auto-refill
    (slug ends in -YYYYMMDD). They are one template with the district name
    swapped, so the duplicate gate blocks them forever and the daily
    blocked-articles email never stops."""
    if not isinstance(raw_q, list):
        return raw_q
    keep = [a for a in raw_q if a.get('published') or not (
        _DATED_AUTO.search(a.get('slug', '')) or a.get('slug') in REDIRECTED)]
    if len(keep) != len(raw_q):
        log(f"pruned {len(raw_q) - len(keep)} dated auto-generated pending articles")
        _REWRITE_APPLIED.append('__pruned__')
    return keep

def prune_noindex_from_sitemap(q):
    smp = ROOT/"sitemap.xml"
    try:
        sm = smp.read_text()
    except Exception:
        return
    new = sm
    for a in q:
        slug = a.get('slug')
        if slug in REDIRECTED or (a.get('published') and slug in CANONICAL_TO):
            new = re.sub(r'\s*<url>\s*<loc>[^<]*/blog/%s/</loc>.*?</url>' % re.escape(slug), '', new, flags=re.S)
            continue
        if not a.get('published') or slug not in NOINDEX_SLUGS:
            continue
        if is_noindex(a):
            new = re.sub(r'\s*<url>\s*<loc>[^<]*/blog/%s/</loc>.*?</url>' % re.escape(slug), '', new, flags=re.S)
        elif f'/blog/{slug}/<' not in new:
            new = new.replace('</urlset>',
                f'  <url>\n    <loc>{SITE}/blog/{slug}/</loc>\n    <lastmod>{datetime.date.today().isoformat()}</lastmod>\n'
                f'    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n</urlset>')
    if new != sm:
        smp.write_text(new, encoding='utf-8')
        log(f"sitemap: noindex sync {len(re.findall('<loc>', sm))} -> {len(re.findall('<loc>', new))} urls")

def log(m):
    line = f"{datetime.datetime.now().isoformat(timespec='seconds')}  {m}"
    print(line)
    try: LOG.open('a').write(line+"\n")
    except Exception: pass

def ar_date(d): return f"{d.day} {MONTHS[d.month-1]} {d.year}"

# ---------- HTML shells (identical to the site's blog template) ----------
def header():
    return '''<header class="mnav"><div class="mnav__in">
    <a href="/" class="row" style="gap:11px"><img src="/logo.png" alt="كوكب الطفل الحر" style="width:46px;height:46px;border-radius:13px"/>
      <span class="brand-name">كوكب الطفل الحر<small>KAWKAB AL-TIFL AL-HURR · JEDDAH</small></span></a>
    <nav class="links"><a href="/#philosophy">رؤيتنا</a><a href="/#programs">برامجنا</a>
      <a href="/blog/" aria-current="page">المدوّنة</a><a href="/#gallery">لحظاتنا</a><a href="/#contact">تواصل</a></nav>
    <div class="mnav__cta">
      <a class="lang-toggle" href="/app/" aria-label="تطبيقات الجوال" title="تطبيقات الجوال" style="gap:5px"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>تطبيق</a>
      <a class="lang-toggle" href="/en/" lang="en" dir="ltr" aria-label="Switch to English" title="English"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M3 12h18"/><path d="M12 3c2.6 2.4 4 5.6 4 9s-1.4 6.6-4 9c-2.6-2.4-4-5.6-4-9s1.4-6.6 4-9z"/></svg>EN</a>
      <a class="btn btn--ghost btn--sm" href="/login/">دخول</a>
      <a class="btn btn--primary btn--sm" href="/#register">احجز زيارة</a>
    </div></div></header>'''

def footer():
    return '''<footer class="foot"><div class="foot__in">
    <div class="soc"><a href="https://wa.me/966541558173" target="_blank" rel="noopener" aria-label="واتساب" id="f-wa"></a></div>
    <nav class="fnav"><a href="/">الرئيسية</a><a href="/blog/">المدوّنة</a><a href="/#programs">برامجنا</a>
      <a href="/#register">احجز زيارة</a><a href="/partners/">شركاؤنا</a><a href="/privacy/">الخصوصية</a><a href="/login/">دخول</a></nav>
    <div class="cr">كوكب الطفل الحر © ٢٠٢٦ — جدة، المملكة العربية السعودية · جميع الحقوق محفوظة</div>
  </div></footer>
<button id="totop" aria-label="للأعلى"></button>
<script src="/assets/app.js?v=48"></script>
<script>(function(){var I=NS.icon;var e=document.getElementById('f-wa');if(e)e.innerHTML=I('whatsapp');var tt=document.getElementById('totop');if(tt){tt.innerHTML=I('arrowUp');addEventListener('scroll',function(){tt.classList.toggle('show',scrollY>500)},{passive:true});tt.addEventListener('click',function(){scrollTo({top:0,behavior:'smooth'})});}})();</script>
<script src="/assets/bot.js?v=2" defer></script>'''

def cta(kw):
    return (f'<aside class="cta-card"><div class="cta-card__glow"></div>'
      f'<h2>هل تبحثين عن {esc(kw)}؟</h2>'
      f'<p>كوكب الطفل الحر في حي الفيصلية بجدة، نستقبل الأطفال من سنتين إلى ٥ سنوات — بيئة تعليمية آمنة مع القرآن والعربية والإنجليزية، بتقييم <strong>4.7★</strong> على خرائط جوجل. احجزي جولة تعريفية وشاهدي بيئتنا المُعدّة عن قرب.</p>'
      f'<div class="cta-card__btns"><a class="btn btn--primary btn--lg" href="/#register">احجزوا زيارة</a>'
      f'<a class="btn btn--soft btn--lg" href="https://wa.me/966541558173" target="_blank" rel="noopener">تواصل واتساب</a></div></aside>')

def faq_block(faq):
    items=''.join(f'<details class="faq__item"><summary>{esc(f["q"])}</summary>'
                  f'<div class="faq__a"><p>{esc(f["a"])}</p></div></details>' for f in (faq or []))
    return f'<section class="faq" aria-label="الأسئلة الشائعة"><h2>الأسئلة الشائعة</h2>{items}</section>'

def related_block(a, allslugs, titles):
    # Link only to articles that are actually published. Queue entries that
    # are unpublished (or were dropped from the queue) have no page and 404.
    allslugs={s for s in allslugs if titles.get(s,{}).get('pub') and s not in REDIRECTED}
    rel=[s for s in (a.get('related') or []) if s in allslugs and s!=a['slug']][:3]
    if len(rel)<3:
        # allslugs is a set, so iterating it directly picked different fillers
        # on every run: 42 published articles had their internal links
        # reshuffled daily. Order by a hash of (this slug, candidate) so the
        # choice is stable per article yet still spreads links across the site.
        fillers=sorted(allslugs, key=lambda s: hashlib.sha1(
            (a['slug']+'|'+s).encode('utf-8')).hexdigest())
        for s in fillers:
            if s!=a['slug'] and s not in rel: rel.append(s)
            if len(rel)>=3: break
    rel=rel[:3]
    cards=''.join(f'<a class="rel-card" href="/blog/{s}/"><span class="rel-card__cat">{esc(CATN.get(titles.get(s,{}).get("cat","dev")))}</span>'
        f'<span class="rel-card__title">{esc(titles.get(s,{}).get("title",s))}</span>'
        f'<span class="rel-card__go">اقرأ المقال ←</span></a>' for s in rel)
    return f'<nav class="related" aria-label="مقالات ذات صلة"><h2>مقالات قد تهمّك</h2><div class="related__grid">{cards}</div></nav>'

def modified_iso(a, iso):
    """Last content change (rewrite or text fix), never before the publish date."""
    m = str(a.get('modified') or '')[:10]
    return m if m > iso else iso

def jsonld(a, iso):
    url=f"{SITE}/blog/{a['slug']}/"; cat=CATN.get(a['cat'],'')
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    j=lambda o: json.dumps(o,ensure_ascii=False,separators=(',',':'))
    bp={"@context":"https://schema.org","@type":"BlogPosting","@id":url+"#article","headline":a['seoTitle'],
        "description":a['metaDescription'],"inLanguage":"ar","url":url,"mainEntityOfPage":{"@type":"WebPage","@id":url},
        "datePublished":iso,"dateModified":modified_iso(a, iso),
        "author":{"@type":"Organization","@id":SITE+"/#business","name":"كوكب الطفل الحر","url":SITE+"/"},
        "publisher":{"@type":"Organization","@id":SITE+"/#business","name":"كوكب الطفل الحر","logo":{"@type":"ImageObject","url":SITE+"/logo.png"}},
        "image":a['imageUrl'],"keywords":", ".join(k for k in kws if k),"articleSection":cat,"wordCount":a.get('wordCount')}
    fq={"@context":"https://schema.org","@type":"FAQPage","mainEntity":[
        {"@type":"Question","name":f['q'],"acceptedAnswer":{"@type":"Answer","text":f['a']}} for f in (a.get('faq') or [])]}
    bc={"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
        {"@type":"ListItem","position":1,"name":"الرئيسية","item":SITE+"/"},
        {"@type":"ListItem","position":2,"name":"المدوّنة","item":SITE+"/blog/"},
        {"@type":"ListItem","position":3,"name":a['title'],"item":url}]}
    return (f'<script type="application/ld+json">{j(bp)}</script>\n'
            f'<script type="application/ld+json">{j(fq)}</script>\n'
            f'<script type="application/ld+json">{j(bc)}</script>')

# وسم جوجل أناليتكس — منسوخ حرفياً من صفحات الموقع كي تنطبق عليه
# بصمات CSP الموجودة في mk-csp-parts.conf دون أي تعديل عليها.
GA_TAG = '<!-- Google tag (gtag.js) -->\n<script>addEventListener("load",function(){setTimeout(function(){var s=document.createElement("script");s.async=1;s.src="https://www.googletagmanager.com/gtag/js?id=G-H0856C2N0T";document.head.appendChild(s);},1500);});</script>\n<script>\nwindow.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}\ngtag(\'js\',new Date());gtag(\'config\',\'G-H0856C2N0T\');\naddEventListener(\'click\',function(e){var a=e.target.closest&&e.target.closest(\'a\');if(!a)return;var h=a.getAttribute(\'href\')||\'\';if(h.indexOf(\'wa.me\')>-1||h.indexOf(\'whatsapp\')>-1){gtag(\'event\',\'whatsapp_click\',{transport_type:\'beacon\'});}else if(h.indexOf(\'#register\')>-1){gtag(\'event\',\'book_visit_click\');}},true);\naddEventListener(\'submit\',function(e){if(e.target&&e.target.id===\'regform\'){gtag(\'event\',\'lead_form_submit\');}},true);\n</script>\n<!-- end Google tag -->'


# Contextual internal links: the first mention of a topic in a paragraph or
# list item links to the article that covers it. Only published, indexable
# targets; never the article itself; at most INLINE_LINK_MAX per article.
INLINE_LINKS = [
    ('روضة كوكب الطفل الحر', '/'),
    # pillar pages first, so they collect the most contextual links
    # The homepage is the page for this term (SEO plan 2026-10-02): the
    # contextual links that used to go to the top-rated article now carry
    # the money term to the page that targets it.
    ('حضانة أطفال في جدة', '/'),
    ('روضة أطفال في جدة', 'kindergarten-rawda-jeddah'),
    ('مركز أطفال مونتيسوري', 'montessori-children-center-jeddah'),
    ('الفرق بين التمهيدي والروضة', 'pre-kg-vs-kg-difference'),
    ('معايير أمان الحضانة', 'nursery-safety-checklist-jeddah'),
    ('التسجيل في الحضانة', 'nursery-registration-jeddah-new-year'),
    ('أول يوم في الحضانة', 'first-day-nursery-separation-anxiety'),
    ('قلق الانفصال', 'nursery-separation-anxiety-jeddah-plan'),
    ('الحياة العملية', 'montessori-practical-life-skills-nursery'),
    ('الأنشطة الحسية', 'montessori-sensorial-activities-nursery'),
    ('المهارات الحركية الدقيقة', 'preschool-fine-motor-skills-montessori'),
    ('اللعب الحركي', 'preschool-gross-motor-play-jeddah'),
    ('جاهزية الطفل', 'nursery-readiness-signs-child-jeddah'),
    ('الأم العاملة', 'nursery-routine-for-working-mothers-jeddah'),
    ('رسوم الحضانة', 'nursery-fees-value-jeddah-guide'),
    ('الزيارة التعريفية', 'nursery-visit-checklist-jeddah'),
    ('التواصل مع الأهل', 'nursery-communication-with-parents-jeddah'),
    ('استقلال الطفل', 'child-independence-nursery-jeddah'),
    ('المهارات الاجتماعية', 'child-social-skills-nursery-jeddah'),
    ('تركيز الطفل', 'child-focus-attention-montessori'),
    ('المجموعات الصغيرة', 'nursery-small-groups-jeddah'),
    ('روتين اليوم', 'montessori-classroom-routine-jeddah'),
    ('الحضانة التقليدية', 'montessori-vs-traditional-nursery-jeddah'),
    ('أنشطة الرياضيات', 'montessori-math-activities-preschool-jeddah'),
    ('أنشطة اللغة', 'montessori-language-activities-arabic-english'),
    ('مواد مونتيسوري', 'montessori-activities-at-home'),
    ('معلمة مونتيسوري', 'qualified-teachers-nursery-jeddah'),
    ('أخطاء شائعة عند البحث', 'how-to-choose-nursery-jeddah'),
    ('تعليم القرآن', 'quran-nursery-jeddah-montessori'),
    ('كاميرات المراقبة', 'nursery-with-cctv-cameras-jeddah'),
    ('كاميرات مراقبة', 'nursery-with-cctv-cameras-jeddah'),
    ('حي الفيصلية', '/'),
    ('الأسئلة الشائعة', 'nursery-faq-jeddah-parents'),
    ('منهج مونتيسوري', 'what-is-montessori-method'),
    # SEO plan 2026-10-02: the fees and admissions pages the homepage now
    # links to, and the districts hub, collect the generic mentions.
    ('أسعار الحضانات', 'nursery-prices-jeddah'),
    ('رسوم الحضانات', 'nursery-prices-jeddah'),
    ('أوراق التسجيل', 'nursery-registration-documents-jeddah'),
    ('حضانات جدة', 'jeddah-nurseries-districts-guide'),
    ('أحياء جدة', 'jeddah-nurseries-districts-guide'),
    # Guides queued on 2026-10-02 (rewrites.json, new:true): ok() links a
    # target only once it is published, so these stay inert until then.
    ('الطفل العنيد', 'stubborn-child-4-years-montessori'),
    ('العناد', 'stubborn-child-4-years-montessori'),
    ('ذكاء الطفل', 'child-intelligence-signs-2-3-years'),
    ('التعبير عن مشاعره', 'child-express-feelings-activities'),
    ('التعبير عن المشاعر', 'child-express-feelings-activities'),
    ('مشاعر الطفل', 'child-express-feelings-activities'),
    ('الألعاب الحركية', 'movement-games-kids-home-no-tools'),
    ('ألعاب حركية', 'movement-games-kids-home-no-tools'),
    ('مراكز تعليمية', 'educational-centers-kids-jeddah'),
    ('مركز تعليمي', 'educational-centers-kids-jeddah'),
    ('شهر رمضان', 'ramadan-activities-kids-2027'),
    # Montessori head terms the homepage ranks for: lowest priority, so a
    # block with a more specific topic links that topic instead; the home
    # link is still at most one per article (target used once).
    ('حضانة مونتيسوري', '/'),
    ('روضة مونتيسوري', '/'),
]
INLINE_LINK_MAX = 5
_BLOCK = re.compile(r'(<(p|li)\b[^>]*>)(.*?)(</\2>)', re.S)

def add_inline_links(a, titles):
    html = a.get('bodyHtml') or ''
    me = a.get('slug')
    used, n = set(), 0
    def ok(target):
        if target == '/':
            return True
        return target != me and titles.get(target, {}).get('pub') and \
            not is_noindex({'slug': target, 'rewritten': titles.get(target, {}).get('rw')})
    def block(m):
        nonlocal n
        inner = m.group(3)
        if '<a ' in inner or n >= INLINE_LINK_MAX:
            return m.group(0)
        for phrase, target in INLINE_LINKS:
            if target in used or not ok(target):
                continue
            i = inner.find(phrase)
            if i < 0:
                continue
            # skip a phrase that sits inside a tag attribute
            if inner.rfind('<', 0, i) > inner.rfind('>', 0, i):
                continue
            href = '/' if target == '/' else f'/blog/{target}/'
            inner = inner[:i] + f'<a href="{href}">{phrase}</a>' + inner[i+len(phrase):]
            used.add(target); n += 1
            break
        return m.group(1) + inner + m.group(4)
    return _BLOCK.sub(block, html)

def updated_html(a, iso):
    m = modified_iso(a, iso)
    if m == iso:
        return ''
    try:
        md = datetime.date.fromisoformat(m)
    except ValueError:
        return ''
    return f'<span class="am-dot">·</span><span>آخر تحديث <time datetime="{m}">{esc(ar_date(md))}</time></span>'

def render_article(a, iso, d, allslugs, titles):
    cat=CATN.get(a['cat'],''); url=f"{SITE}/blog/{a['slug']}/"
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    rt=max(4, round((a.get('wordCount') or 1100)/180))
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
{GA_TAG}
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(a['seoTitle'])}</title>
<meta name="description" content="{esc(a['metaDescription'])}"/>
<meta name="keywords" content="{esc(', '.join(k for k in kws if k))}"/>
<meta name="author" content="كوكب الطفل الحر"/>
<meta name="robots" content="{'noindex, follow' if is_noindex(a) else 'index, follow, max-image-preview:large'}"/>
<meta name="theme-color" content="#184e3e"/>
<link rel="canonical" href="{SITE + CANONICAL_TO[a["slug"]] if a["slug"] in CANONICAL_TO else url}"/>
<link rel="alternate" hreflang="ar" href="{url}"/><link rel="alternate" hreflang="x-default" href="{url}"/>
<meta name="geo.region" content="SA-02"/><meta name="geo.placename" content="Jeddah"/><meta name="geo.position" content="21.5795281;39.194829"/>
<meta property="og:type" content="article"/><meta property="og:site_name" content="كوكب الطفل الحر"/>
<meta property="og:title" content="{esc(a['seoTitle'])}"/><meta property="og:description" content="{esc(a['metaDescription'])}"/>
<meta property="og:url" content="{url}"/><meta property="og:image" content="{esc(a['imageUrl'])}"/><meta property="og:image:alt" content="{esc(a['imageAlt'])}"/><meta property="og:locale" content="ar_SA"/>
<meta property="article:published_time" content="{iso}"/><meta property="article:section" content="{esc(cat)}"/>
<meta name="twitter:card" content="summary_large_image"/><meta name="twitter:title" content="{esc(a['seoTitle'])}"/>
<meta name="twitter:description" content="{esc(a['metaDescription'])}"/><meta name="twitter:image" content="{esc(a['imageUrl'])}"/><meta name="twitter:image:alt" content="{esc(a['imageAlt'])}"/>
<link rel="icon" href="/logo.png"/><link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
<link rel="stylesheet" href="/assets/fonts.css?v=2"/><link rel="stylesheet" href="/assets/app.css?v=10"/><link rel="stylesheet" href="/assets/blog.css?v=1"/>
{jsonld(a, iso)}
</head><body class="blog-body">
{header()}
<main class="container article-wrap">
  <nav class="crumbs" aria-label="مسار التنقّل"><a href="/">الرئيسية</a><span>›</span><a href="/blog/">المدوّنة</a><span>›</span><span class="crumbs__cur">{esc(cat)}</span></nav>
  <article class="article"><header class="article__head">
    <a class="article__cat" href="/blog/#{a['cat']}">{esc(cat)}</a>
    <h1>{esc(a['title'])}</h1>
    <div class="article__meta"><span class="am-author"><img src="/logo.png" alt="كوكب الطفل الحر"/> فريق كوكب الطفل الحر</span>
      <span class="am-dot">·</span><time datetime="{iso}">{esc(ar_date(d))}</time>{updated_html(a, iso)}<span class="am-dot">·</span><span>{rt} دقائق قراءة</span></div>
  </header>
  <div class="article__body">
<figure class="article-hero"><img src="{esc(a['imageUrl'])}" alt="{esc(a['imageAlt'])}" width="1200" height="800" loading="eager" fetchpriority="high"/></figure>
{add_inline_links(a, titles)}
  </div>
  {faq_block(a.get('faq'))}
  {cta(a.get('targetKeyword',''))}
  {related_block(a, allslugs, titles)}
  </article>
</main>
{footer()}
</body></html>'''

def announce_rewrites(q, today):
    """Rewritten articles changed in place: bump their sitemap <lastmod> so
    Google recrawls them, and notify IndexNow (Bing, Yandex...). Pending
    articles are skipped; they are announced when published."""
    live = {a.get('slug') for a in q if a.get('published')}
    slugs = [x for x in _REWRITE_APPLIED if x in live]
    if not slugs:
        return
    smp = ROOT/"sitemap.xml"
    try:
        sm = smp.read_text()
        new = sm
        for slug in slugs:
            new = re.sub(r'(<loc>[^<]*/blog/%s/</loc>\s*<lastmod>)[^<]*(</lastmod>)' % re.escape(slug),
                         r'\g<1>%s\g<2>' % today.isoformat(), new)
        if new != sm:
            smp.write_text(new, encoding='utf-8')
    except Exception as ex:
        log(f"sitemap lastmod update failed: {ex}")
    sent = 0
    for slug in slugs[:50]:
        if indexnow(f"{SITE}/blog/{slug}/") is not None:
            sent += 1
    log(f"announced {len(slugs)} rewritten articles (indexnow ok={sent})")

def indexnow(url):
    try:
        key=KEYF.read_text().strip()
        payload={"host":"montessori-ksa.com","key":key,
                 "keyLocation":f"{SITE}/{key}.txt","urlList":[url]}
        req=urllib.request.Request("https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode(),headers={"Content-Type":"application/json; charset=utf-8"})
        r=urllib.request.urlopen(req,timeout=20); return r.status
    except Exception as ex:
        log(f"indexnow err: {ex}"); return None

def email(subject, html):
    try:
        req=urllib.request.Request(WEBHOOK,data=json.dumps({"subject":subject,"html":html}).encode(),
            headers={"Content-Type":"application/json"})
        urllib.request.urlopen(req,timeout=20); return True
    except Exception as ex:
        log(f"email err: {ex}"); return False

def health():
    ok={}
    for path in ("/","/blog/","/sitemap.xml","/robots.txt"):
        try:
            r=urllib.request.urlopen(SITE+path,timeout=15); ok[path]=r.status
        except Exception as e: ok[path]=str(e)
    return ok

def _get(path):
    try:
        r=urllib.request.urlopen(SITE+path,timeout=15)
        return r.status, r.read().decode('utf-8','replace')
    except Exception as e:
        return None, str(e)

def seo_healthcheck():
    """فحص صحّة سيو يومي (مكتبة قياسية فقط) — يمسك مشاكل الموقع قبل ما تضرّ الترتيب.
    يرجّع (rows, worst) حيث worst ∈ {ok,warn,fail}. أهم فحص: حارس التقييم المزيّف."""
    rows=[]; rank={'ok':0,'warn':1,'fail':2}
    def add(l,s,d): rows.append((l,s,d))
    # 1) الصفحتان الرئيسيتان: لا تقييم مزيّف + سكيمّا + عناصر السيو
    for path,lbl in (("/","الرئيسية"),("/en/","الإنجليزية")):
        st,b=_get(path)
        if st!=200: add(f"تحميل {lbl}","fail",f"HTTP {st}"); continue
        if ("aggregateRating" in b) or ("reviewCount" in b):
            add(f"حارس التقييم المزيّف ({lbl})","fail","رجع aggregateRating — يجب إزالته فوراً")
        else:
            add(f"حارس التقييم المزيّف ({lbl})","ok","نظيف — لا تقييم مُلفّق")
        if ('"ChildCare"' in b) or ('"Preschool"' in b):
            add(f"سكيمّا الحضانة ({lbl})","ok","موجودة")
        else:
            add(f"سكيمّا الحضانة ({lbl})","warn","لم أجد Preschool/ChildCare")
        miss=[n for n,c in (("العنوان","<title>"),("الوصف",'name="description"'),
                            ("canonical",'rel="canonical"'),("hreflang",'hreflang=')) if c not in b]
        add(f"عناصر السيو ({lbl})","ok" if not miss else "warn","مكتملة" if not miss else "ناقص: "+"، ".join(miss))
    # 2) خريطة الموقع
    st,b=_get("/sitemap.xml")
    if st==200 and "<urlset" in b:
        fresh=re.findall(r"<lastmod>([^<]+)</lastmod>", b)
        add("خريطة الموقع","ok",f"{b.count('<url>')} رابط · آخر تحديث {max(fresh) if fresh else '؟'}")
    else:
        add("خريطة الموقع","fail",f"HTTP {st}")
    # 3) robots
    st,b=_get("/robots.txt")
    add("robots.txt","ok" if (st==200 and "Sitemap:" in b and "/blog/" in b) else "warn",
        "يسمح بالمدوّنة ويشير للخريطة" if st==200 else f"HTTP {st}")
    # 4) فهرس المدوّنة + آخر مقالين منشورين
    st,_=_get("/blog/")
    add("فهرس المدوّنة","ok" if st==200 else "fail",f"HTTP {st}")
    try:
        pub=sorted([a for a in json.loads(QUEUE.read_text()) if a.get('published')],
                   key=lambda a:a.get('published'),reverse=True)[:2]
    except Exception: pub=[]
    for a in pub:
        st,b=_get(f"/blog/{a['slug']}/")
        if st!=200: add(f"مقال «{a['slug']}»","fail",f"HTTP {st}"); continue
        if 'noindex' in b.lower(): add(f"مقال «{a['slug']}»","fail","يحتوي noindex!")
        elif 'application/ld+json' not in b: add(f"مقال «{a['slug']}»","warn","بلا JSON-LD")
        else: add(f"مقال «{a['slug']}»","ok","قابل للفهرسة + سكيمّا")
    # 6) فحص الحقائق على المقالات المنشورة — نفس قواعد الحاجز قبل النشر
    # ثلاث حالات (قرار 2026-09-13 رقم 1): فشل فقط لو فئات أعمار المراحل باقية،
    # تحذير للفئات المؤجلة (سعر/دوام/مراجعات...) بلا إنذار يومي دائم
    if facts is None:
        add('فحص الحقائق', 'fail',
            'تعذّر تحميل موديول الحقائق: %s — النشر متوقف' % FACTS_IMPORT_ERROR)
    else:
        IN_SCOPE_MARKERS = ('عمر مرحلة خاطئ', '«الروضة» مقترنة بعمر مرحلة',
                             'مرحلة غير موجودة', 'عدد البرامج')
        viol = facts.audit_dir(str(ROOT/'blog'))
        in_scope = [(p, w) for p, w in viol
                    if any(any(mk in r for mk in IN_SCOPE_MARKERS) for r in w)]
        deferred = [(p, w) for p, w in viol if (p, w) not in in_scope]
        if in_scope:
            add('فحص الحقائق', 'fail',
                '%d مقالاً يخالف حقائق المنشأة (أعمار المراحل): %s'
                % (len(in_scope), ', '.join(pathlib.Path(p).parent.name for p, _ in in_scope[:5])))
        elif deferred:
            add('فحص الحقائق', 'warn',
                '%d مقالاً قديماً بمخالفات مؤجلة (سعر/دوام/مراجعات) — لا حاجة لتدخّل يومي'
                % len(deferred))
        else:
            add('فحص الحقائق', 'ok', 'كل المقالات المنشورة مطابقة')
    worst={0:'ok',1:'warn',2:'fail'}[max((rank[s] for _,s,_ in rows), default=0)]
    return rows, worst

def seo_health_html(rows):
    cm={'ok':('#2a7d61','✅'),'warn':('#a86f27','⚠️'),'fail':('#c0392b','⛔')}
    tr="".join(
        f'<tr><td style="padding:6px 10px;border-bottom:1px solid #eee">{cm[s][1]} {esc(l)}</td>'
        f'<td style="padding:6px 10px;border-bottom:1px solid #eee;color:{cm[s][0]}">{esc(d)}</td></tr>'
        for l,s,d in rows)
    return f'<table style="width:100%;border-collapse:collapse;font-size:13.5px">{tr}</table>'

def _patch_file(path, transform):
    try:
        if not path.exists():
            return False
        old = path.read_text(encoding='utf-8')
        new = transform(old)
        if new != old:
            path.write_text(new, encoding='utf-8')
        return new != old
    except Exception as ex:
        log(f"repair skipped {path}: {ex}")
        return False

def _registration_script(english=False):
    if english:
        messages = ("Your request was received. We will contact you soon.",
                    "Unable to submit the request right now.")
    else:
        messages = ("تم استلام طلبك وسنتواصل معك قريباً.",
                    "تعذر إرسال الطلب حالياً.")
    return f'''<script id="montessori-registration-fix">
(function(){{
  var f=document.getElementById('regform');
  if(!f || f.dataset.fixed==='1') return;
  f.dataset.fixed='1';
  f.method='post';
  f.action='https://odoo.montessori-ksa.com/register-visit';
  f.addEventListener('submit',function(ev){{
    ev.preventDefault();
    var b=f.querySelector('[type="submit"]'),m=document.getElementById('reg-msg');
    if(b) b.disabled=true;
    fetch(f.action,{{method:'POST',headers:{{'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8'}},
      body:new URLSearchParams(new FormData(f)),credentials:'omit'}})
      .then(function(r){{return r.json();}})
      .then(function(x){{if(m)m.textContent=x.ok?'{messages[0]}':(x.error||'{messages[1]}');if(x.ok)f.reset();}})
      .catch(function(){{if(m)m.textContent='{messages[1]}';}})
      .finally(function(){{if(b)b.disabled=false;}});
  }});
}})();
</script>'''

def _pwa_head():
    """Shared PWA metadata for public pages, including the shared homepage."""
    return '''<!-- montessori-pwa-head -->
<link rel="manifest" href="/manifest.webmanifest"/>
<link rel="apple-touch-icon" href="/apple-touch-icon.png"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>
<meta name="apple-mobile-web-app-title" content="كوكب الطفل"/>
'''

def _pwa_mobile_style():
    return '''<style id="montessori-mobile-home-fix">
@media(max-width:860px){
  .hero__in{grid-template-columns:minmax(0,1fr);min-width:0;}
  .hero__in>*{min-width:0;max-width:100%;}
  .hero__text{width:auto;min-width:0;max-width:100%;}
  .hero h1{max-width:100%;overflow-wrap:anywhere;}
  .hero h1 .em{white-space:normal!important;overflow-wrap:anywhere;}
  .hero__art{width:100%;max-width:100%;}
}
</style>'''

def _pwa_script():
    """Load the install helper after the page so Android and iOS share one flow."""
    return '<script id="montessori-pwa-fix" src="/assets/install.js?v=3" defer></script>'

# Key guides for AI assistants, in priority order; only pages that exist on
# disk are listed so llms.txt never points at a 404.
LLMS_GUIDES = [
    ('geo-montessori-nursery-jeddah-brand-answers', 'روضة كوكب الطفل الحر — كل المعلومات في صفحة واحدة'),
    ('nursery-faq-jeddah-parents', 'أسئلة شائعة عن الحضانة في جدة (٢٠ سؤالًا)'),
    ('ai-search-answer-nursery-jeddah', 'أفضل حضانة مونتيسوري في جدة — معايير الاختيار'),
    ('montessori-children-center-jeddah', 'مركز أطفال مونتيسوري في جدة'),
    ('montessori-nursery-faisaliyah-jeddah-details', 'حضانة مونتيسوري في حي الفيصلية — الموقع والعمر والدوام'),
    ('what-is-montessori-method', 'ما هو منهج مونتيسوري؟'),
    ('nursery-near-me-jeddah', 'حضانة قريبة مني في جدة — كيف تختارين'),
    ('nursery-for-2-year-old-jeddah-montessori', 'حضانة لطفل عمره سنتان'),
    ('nursery-for-3-year-old-jeddah-montessori', 'حضانة لطفل عمره ٣ سنوات'),
    ('prekg-for-4-year-old-jeddah-montessori', 'طفل الرابعة: المستوى الثاني'),
    ('nursery-fees-value-jeddah-guide', 'رسوم الحضانة في جدة — كيف تقيّمين القيمة'),
    ('nursery-visit-checklist-jeddah', 'قائمة الزيارة التعريفية للحضانة'),
    ('nursery-separation-anxiety-jeddah-plan', 'خطة أسبوعي التكيّف وقلق الانفصال'),
    ('how-to-choose-nursery-jeddah', 'كيف تختارين حضانة في جدة'),
    ('jeddah-nurseries-districts-guide', 'دليل حضانات جدة بالأحياء — كيف تختارين حضانة قريبة من بيتك'),
    ('nursery-prices-jeddah', 'أسعار الحضانات في جدة — كيف تُحسب الرسوم وما الذي يشمله الاشتراك'),
    ('nursery-registration-documents-jeddah', 'أوراق التسجيل في الحضانة بجدة وخطواته'),
    ('quran-nursery-jeddah-montessori', 'تعليم القرآن للأطفال في الحضانة مع العربية والإنجليزية — ما يناسب كل عمر'),
    ('bilingual-nursery-jeddah', 'حضانة ثنائية اللغة عربي وإنجليزي في جدة'),
    ('nursery-with-cctv-cameras-jeddah', 'كاميرات المراقبة في الحضانة — ما الذي يطمئنك فعلاً'),
    ('montessori-kindergarten-jeddah', 'روضة منتسوري في جدة — المنهج الحقيقي وعلاماته'),
]

# English pages are static (not queue articles); listed when present on disk.
LLMS_EN_GUIDES = [
    ('montessori-nursery-jeddah-guide', "Montessori nursery in Jeddah: a parent's guide to the method for ages 2 to 5"),
    ('daycare-in-jeddah', 'Daycare in Jeddah: the right age to start (Pre-KG from age 2), hours, and what to check'),
    ('nursery-in-jeddah', 'Nursery in Jeddah: how to compare nurseries; bilingual Arabic and English'),
    ('kindergarten-in-jeddah', 'Kindergarten in Jeddah: Pre-KG (2 to 3), KG1 (3 to 4), KG2 (4 to 5) explained'),
]

# Direct answers to the questions parents put to AI assistants, in the
# phrasing they use. Facts only (facts.py gates the whole file).
LLMS_QUICK_ANSWERS = [
    ('هل تستقبل الروضة طفلًا عمره سنتان؟',
     'نعم. مرحلة ما قبل الروضة تستقبل الأطفال من سنتين إلى ٣ سنوات، ثم المستوى الأول (٣–٤) والمستوى الثاني (٤–٥)، كلها في البيئة نفسها.'),
    ('ما المرحلة المناسبة لطفل عمره ٤ سنوات في جدة؟',
     'المستوى الثاني (٤–٥) بمنهج مونتيسوري: قراءة وكتابة ورياضيات محسوسة وتهيئة للمدرسة، مع العربية الفصحى والإنجليزية والقرآن.'),
    ('هل تجمع الروضة بين القرآن واللغة العربية والإنجليزية؟',
     'نعم. اليوم الدراسي يجمع منهج مونتيسوري الأصيل مع اللغة العربية الفصحى والإنجليزية وتعليم القرآن للأطفال من سنتين إلى ٥ سنوات.'),
    ('أين تقع الروضة وهل هي قريبة من حي الفيصلية؟',
     'الروضة في حي الفيصلية نفسه، شارع محمد عبدالكريم، جدة، وتخدم الأسر في الفيصلية والأحياء المجاورة. الدوام من الأحد إلى الخميس 08:00–13:00، مع ضيافة بالساعة.'),
    ('كيف أقارن بين حضانة مونتيسوري وحضانة أخرى في المنطقة؟',
     'انظري إلى البيئة المُعدّة، وتأهيل المعلمات، وكاميرات المراقبة، وطريقة التواصل اليومي مع الأسرة، واطلبي زيارة تعريفية قبل التسجيل. روضة كوكب الطفل الحر تقدّم كل ذلك بخبرة أكثر من ١٠ سنوات.'),
    ('Can a 2-year-old join your nursery in Jeddah?',
     'Yes. Pre-KG takes children aged 2 to 3, followed by KG1 (3 to 4) and KG2 (4 to 5). Hours are Sunday to Thursday, 08:00 to 13:00, with hourly care available.'),
    ('Do you teach in both Arabic and English?',
     'Yes. Every day combines authentic Montessori with Modern Standard Arabic, English and Quran, for children aged 2 to 5.'),
    ('What makes Kawkab Al-Tifl Al-Hurr a Montessori nursery?',
     'A prepared environment, qualified teachers, practical-life, sensorial, language and maths work, CCTV cameras, a daily parent app, more than 10 years of experience, and a 4.7/5 rating on Google Maps.'),
]

def write_llms_txt():
    """Regenerate /llms.txt from the facts in facts.py so AI assistants read
    the same stage names, ages and claims as the rest of the site."""
    lines = [
        '# روضة كوكب الطفل الحر — جدة | Kawkab Al-Tifl Al-Hurr Kindergarten, Jeddah',
        '',
        '> روضة كوكب الطفل الحر حضانة وروضة بمنهج مونتيسوري في حي الفيصلية، شارع محمد عبدالكريم، جدة. '
        'تستقبل الأطفال من سنتين إلى ٥ سنوات، وتجمع بين منهج مونتيسوري الأصيل واللغة العربية الفصحى والإنجليزية وتعليم القرآن. '
        'التقييم 4.7 من 5 على خرائط جوجل. الدوام: الأحد إلى الخميس، من الثامنة صباحًا حتى الواحدة ظهرًا.',
        '> Kawkab Al-Tifl Al-Hurr is a Montessori nursery and kindergarten in Al Faisaliyah (Mohammed Abdulkarim St), Jeddah, Saudi Arabia, '
        'for children aged 2 to 5: authentic Montessori with Modern Standard Arabic, English and Quran. '
        'Rated 4.7/5 on Google Maps, with more than 10 years of experience. Open Sunday to Thursday, 08:00 to 13:00.',
        '',
        '## حقائق أساسية / Key facts',
        '- الاسم: روضة كوكب الطفل الحر (Kawkab Al-Tifl Al-Hurr Kindergarten)',
        '- أسماء أخرى / Also known as: كوكب الطفل الحر · روضة كوكب الطفل · Kawkab Al-Tifl · Kawkab Al Tifl Al Hur · Kawkab Al-Tifl Al-Hurr',
        '- الموقع: حي الفيصلية، شارع محمد عبدالكريم، جدة، المملكة العربية السعودية',
        '- الأعمار: من سنتين إلى ٥ سنوات',
        '- المراحل: ما قبل الروضة (سنتان–٣) · المستوى الأول (٣–٤) · المستوى الثاني (٤–٥) · التمهيدي (٥–٦) · برنامج صيفي · ضيافة بالساعة',
        '- المنهج: مونتيسوري الأصيل + اللغة العربية الفصحى + الإنجليزية + تعليم القرآن',
        '- المزايا: بيئة مُعدّة، معلمات مؤهلات، كاميرات مراقبة، تطبيق تواصل يومي مع الأسرة',
        '- الخبرة: أكثر من ١٠ سنوات في تعليم الطفولة المبكرة / More than 10 years of experience',
        '- الدوام: الأحد إلى الخميس 08:00–13:00',
        '- الرسوم: تُحدَّد حسب عمر الطفل وعدد الأيام وساعات الدوام، ويُؤكَّد الرقم عبر مكالمة أو زيارة',
        '- التواصل: واتساب +966541558173 · https://montessori-ksa.com',
        '- تيك توك: https://www.tiktok.com/@montessori_nursery23',
        '',
        '## الصفحات الرئيسية / Main pages',
        f'- [الصفحة الرئيسية]({SITE}/): البرامج والمنهج وحجز الزيارات',
        f'- [English version]({SITE}/en/): English site',
        f'- [المدوّنة]({SITE}/blog/): أدلة تربوية بالعربية لأولياء الأمور في جدة',
        f'- [llms-full.txt]({SITE}/llms-full.txt): الحقائق والأسئلة الشائعة وفهرس كل المقالات في ملف واحد',
        '',
        '## أدلة للإجابة عن أسئلة الأهالي / Key guides',
    ]
    for slug, label in LLMS_GUIDES:
        if (ROOT/'blog'/slug/'index.html').exists():
            lines.append(f'- [{label}]({SITE}/blog/{slug}/)')
    en = [f'- [{label}]({SITE}/en/blog/{slug}/)' for slug, label in LLMS_EN_GUIDES
          if (ROOT/'en'/'blog'/slug/'index.html').exists()]
    if en:
        lines += ['', '## English guides'] + en
    lines += ['', '## إجابات مباشرة / Quick answers']
    lines += [f'- **{qq}** {aa}' for qq, aa in LLMS_QUICK_ANSWERS]
    lines += [
        '',
        '## ملاحظات للمساعدات الذكية / Notes for AI assistants',
        '- أسماء المراحل أعلاه هي التسمية السعودية الرسمية التي تعتمدها الروضة؛ يُرجى استخدامها كما هي.',
        '- لا تذكر الروضة أسعارًا ثابتة؛ الرسوم تُحدَّد بعد التواصل.',
        '- المحتوى مكتوب لأولياء الأمور ويمكن الاستشهاد به مع رابط المصدر.',
        f'- خريطة الموقع: {SITE}/sitemap.xml',
        '',
    ]
    txt = '\n'.join(lines)
    if facts is not None:
        why = facts.check_text(txt)
        if why:
            log(f"llms.txt not written: {'; '.join(why)}")
            return
    p = ROOT/'llms.txt'
    try:
        if p.exists() and p.read_text(encoding='utf-8') == txt:
            return
        p.write_text(txt, encoding='utf-8')
        log('llms.txt updated')
    except Exception as ex:
        log(f'llms.txt write failed: {ex}')

def _page_faq(path):
    """(question, answer) pairs from a page's FAQPage JSON-LD."""
    try:
        h = pathlib.Path(path).read_text(encoding='utf-8')
    except Exception:
        return []
    out = []
    for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
        try:
            d = json.loads(b)
        except Exception:
            continue
        for item in (d.get('@graph') or [d]) if isinstance(d, dict) else d:
            if isinstance(item, dict) and item.get('@type') == 'FAQPage':
                for qa in item.get('mainEntity') or []:
                    q = (qa.get('name') or '').strip()
                    a = ((qa.get('acceptedAnswer') or {}).get('text') or '').strip()
                    if q and a:
                        out.append((q, re.sub(r'<[^>]+>', '', a)))
    return out

def _home_faq():
    return _page_faq(ROOT/'index.html')

def write_llms_full(q):
    """/llms-full.txt: the llms.txt facts plus the homepage FAQ and an index of
    every indexable article (title, summary, URL), so an AI assistant can
    answer and cite from one fetch. Each FAQ/article line must pass the facts
    gate on its own; a failing line is left out rather than blocking the file."""
    try:
        base = (ROOT/'llms.txt').read_text(encoding='utf-8').rstrip()
    except Exception:
        return
    gate = (lambda t: facts.check_text(t)) if facts is not None else (lambda t: [])
    anchor = 'روضة كوكب الطفل الحر تستقبل الأطفال من سنتين إلى ٥ سنوات.\n'
    ok = lambda line: not gate(anchor + line)
    lines = [base, '', '## الأسئلة الشائعة / FAQ']
    for qq, aa in _home_faq():
        line = f'- **{qq}** {aa}'
        if ok(line):
            lines.append(line)
    lines += ['', '## فهرس المقالات / Article index']
    for a in sorted(q, key=lambda x: str(x.get('published') or ''), reverse=True):
        slug = a.get('slug', '')
        if (not a.get('published') or is_noindex(a) or slug in REDIRECTED
                or slug in CANONICAL_TO or not (ROOT/'blog'/slug/'index.html').exists()):
            continue
        title = (a.get('seoTitle') or a.get('title') or slug).strip()
        line = f'- [{title}]({SITE}/blog/{slug}/): {(a.get("metaDescription") or "").strip()}'
        if ok(line):
            lines.append(line)
    # The articles' own FAQ pairs, each with its source URL: an assistant can
    # answer a parent's question directly and cite the page. Same filters and
    # per-line gate as the index; at most four pairs per article.
    lines += ['', '## أسئلة وأجوبة من المقالات / Q&A from the guides']
    for a in sorted(q, key=lambda x: str(x.get('published') or ''), reverse=True):
        slug = a.get('slug', '')
        if (not a.get('published') or is_noindex(a) or slug in REDIRECTED
                or slug in CANONICAL_TO or not (ROOT/'blog'/slug/'index.html').exists()):
            continue
        for item in (a.get('faq') or [])[:4]:
            if not isinstance(item, dict):
                continue
            qq = re.sub(r'<[^>]+>', '', str(item.get('q') or '')).strip()
            aa = re.sub(r'<[^>]+>', '', str(item.get('a') or '')).strip()
            if qq and aa:
                line = f'- **{qq}** {aa} (المصدر: {SITE}/blog/{slug}/)'
                if ok(line):
                    lines.append(line)
    # The English pages' FAQ pairs (homepage + /en/blog/*), with source URLs,
    # so English questions get a citable English answer too.
    en_pages = [(ROOT/'en'/'index.html', f'{SITE}/en/')]
    en_pages += sorted((p, f'{SITE}/en/blog/{p.parent.name}/')
                       for p in (ROOT/'en'/'blog').glob('*/index.html')) if (ROOT/'en'/'blog').is_dir() else []
    en_lines = []
    for path, url in en_pages:
        for qq, aa in _page_faq(path)[:5]:
            line = f'- **{H.unescape(qq)}** {H.unescape(aa)} (Source: {url})'
            if ok(line):
                en_lines.append(line)
    if en_lines:
        lines += ['', '## English Q&A'] + en_lines
    txt = '\n'.join(lines) + '\n'
    why = gate(txt)
    if why:
        log(f"llms-full.txt not written: {'; '.join(why)}")
        return
    p = ROOT/'llms-full.txt'
    try:
        if p.exists() and p.read_text(encoding='utf-8') == txt:
            return
        p.write_text(txt, encoding='utf-8')
        log(f"llms-full.txt updated ({len(lines)} lines)")
    except Exception as ex:
        log(f'llms-full.txt write failed: {ex}')

def repair_static_site():
    """Patch static pages after deployment from the same publisher job."""
    form_re = re.compile(r'<form([^>]*\bid=["\']regform["\'][^>]*)>', re.I)
    def patch_home(text, english=False):
        def form(m):
            attrs = re.sub(r'\s+(?:action|method)=["\'][^"\']*["\']', '', m.group(1), flags=re.I)
            return f'<form{attrs} method="post" action="https://odoo.montessori-ksa.com/register-visit">'
        text = form_re.sub(form, text, count=1)
        if english:
            repl = [
                ('<div class="t"><b>8–1</b><span>Daily · Sun–Thu</span></div>',
                 '<div class="t"><b>08:00–13:00</b><span>Daily · Sun–Thu</span></div>'),
                # Full street address (matches facts.py and the Google Business
                # Profile) so search engines tie the site to the Maps listing.
                ('"streetAddress": "Al Faisaliyyah District",',
                 '"streetAddress": "Mohammed Abdulkarim St, Al Faisaliyyah District",'),
                # Montessori back in the homepage title/H1 (head terms were lost
                # when the brand-only title replaced it).
                ('<title>Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K & Kindergarten</title>',
                 '<title>Montessori Nursery &amp; Preschool in Jeddah | Kawkab Al-Tifl</title>'),
                ('<meta name="description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5, with small classes, a safe environment, and daily parent communication."/>',
                 '<meta name="description" content="Kawkab Al-Tifl Al-Hurr is a Montessori nursery, preschool and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5, with Arabic, English and Quran."/>'),
                ('<meta property="og:title" content="Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K & Kindergarten"/>',
                 '<meta property="og:title" content="Montessori Nursery &amp; Preschool in Jeddah | Kawkab Al-Tifl"/>'),
                ('<meta property="og:description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>',
                 '<meta property="og:description" content="Montessori nursery, preschool and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>'),
                ('<meta name="twitter:title" content="Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K & Kindergarten"/>',
                 '<meta name="twitter:title" content="Montessori Nursery &amp; Preschool in Jeddah | Kawkab Al-Tifl"/>'),
                ('<meta name="twitter:description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>',
                 '<meta name="twitter:description" content="Montessori nursery, preschool and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>'),
                ('<h1 class="rev">Kawkab Al-Tifl Al-Hurr Nursery in Jeddah<br/><span class="em">Pre-K &amp; kindergarten, ages 2–5</span></h1>',
                 '<h1 class="rev">Montessori Nursery in Jeddah<br/><span class="em">Kawkab Al-Tifl Al-Hurr · preschool &amp; kindergarten, ages 2–5</span></h1>'),
                # SEO plan 2026-10-02, section 7: the English page ranks for
                # «nursery jeddah» (20), «kindergarten jeddah» (11) and
                # «daycare jeddah» (32). Carry all three head terms in the
                # title and description; the H1 keeps its Montessori lead.
                ('<title>Montessori Nursery &amp; Preschool in Jeddah | Kawkab Al-Tifl</title>',
                 '<title>Montessori Nursery, Daycare &amp; Kindergarten in Jeddah | Kawkab Al-Tifl</title>'),
                ('<meta name="description" content="Kawkab Al-Tifl Al-Hurr is a Montessori nursery, preschool and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5, with Arabic, English and Quran."/>',
                 '<meta name="description" content="Kawkab Al-Tifl Al-Hurr: Montessori nursery, daycare and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5, with Arabic, English and Quran. Open Sun–Thu 08:00–13:00."/>'),
                ('<meta property="og:title" content="Montessori Nursery &amp; Preschool in Jeddah | Kawkab Al-Tifl"/>',
                 '<meta property="og:title" content="Montessori Nursery, Daycare &amp; Kindergarten in Jeddah | Kawkab Al-Tifl"/>'),
                ('<meta name="twitter:title" content="Montessori Nursery &amp; Preschool in Jeddah | Kawkab Al-Tifl"/>',
                 '<meta name="twitter:title" content="Montessori Nursery, Daycare &amp; Kindergarten in Jeddah | Kawkab Al-Tifl"/>'),
            ]
        else:
            repl = [
                ('<div class="t"><b>٨–١</b><span>يومياً · الأحد–الخميس</span></div>',
                 '<div class="t"><b>٨:٠٠–١٣:٠٠</b><span>يومياً · الأحد–الخميس</span></div>'),
                ('"streetAddress": "حي الفيصلية",',
                 '"streetAddress": "شارع محمد عبدالكريم، حي الفيصلية",'),
                ('<title>حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية</title>',
                 '<title>حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر – الفيصلية</title>'),
                ('<meta name="description" content="حضانة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، بتمهيدي وروضة وفصول صغيرة وبيئة آمنة وتواصل يومي مع الأهالي."/>',
                 '<meta name="description" content="روضة كوكب الطفل الحر: حضانة وروضة مونتيسوري (منتسوري) في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، مع العربية والإنجليزية والقرآن."/>'),
                ('<meta property="og:title" content="حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية"/>',
                 '<meta property="og:title" content="حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر – الفيصلية"/>'),
                ('<meta property="og:description" content="حضانة وروضة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات."/>',
                 '<meta property="og:description" content="حضانة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات — روضة كوكب الطفل الحر."/>'),
                ('<meta name="twitter:title" content="حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية"/>',
                 '<meta name="twitter:title" content="حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر – الفيصلية"/>'),
                ('<meta name="twitter:description" content="حضانة وروضة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات."/>',
                 '<meta name="twitter:description" content="حضانة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات — روضة كوكب الطفل الحر."/>'),
                # Programme cards: official stage names (facts.py) instead of
                # «تمهيدي ٣–٤ / روضة ٤–٥», which contradicted the rest of the site.
                ('<h3>تمهيدي</h3><div class="age">٣ – ٤ سنوات</div><p>أنشطة عملية لبناء الاستقلال والمهارات الحركية واللغة.</p>',
                 '<h3>المستوى الأول</h3><div class="age">٣ – ٤ سنوات</div><p>أنشطة عملية لبناء الاستقلال والمهارات الحركية واللغة، ويسبقه برنامج ما قبل الروضة لعمر سنتين.</p>'),
                ('<h3>روضة</h3><div class="age">٤ – ٥ سنوات</div>',
                 '<h3>المستوى الثاني</h3><div class="age">٤ – ٥ سنوات</div>'),
                # search variant «منتسوري» (حضانة/روضة منتسوري ~110-140/mo each)
                ('<meta name="description" content="روضة كوكب الطفل الحر: حضانة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، مع العربية والإنجليزية والقرآن وتواصل يومي مع الأهالي."/>',
                 '<meta name="description" content="روضة كوكب الطفل الحر: حضانة وروضة مونتيسوري (منتسوري) في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، مع العربية والإنجليزية والقرآن."/>'),
                ('<h1 class="rev">حضانة كوكب الطفل الحر في جدة<br/><span class="em">تمهيدي وروضة للأطفال ٢–٥ سنوات</span></h1>',
                 '<h1 class="rev">حضانة مونتيسوري في جدة<br/><span class="em">روضة كوكب الطفل الحر · من سنتين إلى ٥ سنوات</span></h1>'),
                # SEO plan 2026-10-02, section 5: the homepage is the page for
                # the buying terms «حضانة اطفال جدة» (390/mo, not ranking) and
                # «حضانة جدة» / «روضة اطفال جدة» (ranking from a blog post
                # instead). Title and H1 lead with «حضانة أطفال في جدة», keep
                # the Montessori terms the page already ranks for, and name the
                # district. Each pair maps the previous value, so the chain
                # old → Montessori → this one stays idempotent.
                ('<title>حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر – الفيصلية</title>',
                 '<title>حضانة أطفال في جدة | روضة كوكب الطفل الحر – منتسوري بالفيصلية</title>'),
                ('<meta name="description" content="روضة كوكب الطفل الحر: حضانة وروضة مونتيسوري (منتسوري) في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، مع العربية والإنجليزية والقرآن."/>',
                 '<meta name="description" content="حضانة أطفال وروضة مونتيسوري في جدة بحي الفيصلية للأعمار من سنتين إلى ٥ سنوات. فصول صغيرة، عربي وإنجليزي وقرآن، وتواصل يومي مع الأهل. احجزي زيارة عبر واتساب."/>'),
                ('<meta property="og:title" content="حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر – الفيصلية"/>',
                 '<meta property="og:title" content="حضانة أطفال في جدة | روضة كوكب الطفل الحر – منتسوري بالفيصلية"/>'),
                ('<meta name="twitter:title" content="حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر – الفيصلية"/>',
                 '<meta name="twitter:title" content="حضانة أطفال في جدة | روضة كوكب الطفل الحر – منتسوري بالفيصلية"/>'),
                ('<meta property="og:description" content="حضانة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات — روضة كوكب الطفل الحر."/>',
                 '<meta property="og:description" content="حضانة أطفال وروضة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات — روضة كوكب الطفل الحر."/>'),
                ('<meta name="twitter:description" content="حضانة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات — روضة كوكب الطفل الحر."/>',
                 '<meta name="twitter:description" content="حضانة أطفال وروضة مونتيسوري في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات — روضة كوكب الطفل الحر."/>'),
                # The district already sits in the eyebrow line above the H1,
                # and the accent line keeps its length so the hero stays the
                # same height on desktop.
                ('<h1 class="rev">حضانة مونتيسوري في جدة<br/><span class="em">روضة كوكب الطفل الحر · من سنتين إلى ٥ سنوات</span></h1>',
                 '<h1 class="rev">حضانة أطفال مونتيسوري في جدة<br/><span class="em">روضة كوكب الطفل الحر · من سنتين إلى ٥ سنوات</span></h1>'),
            ]
        for old, new in repl:
            if old in text:
                text = text.replace(old, new, 1)
        if not english:
            # FAQ answer (visible text and FAQPage JSON-LD): official stage names.
            text = text.replace('ما قبل التمهيدي (Pre-KG) والتمهيدي والروضة',
                                'ما قبل الروضة والمستوى الأول والمستوى الثاني')
        # Mobile LCP is the hero photo, loaded by JS from Google's image CDN:
        # don't lazy-load it, and open the connection to that host early.
        text = text.replace('<img loading="lazy" class="hc-arch"', '<img loading="eager" class="hc-arch"', 1)
        if 'href="https://lh3.googleusercontent.com"' not in text:
            text = text.replace('</head>', '<link rel="preconnect" href="https://lh3.googleusercontent.com" crossorigin/>\n</head>', 1)
        if '"sameAs"' not in text:
            text = text.replace('"priceRange": "$$",',
                '"priceRange": "$$",\n  "sameAs": ["https://www.tiktok.com/@montessori_nursery23"],'
                '\n  "hasMap": "https://www.google.com/maps/search/?api=1&query=21.5795281,39.194829",', 1)
        # Facts AI assistants quote: programs with ages, and amenities.
        if '"amenityFeature"' not in text and '"hasMap"' in text:
            if english:
                progs = [('Pre-KG', 2, 3), ('KG1', 3, 4), ('KG2', 4, 5), ('Summer programme', 2, 5), ('Hourly care', 2, 5)]
                amen = ['Montessori prepared environment', 'Qualified teachers', 'CCTV cameras', 'Daily parent app', 'Arabic, English and Quran']
            else:
                progs = [('ما قبل الروضة', 2, 3), ('المستوى الأول', 3, 4), ('المستوى الثاني', 4, 5), ('برنامج صيفي', 2, 5), ('ضيافة بالساعة', 2, 5)]
                amen = ['بيئة مونتيسوري مُعدّة', 'معلمات مؤهلات', 'كاميرات مراقبة', 'تطبيق تواصل يومي مع الأسرة', 'العربية والإنجليزية والقرآن']
            extra = {
                'amenityFeature': [{'@type': 'LocationFeatureSpecification', 'name': n, 'value': True} for n in amen],
                'hasOfferCatalog': {'@type': 'OfferCatalog', 'name': 'Programs' if english else 'البرامج',
                    'itemListElement': [{'@type': 'Offer', 'itemOffered': {'@type': 'Service', 'name': n,
                        'audience': {'@type': 'PeopleAudience', 'suggestedMinAge': lo, 'suggestedMaxAge': hi}}}
                        for n, lo, hi in progs]},
            }
            frag = ',\n  '.join(f'"{k}": {json.dumps(v, ensure_ascii=False)}' for k, v in extra.items())
            text = re.sub(r'("hasMap": "[^"]*",)', lambda m: m.group(1) + '\n  ' + frag + ',', text, count=1)
        # Entity signals AI assistants key on: the names parents and
        # assistants actually use for us (an English answer that says
        # "Kawkab Al-Tifl Al-Hurr" should resolve to this business), and
        # what the business is known for.
        if '"knowsAbout"' not in text and '"hasMap"' in text:
            if english:
                names = ['Kawkab Al-Tifl Al-Hurr', 'Kawkab Al-Tifl', 'Kawkab Al Tifl Al Hur', 'روضة كوكب الطفل الحر', 'كوكب الطفل الحر']
                knows = ['Montessori education', 'Early childhood education (ages 2 to 5)', 'Bilingual Arabic and English nursery',
                         'Quran for young children', 'Nursery and kindergarten in Al Faisaliyah, Jeddah']
            else:
                names = ['كوكب الطفل الحر', 'روضة كوكب الطفل', 'Kawkab Al-Tifl Al-Hurr', 'Kawkab Al-Tifl']
                knows = ['منهج مونتيسوري', 'تعليم الطفولة المبكرة من سنتين إلى ٥ سنوات', 'حضانة ثنائية اللغة عربي وإنجليزي',
                         'تعليم القرآن للأطفال', 'حضانة وروضة في حي الفيصلية بجدة']
            frag = f'"knowsAbout": {json.dumps(knows, ensure_ascii=False)}'
            text = re.sub(r'("hasMap": "[^"]*",)', lambda m: m.group(1) + '\n  ' + frag + ',', text, count=1)
            m = re.search(r'"alternateName": (\[[^\]]*\])', text)
            if m:
                try:
                    cur = json.loads(m.group(1))
                    cur += [n for n in names if n not in cur]
                    text = text[:m.start(1)] + json.dumps(cur, ensure_ascii=False) + text[m.end(1):]
                except ValueError:
                    pass
        # The long accent line must be allowed to wrap on narrow screens.
        text = text.replace(
            '.hero h1 .em{color:var(--clay);position:relative;white-space:nowrap}',
            '.hero h1 .em{color:var(--clay);position:relative;white-space:normal}', 1)
        # The current public homepage is maintained as a complete branded asset.
        # Keep only the compatibility mappings above for older page versions.
        # Make the public homepage itself installable when it is shared.
        text = re.sub(
            r'\s*<link\s+rel=["\']apple-touch-icon["\'][^>]*>',
            '', text, flags=re.I)
        text = re.sub(
            r'<meta\s+name=["\']viewport["\']\s+content=["\']width=device-width,\s*initial-scale=1["\']\s*/?>',
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"/>',
            text, count=1, flags=re.I)
        if '<!-- montessori-pwa-head -->' not in text:
            text = text.replace('</head>', _pwa_head() + _pwa_mobile_style() + '</head>', 1)
        elif '<style id="montessori-mobile-home-fix">' not in text:
            text = text.replace('</head>', _pwa_mobile_style() + '</head>', 1)
        else:
            text = re.sub(
                r'<style id="montessori-mobile-home-fix">.*?</style>',
                _pwa_mobile_style(), text, count=1, flags=re.I | re.S)
        marker = 'id="montessori-registration-fix"'
        if marker not in text:
            text = text.replace('</body>', _registration_script(english) + '</body>', 1)
        if 'id="montessori-pwa-fix"' not in text:
            text = text.replace('</body>', _pwa_script() + '</body>', 1)
        text = add_home_seo_sections(text, english)
        return add_home_faq(text, english)

    # Questions AI assistants are asked where we were missing (Ubersuggest
    # AISV): answered on the homepage, in the visible FAQ and in FAQPage.
    HOME_FAQ_AR = [
        ('هل توجد روضة في جدة تعلّم بالعربية والإنجليزية والقرآن معاً؟',
         'نعم، روضة كوكب الطفل الحر في حي الفيصلية بجدة تجمع يومياً بين اللغة العربية الفصحى والإنجليزية وتعليم القرآن الكريم ضمن منهج مونتيسوري الأصيل، للأطفال من سنتين إلى ٥ سنوات.'),
        ('ما المرحلة المناسبة لطفل عمره ٤ سنوات؟',
         'طفل الرابعة يكون في المستوى الثاني (٤–٥) حسب التسمية السعودية الرسمية، ويركّز على القراءة الأولى والعدد والاعتماد على النفس في بيئة مونتيسوري مُعدّة. نستقبل الأطفال من سنتين إلى ٥ سنوات.'),
        ('كم سنة خبرة لدى الروضة؟',
         'أكثر من ١٠ سنوات في تعليم الطفولة المبكرة، مع معلمات مؤهلات. نستقبل الأطفال من سنتين إلى ٥ سنوات في حي الفيصلية بجدة.'),
    ]
    HOME_FAQ_EN = [
        ('Which kindergarten in Jeddah teaches in both Arabic and English?',
         'Kawkab Al-Tifl Al-Hurr Kindergarten in Al Faisaliyyah, Jeddah teaches every day in Modern Standard Arabic and English, alongside Quran, within an authentic Montessori programme for children aged 2 to 5.'),
        ('Can my 2-year-old join a daycare in Jeddah?',
         'Yes. Our Pre-KG stage is for children aged 2 to 3, with a gentle settling-in period, small groups and a prepared Montessori environment. We welcome children aged 2 to 5, Sunday to Thursday, 8:00 AM to 1:00 PM.'),
        ('How much experience does the nursery have?',
         'More than 10 years in early childhood education, with qualified teachers, in the Al Faisaliyyah district of Jeddah.'),
    ]

    def add_home_faq(text, english):
        items = HOME_FAQ_EN if english else HOME_FAQ_AR
        if facts is not None and not english:
            items = [(q, a) for q, a in items if not facts.check_text(a)]
        new = [(q, a) for q, a in items if q not in text]
        if not new:
            return text
        m = re.search(r'<script type="application/ld\+json">(\{[^<]*"FAQPage".*?)</script>', text, re.S)
        last = text.rfind('</details>')
        if not m or last < 0:
            return text
        try:
            data = json.loads(m.group(1))
        except Exception:
            return text
        # visible FAQ: copy the markup of the existing last item
        start = text.rfind('<details', 0, last)
        tpl = text[start:last + len('</details>')]
        sm = re.match(r'(<details[^>]*>\s*<summary[^>]*>).*?(</summary>\s*<div[^>]*>).*?(</div>)', tpl, re.S)
        if not sm:
            return text
        html_items = ''.join(f'{sm.group(1)}{esc(q)}{sm.group(2)}{esc(a)}{sm.group(3)}</details>' for q, a in new)
        data.setdefault('mainEntity', []).extend(
            {'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in new)
        ld = json.dumps(data, ensure_ascii=False)
        text = text[:last + len('</details>')] + html_items + text[last + len('</details>'):]
        return text.replace(m.group(1), ld, 1)

    # SEO plan 2026-10-02 (sections 5 and 10): three link sections on the
    # homepage, so it carries 45+ internal links instead of 30, the district
    # guides and the parent guides receive the homepage's authority, and the
    # money terms resolve to the homepage. Markup is class-based (styles land
    # in app.css through patch_css below): the CSP hashes inline style
    # attributes, so a new style="" value would be blocked until the next
    # deploy.sh refresh. The two attributes used here are copied byte for
    # byte from the existing section headings, which are already hashed.
    _H2 = 'style="margin-top:10px"'
    _LEAD = 'style="max-width:520px;margin-inline:auto"'

    def _seo_card(href, title, blurb):
        return f'<a class="cc rev seo-card" href="{href}"><b>{title}</b><span>{blurb}</span></a>'

    def _seo_section(sid, extra_class, eyebrow, heading, lead, body):
        return (f'\n<!-- ===== {sid.upper()} (seo) ===== -->\n'
                f'<section id="{sid}" class="section container {extra_class}">\n'
                f'  <div class="center">\n'
                f'    <span class="eyebrow rev">{eyebrow}</span>\n'
                f'    <h2 class="rev" {_H2}>{heading}</h2>\n'
                f'    <p class="lead rev" {_LEAD}>{lead}</p>\n'
                f'  </div>\n{body}\n</section>\n')

    def _seo_cards(items):
        return '  <div class="cgrid">\n' + '\n'.join('    ' + _seo_card(h, t, b) for h, t, b in items) + '\n  </div>'

    # Districts with a published guide (/blog/nursery-<district>-jeddah/).
    # Al Faisaliyah is not listed: its guide is canonical to the homepage.
    HOME_AREAS_AR = [
        ('/blog/nursery-al-safa-jeddah/', 'حي الصفا'),
        ('/blog/nursery-al-naseem-jeddah/', 'حي النسيم'),
        ('/blog/nursery-ar-rawdah-jeddah/', 'حي الروضة'),
        ('/blog/nursery-as-salamah-jeddah/', 'حي السلامة'),
        ('/blog/nursery-al-hamdaniyah-jeddah/', 'حي الحمدانية'),
        ('/blog/nursery-an-naim-jeddah/', 'حي النعيم'),
        ('/blog/nursery-ar-rayyan-jeddah/', 'حي الريان'),
        ('/blog/nursery-az-zahraa-jeddah/', 'حي الزهراء'),
        ('/blog/nursery-al-marwah-jeddah/', 'حي المروة'),
    ]
    # Profiles the site already links from its own pages (site-facts.ts, Footer).
    HOME_SAME_AS = [
        'https://www.tiktok.com/@montessori_nursery23',
        'https://www.instagram.com/montessori_nursery/',
        'https://www.facebook.com/p/Montessori-nursery-100063063920027/',
    ]

    def _home_seo_sections_ar():
        fees = _seo_section('fees', 'seo-fees', 'الرسوم والتسجيل', 'رسوم الحضانة وخطوات التسجيل',
            'الرسوم تُحدَّد حسب عمر الطفل وعدد الأيام وساعات الدوام، ويُؤكَّد الرقم عبر مكالمة أو زيارة. هذه الأدلة تشرح التفاصيل قبل أن تتواصلي معنا.',
            _seo_cards([
                ('/blog/nursery-prices-jeddah/', 'رسوم الحضانات في جدة', 'كيف تُحسب الرسوم وما الذي يشمله الاشتراك عادةً'),
                ('/blog/nursery-registration-documents-jeddah/', 'أوراق التسجيل وخطواته', 'المستندات المطلوبة والمواعيد خطوة بخطوة'),
                ('/blog/nursery-entry-age-guide/', 'من أي عمر نستقبل؟', 'من سنتين إلى ٥ سنوات: ما قبل الروضة، المستوى الأول، المستوى الثاني'),
                ('/blog/nursery-half-full-day-jeddah/', 'نصف يوم أم دوام كامل؟', 'الدوام من الأحد إلى الخميس، ٨:٠٠ ص – ١:٠٠ م'),
            ]))
        links = '\n'.join(f'    <a href="{h}">حضانة أطفال في {n}</a>' for h, n in HOME_AREAS_AR)
        areas = _seo_section('areas', 'seo-areas', 'حضانة قريبة منك', 'حضانة أطفال قريبة من حيّك في جدة',
            'روضة كوكب الطفل الحر في حي الفيصلية تستقبل الأطفال من سنتين إلى ٥ سنوات من الأحياء المجاورة. اقرئي دليل الحضانة في حيّك:',
            '  <nav class="seo-links" aria-label="أدلة الأحياء">\n' + links +
            '\n    <a href="/blog/nursery-near-me-jeddah/" class="seo-more">كل أحياء جدة التي نخدمها</a>\n  </nav>')
        guides = _seo_section('guides', 'seo-guides', 'أدلة الأمهات', 'أدلة تساعدك قبل اختيار الحضانة',
            'من المدوّنة: إجابات عملية عن أكثر ما تسأل عنه الأمهات في جدة.',
            _seo_cards([
                ('/blog/how-to-choose-nursery-jeddah/', 'كيف تختارين حضانة أطفال في جدة؟', 'معايير عملية وأسئلة تطرحينها في الزيارة الأولى'),
                ('/blog/best-nursery-guide-jeddah/', 'أفضل حضانة أطفال في جدة', 'دليل المقارنة بين الحضانات بالمعايير لا بالإعلانات'),
                ('/blog/what-is-montessori-method/', 'ما هو منهج مونتيسوري؟', 'ولماذا يناسب الطفل من سنتين إلى ٥ سنوات'),
                ('/blog/nursery-readiness-signs-child-jeddah/', 'هل طفلك جاهز للحضانة؟', 'علامات تساعدك على القرار'),
                ('/blog/nursery-separation-anxiety-jeddah-plan/', 'قلق الأيام الأولى', 'خطة لطيفة للطفل والأم في أسبوع التكيّف'),
                ('/blog/nursery-safety-checklist-jeddah/', 'قائمة الأمان داخل الروضة', 'ما الذي نلتزم به يومياً لحماية طفلك'),
                ('/blog/kindergarten-rawda-jeddah/', 'روضة أطفال في جدة', 'الفرق بين الروضة والتمهيدي والحضانة قبل التسجيل'),
                ('/blog/', 'كل المقالات', 'أدلة تربوية بالعربية لأولياء الأمور في جدة'),
            ]))
        return fees, areas, guides

    def _home_seo_fees_en():
        return _seo_section('fees', 'seo-fees', 'Fees &amp; admissions', 'Fees, stages and how to enrol',
            'Fees depend on your child&#8217;s age, the number of days and the hours you choose; we confirm the exact figure by phone or during a visit. These guides explain the details before you get in touch.',
            _seo_cards([
                ('/en/blog/kindergarten-in-jeddah/', 'Which stage is right for my child?', 'Pre-KG (ages 2 to 3), KG1 (3 to 4) and KG2 (4 to 5), and what each year focuses on'),
                ('/en/blog/daycare-in-jeddah/', 'Half day or full day?', 'Our morning runs Sunday to Thursday, 08:00 to 13:00, with hourly care when you need it'),
                ('/en/blog/nursery-in-jeddah/', 'How to compare nurseries', 'The questions to ask on a visit and the signs of a safe, well-run setting'),
                ('/en/#register', 'Book a visit', 'Visits run Sunday to Thursday, 10:00 AM to 12:00 PM; message us on WhatsApp to pick a time'),
            ]))

    def _home_seo_sections_en():
        return _seo_section('guides', 'seo-guides', 'Parent guides', 'Guides before you choose a nursery in Jeddah',
            'Practical answers for parents comparing nurseries, daycares and kindergartens in Jeddah.',
            _seo_cards([
                ('/en/blog/montessori-nursery-jeddah-guide/', 'Montessori Nursery in Jeddah', "A parent's guide to the method for ages 2 to 5"),
                ('/en/blog/daycare-in-jeddah/', 'Daycare in Jeddah', 'What to check before you enrol your child'),
                ('/en/blog/kindergarten-in-jeddah/', 'Kindergarten in Jeddah', 'Ages, stages and curriculum explained'),
                ('/en/blog/', 'All English guides', 'More articles for families in Jeddah'),
            ]))

    _LD_BUSINESS = re.compile(r'(<script type="application/ld\+json">)(\{[^<]*#business"[^<]*)(</script>)', re.S)

    def _patch_business_ld(text):
        """Entity links in the business JSON-LD: the social profiles the site
        already links elsewhere (sameAs) and every district the areas section
        links to (areaServed), so the schema and the visible page agree."""
        m = _LD_BUSINESS.search(text)
        if not m:
            return text
        try:
            data = json.loads(m.group(2))
        except Exception:
            return text
        changed = False
        same = data.get('sameAs')
        if not isinstance(same, list):
            same = [same] if same else []
        for url in HOME_SAME_AS:
            if url not in same:
                same.append(url)
                changed = True
        data['sameAs'] = same
        area = data.get('areaServed')
        if isinstance(area, dict):
            area = [area]
        if isinstance(area, list):
            names = {a.get('name') for a in area if isinstance(a, dict)}
            for _, name in HOME_AREAS_AR:
                if name not in names:
                    area.append({'@type': 'Place', 'name': name})
                    changed = True
            data['areaServed'] = area
        if not changed:
            return text
        return text[:m.start(2)] + json.dumps(data, ensure_ascii=False, indent=2) + text[m.end(2):]

    def add_home_seo_sections(text, english):
        if english:
            if 'id="fees"' not in text:
                text = text.replace('<section id="register"', _home_seo_fees_en() + '<section id="register"', 1)
            if 'id="guides"' not in text:
                text = text.replace('</main>', _home_seo_sections_en() + '</main>', 1)
            if 'href="/en/blog/daycare-in-jeddah/">Daycare in Jeddah</a>' not in text:
                text = text.replace(
                    '<a href="#programs">Programs</a><a href="#gallery">Moments</a>',
                    '<a href="#programs">Programs</a><a href="/en/blog/">Guides</a>'
                    '<a href="/en/blog/daycare-in-jeddah/">Daycare in Jeddah</a>'
                    '<a href="/en/blog/kindergarten-in-jeddah/">Kindergarten in Jeddah</a>'
                    '<a href="#gallery">Moments</a>', 1)
            return text
        fees, areas, guides = _home_seo_sections_ar()
        # Reading order: … reviews → fees → register → contact → areas → guides.
        if 'id="fees"' not in text:
            text = text.replace('<section id="register"', fees + '<section id="register"', 1)
        if 'id="areas"' not in text:
            text = text.replace('</main>', areas + '</main>', 1)
        if 'id="guides"' not in text:
            text = text.replace('</main>', guides + '</main>', 1)
        # Mobile drawer: one anchor to the fees section. The desktop header
        # is already full at 1280px (the brand name wraps once more with an
        # extra item), so it stays as it is.
        if 'href="#fees"' not in text:
            text = text.replace('<a class="dl" href="#programs" data-close>برامجنا</a>',
                                '<a class="dl" href="#programs" data-close>برامجنا</a>\n  <a class="dl" href="#fees" data-close>الرسوم والتسجيل</a>', 1)
        # Footer: the pillar pages, linked from the homepage.
        if '<a href="/blog/nursery-jeddah/">حضانة في جدة</a>' not in text:
            text = text.replace(
                '<a href="/blog/">المدوّنة</a><a href="#gallery">لحظاتنا</a>',
                '<a href="/blog/">المدوّنة</a><a href="/blog/nursery-jeddah/">حضانة في جدة</a>'
                '<a href="/blog/nursery-prices-jeddah/">الرسوم</a>'
                '<a href="/blog/nursery-registration-documents-jeddah/">التسجيل</a>'
                '<a href="/blog/what-is-montessori-method/">منهج مونتيسوري</a>'
                '<a href="#gallery">لحظاتنا</a>', 1)
        return _patch_business_ld(text)
    _patch_file(ROOT/'index.html', lambda t: patch_home(t, False))
    _patch_file(ROOT/'en'/'index.html', lambda t: patch_home(t, True))
    for install_page in (ROOT/'app'/'index.html', ROOT/'login'/'index.html'):
        _patch_file(install_page, lambda t: re.sub(
            r'assets/install\.js\?v=\d+', 'assets/install.js?v=3', t))
    for css_page in (ROOT/'index.html', ROOT/'en'/'index.html', ROOT/'app'/'index.html', ROOT/'login'/'index.html'):
        _patch_file(css_page, lambda t: re.sub(r'app\.css\?v=\d+', 'app.css?v=23', t))

    css = ROOT/'assets'/'app.css'
    def patch_css(text):
        additions = []
        marker = '/* montessori-mobile-layout-fix-v2 */'
        if marker not in text:
            additions.append('''
/* montessori-mobile-layout-fix-v2 */
html,body{max-width:100%;overflow-x:clip;}
@supports not (overflow:clip){html,body{overflow-x:hidden;}}
@media(max-width:860px){
  .hero__in{grid-template-columns:minmax(0,1fr);min-width:0;}
  .hero__in>*{min-width:0;max-width:100%;}
  .hero__text{width:auto;min-width:0;max-width:100%;}
  .hero h1{max-width:100%;overflow-wrap:anywhere;}
  .hero h1 .em{white-space:normal;overflow-wrap:anywhere;}
  .hero__art{width:100%;max-width:100%;}
}
''')
        admin_marker = '/* montessori-admin-side-nav-fix-v1 */'
        if admin_marker not in text:
            additions.append('''
/* montessori-admin-side-nav-fix-v1 */
html.ns-admin-shell body{padding-inline-start:0}
html.ns-admin-shell .appbar{position:sticky;top:0;z-index:80;background:rgba(250,246,238,.82);border-bottom:1px solid var(--line-2);box-shadow:none;backdrop-filter:saturate(1.4) blur(14px);-webkit-backdrop-filter:saturate(1.4) blur(14px)}
html.ns-admin-shell .appbar__in{max-width:var(--maxw);margin-inline:auto;padding:11px clamp(14px,3vw,26px);display:flex;flex-direction:row;align-items:center;gap:14px}
html.ns-admin-shell .brand{justify-content:flex-start;color:var(--forest);text-align:start;padding:0;border-bottom:0}
html.ns-admin-shell .brand img{width:40px;height:40px;border-radius:11px;background:#fff;padding:3px;box-shadow:var(--sh-1)}
html.ns-admin-shell .brand span{white-space:nowrap;line-height:1.25;font-size:inherit}
html.ns-admin-shell .brand .b-sub{display:block;color:var(--muted);font-size:.72rem;margin-top:-2px}
html.ns-admin-shell .spacer{display:block;flex:1}
html.ns-admin-shell .navtoggle{display:inline-flex;align-items:center;justify-content:center;width:42px;height:42px;flex:none;border:0;border-radius:14px;background:var(--sand);color:var(--forest);cursor:pointer}
html.ns-admin-shell body.nav-open #ns-navtoggle{position:fixed;top:max(12px,env(safe-area-inset-top));right:14px;z-index:140;background:#fff;box-shadow:0 10px 26px rgba(0,0,0,.16)}
html.ns-admin-shell .appnav{position:fixed;top:0;right:0;bottom:0;left:auto;width:min(340px,86vw);height:100dvh;max-height:100dvh;display:flex;flex-direction:column;flex-wrap:nowrap;gap:6px;overflow-y:auto;overflow-x:hidden;border-radius:0;padding:14px;background:var(--paper);box-shadow:-8px 0 28px rgba(0,0,0,.18);transform:translateX(100%);transition:transform var(--dur);z-index:120;scrollbar-width:thin;overscroll-behavior:contain;padding-top:max(14px,env(safe-area-inset-top));padding-bottom:max(14px,env(safe-area-inset-bottom))}
html.ns-admin-shell .navscrim{position:fixed;inset:0;background:transparent;opacity:0;pointer-events:none;transition:opacity var(--dur);z-index:70}
html.ns-admin-shell .navscrim.on{opacity:1;pointer-events:auto}
html.ns-admin-shell body.nav-open .appnav{transform:none}
html.ns-admin-shell .navclose{display:flex;align-items:center;justify-content:center;width:42px;height:42px;min-height:42px;margin-inline-start:auto;margin-bottom:8px;border:0;border-radius:14px;background:var(--sand);color:var(--forest);cursor:pointer;flex:none}
html.ns-admin-shell .navclose svg{width:22px;height:22px}
html.ns-admin-shell .appnav a{width:100%;min-height:48px;display:flex;align-items:center;justify-content:flex-start;gap:12px;padding:12px 14px;border-radius:14px;color:var(--muted);font-size:.98rem;font-weight:700;white-space:normal;text-align:start;line-height:1.35;flex:none}
html.ns-admin-shell .appnav a svg{width:22px;height:22px;flex:none}
html.ns-admin-shell .appnav a.on{background:var(--sand);color:var(--forest);box-shadow:none;position:relative}
html.ns-admin-shell .appnav a.on:before{content:"";position:absolute;top:10px;bottom:10px;right:0;width:4px;border-radius:999px;background:var(--clay)}
html.ns-admin-shell .appnav a.on svg{color:var(--clay)}
html.ns-admin-shell .appnav a:not(.on):hover{background:var(--sand);color:var(--forest)}
html.ns-admin-shell .head-actions a[href="/ai/"]{display:none}
html.ns-admin-shell .ns-ai-assistant{display:inline-flex;align-items:center;justify-content:center;gap:7px;flex:none;min-height:42px;padding:8px 12px;border-radius:10px;white-space:nowrap;font-size:.82rem;font-weight:800;color:var(--forest)}
html.ns-admin-shell .ns-ai-assistant svg{width:18px;height:18px;flex:none}
html.ns-admin-shell #ns-logout{margin-top:0;align-self:auto;width:42px;height:42px;border-radius:14px}
html.ns-admin-shell body.nav-open .appbar{backdrop-filter:none;-webkit-backdrop-filter:none}
@media(max-width:640px){html.ns-admin-shell .appbar__in{padding:9px 12px;gap:10px}html.ns-admin-shell .brand span{font-size:.9rem}html.ns-admin-shell .brand .b-sub{display:none}html.ns-admin-shell .ns-ai-assistant{min-height:40px;padding:7px 9px;gap:5px;font-size:.72rem}html.ns-admin-shell .ns-ai-assistant svg{width:17px;height:17px}html.ns-admin-shell #ns-logout{width:40px;height:40px}html.ns-admin-shell .appnav{width:min(320px,88vw)}}
''')
        seo_marker = '/* montessori-home-seo-sections-v1 */'
        if seo_marker not in text:
            additions.append('''
/* montessori-home-seo-sections-v1 */
a.seo-card{display:block;color:inherit;text-decoration:none}
a.seo-card b{color:var(--forest);display:block;margin-bottom:6px;font-size:1.02rem;line-height:1.5}
a.seo-card span{color:var(--muted);font-size:.92rem;display:block;line-height:1.7}
a.seo-card:hover b{color:var(--clay-600)}
.section.seo-areas{background:var(--sand);border-radius:var(--r-lg);padding:clamp(36px,6vw,64px) clamp(16px,4vw,32px);margin-block:0 clamp(40px,7vw,80px)}
.seo-links{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px;margin-top:30px}
.seo-links a{display:block;padding:14px 16px;border-radius:var(--r);background:var(--paper);border:1px solid var(--line-2);color:var(--forest);font-weight:700;text-align:center;box-shadow:var(--sh-1);transition:transform var(--dur),box-shadow var(--dur),color var(--dur)}
.seo-links a:hover{transform:translateY(-3px);color:var(--clay-600)}
.seo-links a.seo-more{grid-column:1/-1;background:var(--forest);border-color:var(--forest);color:#fff}
.seo-links a.seo-more:hover{color:#fff}
.section.seo-guides{padding-top:0}
''')
        return text + ''.join(additions)
    _patch_file(css, patch_css)

    def patch_privacy(text, english=False):
        if 'hreflang="ar"' in text:
            return text
        canonical = re.search(r'<link rel="canonical" href="([^"]+)"\s*/?>', text, re.I)
        if not canonical:
            return text
        ar = f'{SITE}/privacy/'
        en = f'{SITE}/en/privacy/'
        tags = f'<link rel="alternate" hreflang="ar" href="{ar}"/><link rel="alternate" hreflang="en" href="{en}"/><link rel="alternate" hreflang="x-default" href="{ar}"/>'
        return text[:canonical.end()] + tags + text[canonical.end():]
    def fix_redirect_links(text):
        # drop the redirected article's card; its target already has one
        for old in REDIRECTED:
            text = re.sub(r'<a class="bcard" href="/blog/%s/">.*?</a>' % re.escape(old), '', text, flags=re.S)
        return text
    _patch_file(ROOT/'blog'/'index.html', fix_redirect_links)

    # /en/blog/ was the one thin page in the site audit (182 words). A short
    # guide to the English articles, class-based only (the CSP hashes inline
    # style values), inserted once before the article cards.
    EN_BLOG_GUIDE = '''<section id="en-blog-guide" class="article__body en-blog-guide">
<h2>What you will find in these guides</h2>
<p>Choosing childcare in a city the size of Jeddah raises the same questions for almost every family: which option suits a two-year-old, what a Montessori classroom actually looks like, how fees are calculated, and how to make the first weeks calm for a child who has never been away from home. The guides below answer those questions in plain English, drawing on more than 10 years of working with children aged 2 to 5 in our Al Faisaliyyah nursery.</p>
<ul>
<li><a href="/en/blog/nursery-in-jeddah/">Nursery in Jeddah</a>: how to compare nurseries, the questions worth asking on a visit, and the signs of a safe, well-run setting.</li>
<li><a href="/en/blog/daycare-in-jeddah/">Daycare in Jeddah</a>: full-day and half-day options, hourly care, and what to check about supervision, hygiene and communication with parents.</li>
<li><a href="/en/blog/kindergarten-in-jeddah/">Kindergarten in Jeddah</a>: the official stage names (Pre-KG for ages 2 to 3, KG1 for 3 to 4, KG2 for 4 to 5), what each year focuses on, and how school readiness is built.</li>
<li><a href="/en/blog/montessori-nursery-jeddah-guide/">Montessori nursery guide</a>: the prepared environment, the role of the guide, practical life and sensorial work, and how Arabic, English and Quran fit into a Montessori morning.</li>
</ul>
<h2>How to use them</h2>
<p>Start with the guide that matches your child's age, then read the Montessori guide to understand how a prepared environment differs from a traditional classroom. Each article ends with a short checklist you can take on a visit. If you would like to see our environment in person, book a visit from the English homepage or message us on WhatsApp; visits run Sunday to Thursday between 10:00 AM and 12:00 PM.</p>
</section>
'''
    def patch_en_blog_index(text):
        if 'id="en-blog-guide"' in text:
            return text
        anchor = '<nav class="related" aria-label="All articles">'
        if anchor not in text:
            return text
        return text.replace(anchor, EN_BLOG_GUIDE + anchor, 1)
    _patch_file(ROOT/'en'/'blog'/'index.html', patch_en_blog_index)
    _patch_file(ROOT/'privacy'/'index.html', lambda t: patch_privacy(t, False))
    _patch_file(ROOT/'en'/'privacy'/'index.html', lambda t: patch_privacy(t, True))

    # English blog: an old brand substitution replaced "Montessori Nursery"
    # with the brand in the Montessori guide's title, H1, schema and every
    # card linking to it, so the page lost its head term ("montessori
    # nursery jeddah", "montessori school").
    def patch_en_blog(text):
        text = text.replace('<title>Kawkab Al-Tifl Al-Hurr Kindergarten in Jeddah</title>',
            "<title>Montessori Nursery in Jeddah: A Parent's Guide | Kawkab Al-Tifl</title>")
        text = text.replace('Kawkab Al-Tifl Al-Hurr Kindergarten in Jeddah', 'Montessori Nursery in Jeddah')
        for old in ('<title>Blog | Kawkab Al-Tifl Al-Hurr Kindergarten &mdash; Parent Guides</title>',
                    '<title>Nursery, Preschool &amp; Montessori Guides for Jeddah Parents | Kawkab Al-Tifl</title>'):
            text = text.replace(old, '<title>Nursery &amp; Montessori Guides for Jeddah Parents | Kawkab Al-Tifl</title>')
        # English pages carry no hreflang at all; give each a self-referencing
        # en + x-default next to its canonical (there is no Arabic twin).
        if 'hreflang=' not in text:
            m = re.search(r'<link rel="canonical" href="([^"]+)"\s*/?>', text)
            if m:
                tags = f'<link rel="alternate" hreflang="en" href="{m.group(1)}"/><link rel="alternate" hreflang="x-default" href="{m.group(1)}"/>'
                text = text[:m.end()] + tags + text[m.end():]
        return en_facts(text)
    # English pages were written outside the facts gate. Bring them in line:
    # no review count (facts.py: the number changes), and the official stage
    # names (Pre-KG 2-3, KG1 3-4, KG2 4-5) instead of "Nursery, Pre-K,
    # Kindergarten" for our own programmes.
    def en_facts(text):
        text = re.sub(r'(4\.7(?:&#9733;</strong>|\u2605</strong>| stars)?)\s+from\s+\d+\s+(?:Google\s+)?reviews',
                      r'\1 on Google Maps', text)
        text = re.sub(r'\b[Nn]ursery, [Pp]re-K(?:\s*/\s*[Pp]reschool)?,?\s+(?:and\s+)?[Kk]indergarten',
                      'Pre-KG (2\u20133), KG1 (3\u20134), KG2 (4\u20135)', text)
        return text
    _patch_file(ROOT/'en'/'index.html', en_facts)
    en_blog = ROOT/'en'/'blog'
    if en_blog.is_dir():
        for page in en_blog.rglob('index.html'):
            if _patch_file(page, patch_en_blog) and page.parent != en_blog:
                indexnow(f"{SITE}/en/blog/{page.parent.name}/")

def article_date(article, fallback):
    raw = article.get('published')
    try:
        return datetime.date.fromisoformat(str(raw)[:10]) if raw else fallback
    except (TypeError, ValueError):
        return fallback

def repair_published_articles(q, today):
    titles={x.get('slug',''):{'title':x.get('title',''),'cat':x.get('cat','dev'),'pub':bool(x.get('published')),'rw':x.get('rewritten')} for x in q}
    allslugs=set(titles)
    for a in q:
        if not a.get('published') or not a.get('slug'):
            continue
        d=article_date(a, today)
        art_dir=ROOT/'blog'/a['slug']
        art_dir.mkdir(parents=True, exist_ok=True)
        (art_dir/'index.html').write_text(
            render_article(a, d.isoformat(), d, allslugs | set(a.get('related') or []), titles),
            encoding='utf-8')

def shadowing_redirect(slug):
    """Return the redirect target when the site sends this slug elsewhere.

    A slug can carry an nginx redirect added while it was only a link target.
    Publishing into it would write a page the redirect hides: visitors and
    crawlers follow the 301 and never see it, while the run reports success.
    Checked over HTTP so it reflects what a visitor actually gets.
    """
    import urllib.request, urllib.error
    url = 'https://montessori-ksa.com/blog/%s/' % slug
    req = urllib.request.Request(url, method='HEAD')

    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=10) as resp:
            code, target = resp.status, resp.headers.get('Location')
    except urllib.error.HTTPError as exc:
        code, target = exc.code, exc.headers.get('Location')
    except Exception:
        # A network failure must not stop publishing; the fact gate still ran.
        return None
    if code in (301, 302, 307, 308) and target:
        return target
    return None


def main():
    today=datetime.date.today(); iso=today.isoformat()
    raw_q=json.loads(QUEUE.read_text())
    raw_q=ensure_auto_queue(raw_q, today)
    raw_q=prune_templated_pending(raw_q)
    raw_q=apply_rewrites(raw_q)
    raw_q=apply_text_fixes(raw_q)
    q=[normalized_article(a) for a in raw_q]
    if q != raw_q or _REWRITE_APPLIED:
        QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')
    repair_static_site()
    repair_published_articles(q, today)
    write_llms_txt()
    write_llms_full(q)
    prune_noindex_from_sitemap(q)
    announce_rewrites(q, today)
    pending=[a for a in q if not a.get('published')]
    hz=health()
    hz_ok=all(v==200 for v in hz.values())
    # فحص صحّة السيو اليومي (حارس التقييم المزيّف + سكيمّا + خريطة + مقالات)
    seo_rows, seo_worst = seo_healthcheck()
    seo_lbl={'ok':'✅ سليم تماماً','warn':'⚠️ ملاحظات بسيطة','fail':'⛔ يحتاج تدخّلاً'}[seo_worst]
    seo_sec=(f'<h3 style="color:#184e3e">🔍 فحص السيو اليومي — {seo_lbl}</h3>'
             f'{seo_health_html(seo_rows)}')
    # تنبيه منفصل عند فشل سيو حقيقي (زي الفاحص الأمني)
    if seo_worst=='fail':
        fails=[f"{l}: {d}" for l,s,d in seo_rows if s=='fail']
        email("🚨 [kawkab] تنبيه سيو — فحص فاشل يحتاج تدخّلاً",
              '<div dir="rtl" style="font-family:Tahoma,sans-serif;line-height:1.9">'
              '<h2 style="color:#c0392b">⛔ فحص السيو اليومي رصد مشكلة</h2>'
              '<p>عناصر فاشلة يجب معالجتها فوراً (قد تضرّ الترتيب أو تخالف سياسات جوجل):</p><ul>'
              + "".join(f'<li>{esc(x)}</li>' for x in fails) + '</ul></div>')

    if not pending:
        log("queue empty")
        email("⚠️ [kawkab] تقرير السيو اليومي — الطابور فرغ",
              f'<div dir="rtl" style="font-family:Tahoma,sans-serif"><h2 style="color:#b45309">انتهى مخزون المقالات</h2>'
              f'<p>نشرنا كل المقالات الجاهزة. لتزويد الطابور بمقالات جديدة، شغّل توليد دفعة جديدة.</p>'
              f'<p>فحص الصحة: {"✅ سليم" if hz_ok else "⚠️ "+json.dumps(hz,ensure_ascii=False)}</p>'
              f'{seo_sec}</div>')
        return

    # حاجز الحقائق — لا يُكتب أي ملف قبل اجتيازه (تصميم 2026-09-13)
    if facts is None:
        log(f"facts module unavailable — publishing suspended: {FACTS_IMPORT_ERROR}")
        email("🚨 [kawkab] حاجز الحقائق غير متاح — النشر متوقف",
              '<div dir="rtl" style="font-family:Tahoma,sans-serif;line-height:1.9">'
              '<h2 style="color:#c0392b">⛔ تعذّر تحميل حاجز الحقائق</h2>'
              f'<p>خطأ الاستيراد: {esc(FACTS_IMPORT_ERROR)}</p>'
              '<p>تم إيقاف نشر أي مقال هذا التشغيل حفاظاً على السلامة، '
              'مع استمرار إصلاحات الموقع وفحص السيو كالمعتاد.</p></div>')
        return
    blocked=[]
    a=None
    for cand in pending:
        why=facts.check_article(cand)
        if why:
            cand['blocked']=True; cand['blocked_reasons']=why
            blocked.append((cand.get('slug','?'), why))
            log(f"blocked {cand.get('slug','?')}: {'; '.join(why)}")
            continue
        dup=duplicate_of(cand, [x for x in q if x.get('published')])
        if dup:
            why=['المحتوى مكرر بنسبة %d%% مع مقال منشور (%s). أعد كتابته بمحتوى مختلف.'
                 % (round(dup[1]*100), dup[0])]
            cand['blocked']=True; cand['blocked_reasons']=why
            blocked.append((cand.get('slug','?'), why))
            log(f"blocked {cand.get('slug','?')}: duplicate of {dup[0]} ({dup[1]:.2f})")
            continue
        target=shadowing_redirect(cand.get('slug',''))
        if target:
            why=['الموقع يحوّل هذا الرابط إلى %s، فالمقال سيُنشر محجوباً. '
                 'احذف قاعدة التحويل من nginx قبل نشره.' % target]
            cand['blocked']=True; cand['blocked_reasons']=why
            blocked.append((cand.get('slug','?'), why))
            log(f"blocked {cand.get('slug','?')}: shadowed by redirect -> {target}")
            continue
        cand.pop('blocked', None); cand.pop('blocked_reasons', None)
        a=cand; break
    if blocked:
        QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')
        email("🚨 [kawkab] حاجز الحقائق رفض مقالاً",
              '<div dir="rtl" style="font-family:Tahoma,sans-serif;line-height:1.9">'
              '<h2 style="color:#c0392b">⛔ مقالات مرفوضة قبل النشر</h2>'
              '<p>الحاجز منع نشرها لمخالفتها حقائق المنشأة. صحّح النص في الطابور:</p><ul>'
              + "".join(f'<li><b>{esc(s)}</b><ul>'
                        + "".join(f'<li>{esc(x)}</li>' for x in w) + '</ul></li>'
                        for s, w in blocked) + '</ul></div>')
    if a is None:
        log("all pending articles blocked (facts/duplicate/redirect gates)")
        return
    d=today
    # slugs+titles map for related cards (all queue + assume prior 31 exist)
    titles={x['slug']:{'title':x['title'],'cat':x['cat'],'pub':bool(x.get('published')),'rw':x.get('rewritten')} for x in q}
    allslugs=set(titles) | set()  # related may also point to prior slugs; those resolve at browse time
    # render + write article
    art_dir=ROOT/"blog"/a['slug']; art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir/"index.html").write_text(render_article(a, iso, d, set(titles)|{s for s in (a.get('related') or [])}, titles), encoding='utf-8')

    # patch blog index: insert card at top of its category grid
    idxp=ROOT/"blog"/"index.html"; idx=idxp.read_text()
    m=re.search(r'(<section class="bsec" id="%s">.*?<div class="bgrid">)' % a['cat'], idx, re.S)
    if m:
        rt=max(4, round((a.get('wordCount') or 1100)/180))
        card=(f'<a class="bcard" href="/blog/{a["slug"]}/"><span class="bcard__cat">{esc(CATN[a["cat"]])}</span>'
              f'<h3 class="bcard__title">{esc(a["title"])}</h3><p class="bcard__desc">{esc(a["metaDescription"])}</p>'
              f'<span class="bcard__meta"><time datetime="{iso}">{esc(ar_date(d))}</time> · {rt} دقائق</span></a>')
        idx=idx[:m.end(1)]+card+idx[m.end(1):]; idxp.write_text(idx, encoding='utf-8')
    else:
        log(f"WARN: category section {a['cat']} not found in blog index")

    # patch sitemap
    smp=ROOT/"sitemap.xml"; sm=smp.read_text()
    pr="0.8" if a['cat']=='local' else "0.7"
    block=(f'  <url>\n    <loc>{SITE}/blog/{a["slug"]}/</loc>\n    <lastmod>{iso}</lastmod>\n'
           f'    <changefreq>monthly</changefreq>\n    <priority>{pr}</priority>\n  </url>\n</urlset>')
    if a['slug'] not in sm:
        sm=sm.replace("</urlset>", block); smp.write_text(sm, encoding='utf-8')

    # mark published
    a['published']=iso
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')

    # verify live + indexnow
    url=f"{SITE}/blog/{a['slug']}/"
    try: live=urllib.request.urlopen(url,timeout=15).status
    except Exception as e: live=str(e)
    inx=indexnow(url)
    remaining=len([x for x in q if not x.get('published')])
    a_idx=pending.index(a)
    next_up=next((c for c in pending[a_idx+1:] if not c.get('blocked')), None)

    st={"last_run":iso,"published_count":len([x for x in q if x.get('published')]),"remaining":remaining}
    STATE.write_text(json.dumps(st,ensure_ascii=False,indent=1))

    log(f"published {a['slug']} live={live} indexnow={inx} remaining={remaining} seo={seo_worst}")
    subj_ic = "🚨" if seo_worst=='fail' else "📈"
    email(f"{subj_ic} [kawkab] تقرير السيو اليومي — {ar_date(d)}",
      f'<div dir="rtl" style="font-family:Tahoma,Arial,sans-serif;line-height:1.9;color:#22302a;max-width:640px">'
      f'<h2 style="color:#184e3e">📈 تقرير السيو اليومي — {ar_date(d)}</h2>'
      f'<p style="background:#eaf5ef;border-radius:10px;padding:10px 14px"><b>يعمل تلقائياً على السيرفر</b> — مستقل تماماً.</p>'
      f'<h3 style="color:#184e3e">✅ نُشر اليوم</h3><p><a href="{url}">{esc(a["title"])}</a><br/>الكلمة المستهدفة: {esc(a.get("targetKeyword",""))} — الحالة: {live} — IndexNow: {inx}</p>'
      f'{seo_sec}'
      f'<h3 style="color:#184e3e">🩺 فحص الوصول (HTTP)</h3><p>{"✅ الموقع والمدوّنة والخريطة و robots سليمة (200)" if hz_ok else "⚠️ "+esc(json.dumps(hz,ensure_ascii=False))}</p>'
      f'<h3 style="color:#184e3e">📋 المتبقّي في الطابور</h3><p>{remaining} مقال — ' + ((f'التالي: {esc(next_up["title"])}' if next_up else 'لا يوجد مقال آخر جاهز للنشر حالياً') if remaining>0 else 'الطابور على وشك الانتهاء — يُنصح بالتزويد') + '</p>'
      f'<hr style="border:none;border-top:1px solid #e9e0cf"/><p style="color:#79857c;font-size:13px">كوكب الطفل الحر · montessori-ksa.com · ناشِر آلي على السيرفر</p></div>')

if __name__=="__main__":
    if '--audit' in sys.argv:
        rows = facts.audit_dir(str(ROOT/'blog'))
        for p, why in sorted(rows):
            print(p)
            for x in why:
                print('   -', x)
        print('VIOLATING FILES:', len(rows))
        sys.exit(1 if rows else 0)
    # self-update.sh runs right before this publisher from the same crontab,
    # but a change to self-update.sh itself only acts on its *next* run. Run
    # the freshly installed copy once more here (it is idempotent) so a new
    # install step — e.g. the nursery Excel importer — lands the same day.
    try:
        subprocess.run(['/bin/bash', '/opt/seo/self-update.sh'], timeout=900, check=False)
    except Exception as ex:
        log(f"self-update rerun skipped: {ex}")
    try: main()
    except Exception as ex:
        log(f"FATAL {ex}")
        try: email("⚠️ [kawkab] تقرير السيو اليومي — خطأ", f'<div dir=rtl>حدث خطأ في الناشِر: {esc(ex)}</div>')
        except Exception: pass
        sys.exit(1)
