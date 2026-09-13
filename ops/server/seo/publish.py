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

def ensure_auto_queue(raw_q, today):
    if not isinstance(raw_q, list):
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
      f'<p>كوكب الطفل الحر في حي الفيصلية بجدة — بيئة تعليمية آمنة مع القرآن والعربية والإنجليزية، بتقييم <strong>4.7★</strong> من 71 مراجعة. احجزي جولة تعريفية وشاهدي بيئتنا المُعدّة عن قرب.</p>'
      f'<div class="cta-card__btns"><a class="btn btn--primary btn--lg" href="/#register">احجزوا زيارة</a>'
      f'<a class="btn btn--soft btn--lg" href="https://wa.me/966541558173" target="_blank" rel="noopener">تواصل واتساب</a></div></aside>')

def faq_block(faq):
    items=''.join(f'<details class="faq__item"><summary>{esc(f["q"])}</summary>'
                  f'<div class="faq__a"><p>{esc(f["a"])}</p></div></details>' for f in (faq or []))
    return f'<section class="faq" aria-label="الأسئلة الشائعة"><h2>الأسئلة الشائعة</h2>{items}</section>'

def related_block(a, allslugs, titles):
    rel=[s for s in (a.get('related') or []) if s in allslugs and s!=a['slug']][:3]
    if len(rel)<3:
        for s in allslugs:
            if s!=a['slug'] and s not in rel: rel.append(s)
            if len(rel)>=3: break
    rel=rel[:3]
    cards=''.join(f'<a class="rel-card" href="/blog/{s}/"><span class="rel-card__cat">{esc(CATN.get(titles.get(s,{}).get("cat","dev")))}</span>'
        f'<span class="rel-card__title">{esc(titles.get(s,{}).get("title",s))}</span>'
        f'<span class="rel-card__go">اقرأ المقال ←</span></a>' for s in rel)
    return f'<nav class="related" aria-label="مقالات ذات صلة"><h2>مقالات قد تهمّك</h2><div class="related__grid">{cards}</div></nav>'

def jsonld(a, iso):
    url=f"{SITE}/blog/{a['slug']}/"; cat=CATN.get(a['cat'],'')
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    j=lambda o: json.dumps(o,ensure_ascii=False,separators=(',',':'))
    bp={"@context":"https://schema.org","@type":"BlogPosting","@id":url+"#article","headline":a['seoTitle'],
        "description":a['metaDescription'],"inLanguage":"ar","url":url,"mainEntityOfPage":{"@type":"WebPage","@id":url},
        "datePublished":iso,"dateModified":iso,"author":{"@type":"Organization","name":"كوكب الطفل الحر","url":SITE+"/"},
        "publisher":{"@type":"Organization","name":"كوكب الطفل الحر","logo":{"@type":"ImageObject","url":SITE+"/logo.png"}},
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

def render_article(a, iso, d, allslugs, titles):
    cat=CATN.get(a['cat'],''); url=f"{SITE}/blog/{a['slug']}/"
    kws=[a.get('targetKeyword','')]+(a.get('secondaryKeywords') or [])
    rt=max(4, round((a.get('wordCount') or 1100)/180))
    return f'''<!doctype html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{esc(a['seoTitle'])}</title>
<meta name="description" content="{esc(a['metaDescription'])}"/>
<meta name="keywords" content="{esc(', '.join(k for k in kws if k))}"/>
<meta name="author" content="كوكب الطفل الحر"/>
<meta name="robots" content="index, follow, max-image-preview:large"/>
<meta name="theme-color" content="#184e3e"/>
<link rel="canonical" href="{url}"/>
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
      <span class="am-dot">·</span><time datetime="{iso}">{esc(ar_date(d))}</time><span class="am-dot">·</span><span>{rt} دقائق قراءة</span></div>
  </header>
  <div class="article__body">
<figure class="article-hero"><img src="{esc(a['imageUrl'])}" alt="{esc(a['imageAlt'])}" width="1200" height="800" loading="eager" fetchpriority="high"/></figure>
{a['bodyHtml']}
  </div>
  {faq_block(a.get('faq'))}
  {cta(a.get('targetKeyword',''))}
  {related_block(a, allslugs, titles)}
  </article>
</main>
{footer()}
</body></html>'''

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
                ('<title>Montessori Nursery in Jeddah | Kawkab Al-Tifl Al-Hurr</title>',
                 '<title>Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K &amp; Kindergarten</title>'),
                ('<meta name="description" content="Kawkab Al-Tifl Al-Hurr Kindergarten in Al Faisaliyyah, Jeddah — Montessori nursery, pre-K and kindergarten for ages 2–5, small classes, bilingual Arabic-English."/>',
                 '<meta name="description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5, with small classes, a safe environment, and daily parent communication."/>'),
                ('<meta property="og:title" content="Montessori Nursery in Jeddah | Kawkab Al-Tifl Al-Hurr"/>',
                 '<meta property="og:title" content="Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K &amp; Kindergarten"/>'),
                ('<meta property="og:description" content="Kawkab Al-Tifl Al-Hurr Kindergarten in Al Faisaliyyah, Jeddah — Montessori nursery for ages 2–5."/>',
                 '<meta property="og:description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>'),
                ('<meta name="twitter:title" content="Montessori Nursery in Jeddah | Kawkab Al-Tifl Al-Hurr"/>',
                 '<meta name="twitter:title" content="Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K &amp; Kindergarten"/>'),
                ('<meta name="twitter:description" content="Kawkab Al-Tifl Al-Hurr Kindergarten in Al Faisaliyyah, Jeddah — Montessori nursery for ages 2–5."/>',
                 '<meta name="twitter:description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>'),
                ('<h1 class="rev">Montessori Nursery in Jeddah<br/><span class="em">Pre-K &amp; kindergarten, ages 2–5</span></h1>',
                 '<h1 class="rev">Kawkab Al-Tifl Al-Hurr Nursery in Jeddah<br/><span class="em">Pre-K &amp; kindergarten, ages 2–5</span></h1>'),
                ('<title>Montessori School in Jeddah | Nursery, Pre-K &amp; KG (Ages 2–5)</title>',
                 '<title>Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K &amp; Kindergarten</title>'),
                ('<meta name="description" content="Authentic Montessori school &amp; nursery in Al Faisaliyyah, Jeddah — ages 2–5. Pre-K and kindergarten, bilingual Arabic–English, small classes. Book a visit."/>',
                 '<meta name="description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5, with small classes, a safe environment, and daily parent communication."/>'),
                ('<meta property="og:title" content="Montessori School in Jeddah | Nursery, Pre-K &amp; KG (Ages 2–5)"/>',
                 '<meta property="og:title" content="Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K &amp; Kindergarten"/>'),
                ('<meta property="og:description" content="Montessori school and nursery in Jeddah — Pre-K and kindergarten for ages 2–5."/>',
                 '<meta property="og:description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>'),
                ('<meta name="twitter:title" content="Montessori School in Jeddah | Nursery, Pre-K &amp; KG (Ages 2–5)"/>',
                 '<meta name="twitter:title" content="Kawkab Al-Tifl Al-Hurr Nursery in Jeddah | Pre-K &amp; Kindergarten"/>'),
                ('<meta name="twitter:description" content="Montessori school and nursery in Jeddah — Pre-K and kindergarten for ages 2–5."/>',
                 '<meta name="twitter:description" content="Kawkab Al-Tifl Al-Hurr nursery and kindergarten in Al Faisaliyyah, Jeddah for ages 2–5."/>'),
                ('<h1 class="rev">Where children grow<br/><span class="em">at their own pace</span><br/>and learn hands-on</h1>',
                 '<h1 class="rev">Kawkab Al-Tifl Al-Hurr Nursery in Jeddah<br/><span class="em">Pre-K &amp; kindergarten, ages 2–5</span></h1>'),
                ('<div class="t"><b>8–1</b><span>Daily · Sun–Thu</span></div>',
                 '<div class="t"><b>08:00–13:00</b><span>Daily · Sun–Thu</span></div>'),
            ]
        else:
            repl = [
                ('<title>حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر</title>',
                 '<title>حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية</title>'),
                ('<meta name="description" content="روضة كوكب الطفل الحر في حي الفيصلية بجدة — حضانة مونتيسوري للأطفال من سنتين إلى ٥ سنوات، بتمهيدي وروضة وفصول صغيرة وتواصل يومي مع الأهالي."/>',
                 '<meta name="description" content="حضانة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، بتمهيدي وروضة وفصول صغيرة وبيئة آمنة وتواصل يومي مع الأهالي."/>'),
                ('<meta property="og:title" content="حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر"/>',
                 '<meta property="og:title" content="حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية"/>'),
                ('<meta property="og:description" content="روضة كوكب الطفل الحر في حي الفيصلية بجدة — حضانة مونتيسوري للأطفال من سنتين إلى ٥ سنوات."/>',
                 '<meta property="og:description" content="حضانة وروضة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات."/>'),
                ('<meta name="twitter:title" content="حضانة مونتيسوري في جدة | روضة كوكب الطفل الحر"/>',
                 '<meta name="twitter:title" content="حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية"/>'),
                ('<meta name="twitter:description" content="روضة كوكب الطفل الحر في حي الفيصلية بجدة — حضانة مونتيسوري للأطفال من سنتين إلى ٥ سنوات."/>',
                 '<meta name="twitter:description" content="حضانة وروضة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات."/>'),
                ('<h1 class="rev">حضانة مونتيسوري في جدة<br/><span class="em">تمهيدي وروضة للأطفال ٢–٥ سنوات</span></h1>',
                 '<h1 class="rev">حضانة كوكب الطفل الحر في جدة<br/><span class="em">تمهيدي وروضة للأطفال ٢–٥ سنوات</span></h1>'),
                ('<title>حضانة أطفال في جدة | مونتيسوري تمهيدي وروضة ٢–٥ سنوات</title>',
                 '<title>حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية</title>'),
                ('<meta name="description" content="روضة كوكب الطفل الحر بحي الفيصلية في جدة لأعمار من سنتين إلى ٥ سنوات: تمهيدي وروضة، فصول صغيرة، معلمات مؤهلات، وتقرير يومي لولي الأمر. احجزي زيارة عبر واتساب."/>',
                 '<meta name="description" content="حضانة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات، بتمهيدي وروضة وفصول صغيرة وبيئة آمنة وتواصل يومي مع الأهالي."/>'),
                ('<meta property="og:title" content="حضانة أطفال في جدة | مونتيسوري تمهيدي وروضة ٢–٥ سنوات"/>',
                 '<meta property="og:title" content="حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية"/>'),
                ('<meta property="og:description" content="روضة كوكب الطفل الحر في جدة — تمهيدي وروضة لأعمار من سنتين إلى ٥ سنوات بحي الفيصلية."/>',
                 '<meta property="og:description" content="حضانة وروضة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات."/>'),
                ('<meta name="twitter:title" content="حضانة أطفال في جدة | مونتيسوري تمهيدي وروضة ٢–٥ سنوات"/>',
                 '<meta name="twitter:title" content="حضانة كوكب الطفل الحر في جدة | روضة وتمهيدي حي الفيصلية"/>'),
                ('<meta name="twitter:description" content="روضة كوكب الطفل الحر في جدة — تمهيدي وروضة لأعمار من سنتين إلى ٥ سنوات بحي الفيصلية."/>',
                 '<meta name="twitter:description" content="حضانة وروضة كوكب الطفل الحر في حي الفيصلية بجدة للأطفال من سنتين إلى ٥ سنوات."/>'),
                ('<h1 class="rev">حيث ينمو الطفل<br/><span class="em">وفق إيقاعه</span>،<br/>ويكتشف العالم بيديه</h1>',
                 '<h1 class="rev">حضانة كوكب الطفل الحر في جدة<br/><span class="em">تمهيدي وروضة للأطفال ٢–٥ سنوات</span></h1>'),
                ('<div class="t"><b>٨–١</b><span>يومياً · الأحد–الخميس</span></div>',
                 '<div class="t"><b>٨:٠٠–١٣:٠٠</b><span>يومياً · الأحد–الخميس</span></div>'),
            ]
        for old, new in repl:
            if old in text:
                text = text.replace(old, new, 1)
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
        return text
    _patch_file(ROOT/'index.html', lambda t: patch_home(t, False))
    _patch_file(ROOT/'en'/'index.html', lambda t: patch_home(t, True))
    for install_page in (ROOT/'app'/'index.html', ROOT/'login'/'index.html'):
        _patch_file(install_page, lambda t: re.sub(
            r'assets/install\.js\?v=\d+', 'assets/install.js?v=3', t))
    for css_page in (ROOT/'index.html', ROOT/'en'/'index.html', ROOT/'app'/'index.html', ROOT/'login'/'index.html'):
        _patch_file(css_page, lambda t: re.sub(r'app\.css\?v=\d+', 'app.css?v=22', t))

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
    _patch_file(ROOT/'privacy'/'index.html', lambda t: patch_privacy(t, False))
    _patch_file(ROOT/'en'/'privacy'/'index.html', lambda t: patch_privacy(t, True))

def article_date(article, fallback):
    raw = article.get('published')
    try:
        return datetime.date.fromisoformat(str(raw)[:10]) if raw else fallback
    except (TypeError, ValueError):
        return fallback

def repair_published_articles(q, today):
    titles={x.get('slug',''):{'title':x.get('title',''),'cat':x.get('cat','dev')} for x in q}
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

def main():
    today=datetime.date.today(); iso=today.isoformat()
    raw_q=json.loads(QUEUE.read_text())
    raw_q=ensure_auto_queue(raw_q, today)
    q=[normalized_article(a) for a in raw_q]
    if q != raw_q:
        QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')
    repair_static_site()
    repair_published_articles(q, today)
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
        log("all pending articles blocked by facts gate")
        return
    d=today
    # slugs+titles map for related cards (all queue + assume prior 31 exist)
    titles={x['slug']:{'title':x['title'],'cat':x['cat']} for x in q}
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
    try: main()
    except Exception as ex:
        log(f"FATAL {ex}")
        try: email("⚠️ [kawkab] تقرير السيو اليومي — خطأ", f'<div dir=rtl>حدث خطأ في الناشِر: {esc(ex)}</div>')
        except Exception: pass
        sys.exit(1)
