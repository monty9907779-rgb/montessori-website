# -*- coding: utf-8 -*-
"""مرجع حقائق روضة كوكب الطفل الحر — المصدر الوحيد لما يُسمح بنشره.

يستورده الناشر اليومي /opt/seo/publish.py ومولّد GEO
/opt/geo-watch/geo_autopilot.py. المكتبة القياسية فقط.

الأعمار من ٣ إلى ٥ سنوات فقط (أكّدها المالك 2026-11-03، وتلغي سلّم 2026-09-13):
    المستوى الأول 3-4 · المستوى الثاني 4-5 · البرنامج الصيفي
لا توجد لدينا مرحلة ما قبل الروضة (2-3) ولا التمهيدي (5-6). يبقى الاسمان في
STAGE_AGES حتى يُرفض أي عمر خاطئ لهما في شرح عام، ونسبتهما إلينا مرفوضة.
"""
import os
import re

DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

FACTS = """حقائق المنشأة المسموح ذكرها (ولا تذكر أي حقيقة غيرها عنها):
- الاسم: روضة كوكب الطفل الحر، جدة.
- الموقع: حي الفيصلية، شارع محمد عبدالكريم، جدة.
- الأعمار: من ٣ إلى ٥ سنوات فقط.
- المراحل: المستوى الأول (٣–٤) · المستوى الثاني (٤–٥) · البرنامج الصيفي.
  لا يوجد لدينا ما قبل الروضة ولا التمهيدي.
- الدوام: الأحد إلى الخميس، من الثامنة صباحاً حتى الواحدة ظهراً.
- المنهج: مونتيسوري الأصيل + اللغة العربية الفصحى + الإنجليزية + تعليم القرآن.
- المزايا: بيئة مُعدّة، كاميرات مراقبة، تطبيق تواصل مع الأسرة.
- لا تذكر: «ضيافة بالساعة» ولا «معلمات مؤهلات» ولا «أكثر من ١٠ سنوات» (غير مؤكدة، أزالها المالك 2026-11-08).
- التواصل: واتساب 0541558173.
- التقييمات: آراء الأهالي على خرائط جوجل (لا تذكر رقم تقييم ولا عدد مراجعات).
"""

RULES = """قواعد ملزمة:
1. ممنوع منعاً باتاً ذكر أي سعر أو رقم رسوم أو "يبدأ من" أو نطاق أسعار للمنشأة.
   القاعدة الصحيحة: الرسوم تُحدَّد حسب عمر الطفل وعدد الأيام وساعات الدوام،
   ويُحدَّد الرقم الدقيق عبر مكالمة أو زيارة. اشرح هذه القاعدة بوضوح.
   يجوز الحديث عن أسعار سوق الحضانات في جدة بصيغة عامة دون نسبتها إلينا.
2. ممنوع ذكر أعمار غير ٣–٥ للمنشأة، وممنوع ذكر مرحلة "رضّع" أو "أقل من ٣ سنوات".
   لو السؤال عن عمر خارج نطاقنا، قل بصراحة إننا نستقبل من ٣ إلى ٥ ووجّه لغيره بلطف.
   لازم تذكر نطاق «من ٣ إلى ٥ سنوات» صراحةً بهذه الصيغة مرة على الأقل.
3. مراحلنا بالتسمية السعودية الرسمية: المستوى الأول (٣–٤) والمستوى الثاني (٤–٥)،
   مع البرنامج الصيفي. ممنوع نسبة «ما قبل الروضة» أو «التمهيدي» إلينا.
   ممنوع تسمية أي مرحلة "الحضانة (١–٢)" أو "التمهيدي (٢–٤)" أو "الروضة (٤–٦)".
   ممنوع ذكر رقم تقييم (مثل 4.7★)؛ الإحالة لآراء الأهالي على جوجل فقط.
4. ممنوع اختراع تراخيص أو اعتمادات أو جوائز أو عدد أطفال.
   ممنوع ذكر عدد سنوات خبرة.
5. ممنوع ذكر أسماء حضانات منافسة.
6. الفقرة الأولى تجاوب على السؤال مباشرة في جملتين — هذا ما تقتبسه محركات الذكاء الاصطناعي.
7. عربية فصحى واضحة، موجّهة لأم في جدة. بدون مبالغات تسويقية فارغة.
"""

# ------------------------------------------------------------------
# اقتران اسم المرحلة بعمرها. الرقم وحده ليس مخالفة — الاقتران هو المخالفة.
# 'التمهيدي (٥–٦)' يمر. 'الروضة (٤–٦)' تُرفض.
# ------------------------------------------------------------------
# «ال» اختيارية عمداً: النص الحقيقي يكتب «معلمة تمهيدي (2–4)» بلا أداة تعريف،
# وبدونها يفلت من الفحص.
STAGE_AGES = [
    ('ما قبل الروضة', r'PREKG', (2, 3)),
    ('المستوى الأول', r'(?:ال)?مستوى الأول|KG\s*1', (3, 4)),
    ('المستوى الثاني', r'(?:ال)?مستوى الثاني|KG\s*2', (4, 5)),
    ('التمهيدي', r'(?:ال)?تمهيدي|KG\s*3', (5, 6)),
]

# مدى الاستقبال الكلي (المالك 2026-11-03): مسموح ملتصقاً بـ«الروضة/الحضانة».
INTAKE = (3, 5)

# مدى يلي اسم المرحلة مباشرة: '(2-4 سنوات)' أو ' من 2 إلى 4'
# الحدود تُكتب أحياناً بالكلمات لا بالأرقام (مثال حقيقي في FACTS نفسه:
# «ما قبل الروضة (سنتان–٣)»)، فلازم يفهمها الفاحص وإلا فلتت من كل قواعد الأعمار.
WORD_NUMS = {
    'سنتين': 2, 'سنتان': 2, 'عامين': 2,
    'ثلاث': 3, 'أربع': 4, 'خمس': 5, 'ست': 6,
}
_NUM = r'(?:\d{1,2}|سنتين|سنتان|عامين|ثلاث|أربع|خمس|ست)'
# «التمهيدي (من عامين إلى أربعة)»: كلمة «من» قبل المدى كانت تخرجه من الفحص
# (صفحة bilingual-education-benefits-children الحيّة، 2026-10-10).
_RANGE = r'[^\w؀-ۿ]{0,12}(?:من\s+)?(' + _NUM + r')\s*(?:إلى|الى|حتى|[-–—])\s*(' + _NUM + r')'

# مدى متبوع بوحدة زمن غير العمر (ساعات نوم، دقائق نشاط...) مش عمر مرحلة.
# مثال حقيقي: «طفل التمهيدي ينام 10-13 ساعة يومياً» — رقمان بعد اسم مرحلة
# لكنهما ساعات نوم لا أعمار، وبدون هذا الاستثناء يرفضهما الحاجز للأبد.
_NON_AGE_UNIT = re.compile(
    r'^\s*(?:ساعة|ساعات|دقائق|دقيقة|أشهر|شهر|أيام|يوم)\b')


def _num(s):
    """يحوّل حد المدى (رقم أو كلمة) إلى عدد صحيح."""
    return int(s) if s.isdigit() else WORD_NUMS.get(s)


_STAGE_WORD = re.compile(
    r'PREKG|(?:ال)?مستوى الأول|(?:ال)?مستوى الثاني|(?:ال)?تمهيدي|(?:ال)?حضانة|(?:ال)?روضة')

# فقرة 1 من RULES تسمح صراحةً بذكر أسعار سوق الحضانات في جدة بصيغة عامة
# دون نسبتها إلينا. القاعدة القديمة كانت ترفض أي رقم+ريال بلا سياق فتصطدم
# بهذا الاستثناء المكتوب في نفس الملف — فُصل الفحص لدالة مخصّصة (تحت) بدل
# regex بسيط ضمن BANS.
#
# الأسعار هي القاعدة الوحيدة هنا اللي فيها المبالغة في الرفض أأمن من
# المبالغة في القبول (عكس قواعد الأعمار): سعر مخترع وعد كاذب لعميلة،
# والقاعدة 1 أصلاً بتطلب تفسير إن الرسوم بمكالمة أو زيارة. فالاستثناء
# ضيّق وإيجابي: لازم تُذكر عبارة تحدّد "السوق" كموضوع الجملة صراحة —
# ظرف عام زي "عموماً" أو "في السوق" وحده مش كافي — ولازم الجملة تخلو
# تماماً من أي إشارة لذاتنا (صيغة "نا" أو اسم المنشأة).
# "الروضة" المفردة = اسم المنشأة (نفس المعنى المستخدم في
# _check_orphan_stage_ages)، أما "الروضات" الجمع فهي السوق ولا تُطابق
# "الروضة" كسلسلة فرعية (الحرف الأخير مختلف: ة مقابل ات).
GENERALITY_CUES = ('أسعار الحضانات', 'أسعار الروضات', 'سوق الحضانات',
                    'أسعار السوق', 'متوسط أسعار', 'رسوم الحضانات',
                    'الرسوم الشهرية للحضانات', 'متوسط الرسوم', 'رسوم حضانة',
                    'الحضانات في جدة', 'حضانات اقتصادية', 'حضانات متوسطة',
                    'حضانات مميّزة', 'تصنيف الحضانات', 'تكلفة الساعة',
                    'تتراوح غالباً', 'غالباً بين', 'بشكل عام')
ATTRIBUTION_CUES = ('رسومنا', 'أسعارنا', 'سعرنا', 'تكلفتنا', 'عندنا', 'لدينا',
                    'حضانتنا', 'روضتنا', 'كوكب الطفل')
# نفي صريح لاستقبال الرضّع — جملة رافضة مش ادعاء (قاعدة ٢ تطلب قولها)
_NEGATED = re.compile(r'(?:لا نستقبل|لا نقبل|لا نستقبلهم|نعتذر عن استقبال|دون السنتين|غير مشمول)')
# نسبة سعرية صريحة إلينا: «سعر الروضة»، «رسوم الحضانة»… (غير «برنامج الروضة»)
_PRICE_OF_OURS = re.compile(r'(?:سعر|أسعار|رسوم|تكلفة)\s+ال(?:روضة|حضانة)\b')
_PRICE = re.compile(r'(\d[\d,\.]{2,})\s*(ريال|ر\.س|SAR)')

BANS = [
    ('سعر مخترع', re.compile(r'(رسومنا|أسعارنا|رسوم حضانتنا)[^.]{0,40}\d')),
    ('ادعاء عمر غلط',
     re.compile(r'(?:نستقبل|نرحّب ب|نقبل|لدينا برنامج|مع أطفالنا|أطفالنا من)[^.؟]{0,45}'
                r'(?:رضّع|الرضع|عمر سنة|عمر عام|أقل من سنتين|1[–-]2 سنة|سنة إلى (?:ست|٦|6))')),
    # «من 71 أسرة على خرائط جوجل» أفلتت لأن القاعدة أدناه تطلب كلمة مراجعة/تقييم
    ('عدد مراجعات', re.compile(r'من\s*[\d٠-٩]+\s*(?:أسرة|عائلة|أهل|ولي أمر|أولياء)')),
    ('مرحلة غير موجودة', re.compile(r'(?:برنامج )?الحضانة\s*\(\s*(?:0|1)\s*[-–]\s*[12]')),
    # ساعة الإغلاق تُكتب رقماً مجرّداً أحياناً («8 صباحاً - 2 ظهراً») فتفلت
    # من الصيغ الثلاث الأولى. الدوام ينتهي الواحدة ظهراً.
    ('دوام غلط', re.compile(r'الثانية ظهر|14:00|2:00 ظهر|\b2\s*ظهر')),
    # عدد المراجعات ممنوع ذكره — الرقم يتغيّر. يُمسك بالأرقام وبالحروف معاً:
    # «71 تقييماً» كان يفلت لأن \b بعد حرف عربي لا يقع، و«واحدٍ وسبعين مراجعة»
    # كان يفلت لأن القاعدة تطلب رقماً. (اتصلحت 13/9 بعد أن أفلتت ٦ صفحات حيّة)
    ('عدد مراجعات', re.compile(r'\d+\s*(?:مراجعة|مراجعات|تقييم\w*)')),
    # \u064B-\u0652 = التشكيل. «واحدٍ» كان يفلت لأن التنوين ليس حرفاً في \w.
    ('عدد مراجعات', re.compile(
        r'(?:واحد|اثن|ثلاث|أربع|خمس|ست|سبع|ثمان|تسع)[\w\u064B-\u0652]*\s*'
        r'(?:و?(?:عشرين|ثلاثين|أربعين|خمسين|ستين|سبعين|ثمانين|تسعين))'
        r'[^.،]{0,15}(?:مراجعة|مراجعات|تقييم\w*)')),
    ('وسوم ممنوعة', re.compile(r'<(html|head|body|script|style)\b')),
]

# ضمان إيجابي: لازم يذكر نطاقنا صراحةً.
# سابقة موثّقة (autopilot.log 8/8): الحاجز كان يطلب ٣–٥ بعد توحيد الأعمار على
# ٢–٥ فصار يرفض المحتوى الصحيح. المالك أعاد النطاق إلى ٣–٥ في 2026-11-03.
# أي تغيير هنا يتبعه تشغيل الاختبارات.
MUST = re.compile(
    r'(?:ثلاث|الثالثة|٣|3)(?:\s*(?:سنوات|سنة|أعوام))?\s*(?:إلى|الى|حتى|[–-])\s*(?:٥|5|خمس|الخامسة)')

_TAG = re.compile(r'<[^>]+>')
_SCRIPT = re.compile(r'<(script|style)[^>]*>.*?</\1>', re.S | re.I)


def normalize(text):
    """توحيد النص قبل الفحص: أرقام عربية، مسافات، وتوحيد اسم ما قبل الروضة."""
    t = str(text or '').translate(DIGITS)
    t = re.sub(r'\s+', ' ', t)
    # يُوحَّد أولاً حتى لا تلتقط قاعدة 'التمهيدي' كلمة 'ما قبل التمهيدي'
    t = re.sub(r'ما\s*قبل\s*ال(?:روضة|تمهيدي)', 'PREKG', t)
    t = re.sub(r'\bPre[\s-]?KG\b', 'PREKG', t, flags=re.I)
    return t



def _check_stage_ages(t):
    out = []
    for label, pattern, (lo, hi) in STAGE_AGES:
        for m in re.finditer(pattern, t):
            tail = t[m.end():m.end() + 30]
            nxt = _STAGE_WORD.search(tail)
            if nxt:
                tail = tail[:nxt.start()]
            r = re.match(_RANGE, tail)
            if not r:
                continue
            if _NON_AGE_UNIT.match(tail[r.end():]):
                continue
            got = (_num(r.group(1)), _num(r.group(2)))
            if got != (lo, hi):
                out.append('عمر مرحلة خاطئ — %s: وجد %s-%s والصحيح %d-%d'
                           % (label, got[0], got[1], lo, hi))
    return out


# «الروضة» و«الحضانة» اسمان للمنشأة أو للنشاط، وليسا اسمي مرحلة. أي مدى
# أعمار ملتصق بأحدهما يعني سلّماً قديماً أو مرحلة مخترعة. «الحضانة» أُضيفت
# 2026-09-13: صفحة nursery-prices-jeddah الحيّة كانت تعدّد
# «الحضانة (3-4 سنوات)» ثم «المستوى الأول (3-4 سنوات)» — مرحلة لا وجود لها،
# بنفس عمر مرحلة حقيقية، والتمهيدي غائب. القواعد كانت تعرف «الروضة» وحدها
# فمرّ السلّم كله بلا اعتراض.
_NOT_A_STAGE = r'(?:برنامج |مرحلة |معلمة )?(?:ال)?(?:روضة|حضانة)'


def _check_orphan_stage_ages(t):
    """اسم المنشأة/النشاط مقترناً بعمر مرحلة = تسمية خاطئة."""
    out = []
    for m in re.finditer(_NOT_A_STAGE, t):
        tail = t[m.end():m.end() + 30]
        nxt = _STAGE_WORD.search(tail)
        if nxt:
            tail = tail[:nxt.start()]
        r = re.match(_RANGE, tail)
        if not r:
            continue
        if _NON_AGE_UNIT.match(tail[r.end():]):
            continue
        got = (_num(r.group(1)), _num(r.group(2)))
        if got != INTAKE:  # مدى الاستقبال الكلي مسموح
            out.append('«%s» مقترنة بعمر مرحلة (%s-%s) — التسمية الصحيحة '
                       'المستوى الأول/الثاني/التمهيدي'
                       % (m.group(0).strip(), got[0], got[1]))
    return out


# المدى قبل الاسم: «من 3 إلى 4 سنوات (التمهيدي)». الفحصان أعلاه يقرآن المدى
# بعد اسم المرحلة فقط، فمرّت صفحة montessori-for-kids-guide الحيّة بثلاثة
# عناوين بهذا الشكل (اكتُشفت 2026-10-10). «الروضة/الحضانة» بين القوسين
# تسمية مخترعة كما في _check_orphan_stage_ages، ويُسمح بمدى الاستقبال 3-5.
_RANGE_BEFORE = re.compile(
    '(' + _NUM + r')\s*(?:إلى|الى|حتى|[-–—])\s*(' + _NUM + r')'
    r'\s*(?:سنوات|سنة|أعوام|عام)?\s*\(\s*'
    r'(PREKG|(?:ال)?مستوى الأول|(?:ال)?مستوى الثاني|(?:ال)?تمهيدي'
    r'|(?:برنامج |مرحلة )?(?:ال)?(?:روضة|حضانة))\s*\)')


def _check_stage_ages_before(t):
    """مدى أعمار يسبق اسم المرحلة بين قوسين."""
    out = []
    for m in _RANGE_BEFORE.finditer(t):
        got = (_num(m.group(1)), _num(m.group(2)))
        name = m.group(3).strip()
        stage = next(((label, lo, hi) for label, pattern, (lo, hi) in STAGE_AGES
                      if re.fullmatch(pattern, name)), None)
        if stage:
            label, lo, hi = stage
            if got != (lo, hi):
                out.append('عمر مرحلة خاطئ — %s: وجد %s-%s والصحيح %d-%d'
                           % (label, got[0], got[1], lo, hi))
        elif got != INTAKE:
            out.append('«%s» مقترنة بعمر مرحلة (%s-%s) — التسمية الصحيحة '
                       'المستوى الأول/الثاني/التمهيدي' % (name, got[0], got[1]))
    return out


# وصف سوق الحضانات في جدة يحتفظ بتسميته الشائعة (قرار المالك 2026-09-13):
# سلّم المراحل الجديد يخصّ مراحلنا نحن فقط، لا وصف السوق.
MARKET_CUES = ('الحضانات', 'حضانات', 'الروضات', 'السوق', 'بشكل عام',
               'غالباً', 'عادةً', 'تتراوح', 'معظم', 'أغلب', 'في المملكة',
               'في السعودية', 'المتعارف عليه', 'المعتاد')


def _is_market_sentence(sent):
    """جملة تصف السوق ولا تنسب الكلام إلينا."""
    return (any(c in sent for c in MARKET_CUES)
            and not any(c in sent for c in ATTRIBUTION_CUES))


def _ours_only(t, fn):
    """يشغّل فحص المراحل على الجمل المنسوبة إلينا فقط."""
    out = []
    for sent in re.split(r'[.؟!]', t):
        if _is_market_sentence(sent):
            continue
        out.extend(fn(sent))
    return out


def _check_invented_price(t):
    """سعر مذكور مسموح فقط لو الجملة عامة عن سوق جدة وبلا نسبته إلينا.

    الفحص على مستوى الجملة (مقسّمة على . ؟ !) حتى لا تُغسَّل جملة منسوبة
    إلينا بعبارة عمومية في جملة تانية بعيدة عنها.
    """
    out = []
    for sent in re.split(r'[.؟!]', t):
        m = _PRICE.search(sent)
        if not m:
            continue
        # نفس قاعدة المراحل: جملة تصف السوق ولا تنسب الكلام إلينا مسموحة —
        # لكن «سعر/رسوم الروضة» نسبة سعرية إلينا مهما كان ظرف الجملة.
        if _PRICE_OF_OURS.search(sent):
            pass
        elif _is_market_sentence(sent):
            continue
        out.append('سعر مخترع: «%s»' % m.group(0)[:45])
    return out


def _check_program_count(t):
    out = []
    for m in re.finditer(r'برنامج(?:ين|ان)\b', t):
        span = re.split(r'[.؟!]', t[m.end():m.end() + 200])[0]
        n = len(_STAGE_WORD.findall(span))
        if n >= 3:
            out.append('عدد البرامج: قال «برنامجين» وعدّد %d' % n)
    return out


_WRONG_CLOSE = re.compile(r'(?:حتى|إلى|لغاية)\s+الثانية(?!\s+عشرة)|حتى\s+2(?::00)?\s*(?:ظهر|PM|م\b)|14:00')


def _check_hours(sent):
    """دوامنا ينتهي الواحدة ظهراً؛ «حتى الثانية» منسوبة إلينا غلط."""
    m = _WRONG_CLOSE.search(sent)
    return ['دوام غلط: «%s»' % m.group(0)] if m else []


# نسبة مرحلة لا نقدّمها إلينا، أو مدى الاستقبال القديم (٢–٥)، أو رقم تقييم.
# الجملة تُعدّ «منسوبة إلينا» بكلمة صريحة فقط: الأدلة العامة عن طفل السنتين
# أو عن «التمهيدي» في التسمية السعودية تبقى مسموحة.
OURS_CUES = ATTRIBUTION_CUES + ('نستقبل', 'نقبل', 'نقدّم', 'نقدم', 'نوفّر', 'نوفر',
                                'مراحلنا', 'برامجنا', 'برنامجنا', 'أطفالنا', 'فصولنا')
_NOT_OFFERED_NEG = re.compile(r'لا يوجد|لا توجد|لا نقدّم|لا نقدم|لا تقدّم|لا تقدم|لا يقدّم|لا يقدم|لا نستقبل|ليس لدينا|ليست لدينا|لا تشمل|تسبق (?:سنة )?التمهيدي|قبل (?:سنة )?التمهيدي')
# اسم المرحلة منسوب إلينا حين يلي فعل استقبال/تقديم، أو حين تقول الجملة «عندنا/لدينا».
# «الفرق بين الحضانة والروضة والتمهيدي، وكيف نطبّق ذلك في حضانتنا» شرح لا عرض.
OFFER_CUES = ('نستقبل', 'نقبل', 'نقدّم', 'نقدم', 'نوفّر', 'نوفر', 'تستقبل', 'تقدّم', 'تقدم',
              'يقدّم', 'يقدم', 'يجمع بين', 'تجمع بين', 'مرحلتين', 'مراحلنا', 'برامجنا', 'برنامجنا')
_HAVE = re.compile(r'عندنا|لدينا|مراحلنا|برامجنا|برنامجنا')
_NOT_OFFERED = re.compile(r'PREKG|(?<![\w])و?(?:ال)?تمهيدي')
_OLD_INTAKE = re.compile(
    r'(?:سنتين|سنتان|عامين|السنتين|(?<![\d.])2)(?:\s*(?:سنوات|سنة|أعوام|عام))?'
    r'\s*(?:إلى|الى|حتى|[–-])\s*(?:5|خمس|الخامسة)')
_RATING = re.compile(r'(?:تقييم\w*|★)[^.؟!]{0,20}4[.٫]\d|(?<![\d.])4[.٫]\d\s*(?:★|من\s*5|/\s*5|نجوم)')


def _check_ours_claims(sent):
    """مرحلة لا نقدّمها أو مدى ٢–٥ منسوبان إلينا صراحةً."""
    if not any(c in sent for c in OURS_CUES) or _NOT_OFFERED_NEG.search(sent):
        return []
    out = []
    cue = min((i for i in (sent.find(c) for c in OFFER_CUES) if i >= 0), default=-1)
    stage = _NOT_OFFERED.search(sent, cue if cue >= 0 else len(sent))
    if stage or (_HAVE.search(sent) and _NOT_OFFERED.search(sent)):
        out.append('مرحلة لا نقدّمها منسوبة إلينا: «%s»' % sent.strip()[:45])
    m = _OLD_INTAKE.search(sent)
    if m:
        out.append('مدى أعمار قديم (٢–٥) منسوب إلينا: «%s»' % m.group(0))
    return out


_AGE_RANGE = re.compile(r'\d\s*(?:إلى|الى|حتى|[–-])\s*\d(?:\s*(?:سنوات|سنة|أعوام))?')


def check_text(text):
    """يرجّع قائمة أسباب الرفض — فاضية يعني سليم."""
    t = normalize(text)
    bad = []
    for name, rx in BANS:
        # «رسوم حضانتنا … من ٣ إلى ٥ سنوات»: رقما مدى العمر ليسا سعراً
        m = rx.search(_AGE_RANGE.sub(' ', t) if name == 'سعر مخترع' else t)
        if m:
            bad.append('%s: «%s»' % (name, m.group(0)[:45]))
    bad = [b for b in bad if not (b.startswith('ادعاء عمر غلط') and _NEGATED.search(t))]
    bad.extend(_check_invented_price(t))
    bad.extend(_ours_only(t, _check_stage_ages))
    bad.extend(_ours_only(t, _check_orphan_stage_ages))
    bad.extend(_ours_only(t, _check_stage_ages_before))
    bad.extend(_ours_only(t, _check_hours))
    bad.extend(_check_program_count(t))
    bad.extend(_ours_only(t, _check_ours_claims))
    m = _RATING.search(t)
    if m:
        bad.append('رقم تقييم: «%s»' % m.group(0)[:45])
    if not MUST.search(t):
        bad.append('ما ذكرش نطاق أعمارنا (٣–٥) صراحةً')
    return bad


def check_article(a):
    """يفحص عنصر طابور قبل نشره.

    bodyHtml وسومه تُزال أولاً: أسماء الوسوم تحمل أرقاماً (h2، h3) كانت
    تُشبع قواعد الأرقام فتُقرأ «رسوم حضانتنا …</h2>» سعراً مخترعاً.
    الصفحة المنشورة تُفحص بعد التجريد أصلاً في check_html، فهذا يوحّد
    ما يراه الفحصان.
    """
    body = _TAG.sub(' ', _SCRIPT.sub(' ', a.get('bodyHtml') or ''))
    parts = [a.get('title') or '', a.get('metaDescription') or '',
             body, a.get('seoTitle') or '']
    for x in (a.get('faq') or []):
        parts.append('%s %s' % (x.get('q', ''), x.get('a', '')))
    # نقطة فاصلة بين الحقول حتى لا تتسرّب كلمات العنوان إلى جملة المتن
    return check_text(' . '.join(parts))


# ------------------------------------------------------------------
# حاجز الحقائق للصفحات الإنجليزية (/en/blog/*). نفس الحقائق، بصيغة إنجليزية:
# لا أسعار ولا عدد مراجعات ولا رقم تقييم ولا أعمار خارج ٣–٥ ولا دوام غير 8:00–1:00،
# ولا اعتمادات مخترعة. الأعمار العامة للسوق ("kindergarten covers 4 to 6")
# مسموحة، لكن نسبتها إلينا (we/our/Kawkab) هي المخالفة.
# ------------------------------------------------------------------
_EN_US = r'(?:\bwe\b|\bour\b|\bus\b|Kawkab|\bwelcome\b)'
EN_BANS = [
    ('price', re.compile(r'(?:\d[\d,\.]*\s*(?:SAR|SR|riyals?|ريال)|(?:SAR|SR)\s*\d)', re.I)),
    ('our fees', re.compile(r'\b(?:our|the nursery.s|kawkab.s)\s+(?:monthly\s+|annual\s+|tuition\s+)?(?:fees?|prices?|tuition|rates?)\b[^.]{0,50}\d', re.I)),
    ('fees starting from', re.compile(r'\b(?:fees?|prices?|tuition)\s+(?:start|begin)s?\s+(?:from|at)\b[^.]{0,20}\d', re.I)),
    # "4.7/5 rating" is a score, not a count: the digit after a slash is exempt
    ('review count', re.compile(r'(?<![/\d.])\d[\d,]*\s+(?:google\s+)?(?:reviews?|ratings?)\b|\bfrom\s+\d+\s+(?:parents|families)\b', re.I)),
    ('infants', re.compile(_EN_US + r'[^.?!]{0,60}\b(?:infants?|babies|baby|newborns?|toddlers? under|under (?:2|two)|from (?:1|one) year|1[-–]year)', re.I)),
    # 2026-11-03: ages 3 to 5 only; no Pre-KG or KG3/Tamhidi of ours, no star rating
    # "our guide to nursery for a 2-year-old ... what Pre-KG offers" explains; "we offer Pre-KG" claims
    ('stage we do not offer', re.compile(r'(?:\bwe\s+(?:offer|run|have|provide|welcome|admit|take|teach)|\bour\s+(?:programmes?|programs?|stages?|classes|levels)|\bour\s+(?=Pre-?K|KG\s?3|Tamhidi)|Kawkab\S*\s+(?:offers|runs|has|provides|welcomes|admits))[^.?!]{0,80}\b(?:Pre-?KG|Pre-?K\b|KG\s?3|Tamhidi)', re.I)),
    ('old age range', re.compile(_EN_US + r'[^.?!]{0,80}\b(?:aged?|ages|from|for children)\s+(?:2|two)\s*(?:to|-|–|and)\s*(?:5|five)\b', re.I)),
    ('rating', re.compile(r'\b4\.\d\s*(?:★|&#9733;|/\s*5|out of 5|stars?)|\brated\s+4\.\d', re.I)),
    ('wrong hours', re.compile(r'\b(?:until|till|to|-|–)\s*(?:2|14)(?::00)?\s*(?:pm|p\.m\.)|\b14:00\b|\b2:00\s*pm\b', re.I)),
    # generic advice ("check that a nursery is licensed") is fine; claiming it for us is not
    ('invented credential', re.compile(r'(?:\bwe(?:\'re| are| have been)|\bour\b[^.]{0,40}\b(?:is|are)|Kawkab[^.]{0,40}\b(?:is|are))[^.]{0,30}\b(?:licen[sc]ed|accredited|certified by|ministry[- ]approved|award[- ]winning)\b|\bISO\s?\d{4,}|\baward[- ]winning\b', re.I)),
    ('competitor', re.compile(r'\b(?:Little Gate|Kids Academy|Bright Horizons|Kindercare)\b', re.I)),
    ('markup', re.compile(r'<(html|head|body|script|style)\b', re.I)),
]
# KG1 3-4, KG2 4-5 (also "KG1 (ages 3 to 4)"). Pre-KG keeps its official 2-3 so
# a general explanation of the Saudi ladder is still checked. Any other range
# written right after one of these stage names is wrong.
_EN_STAGES = [('pre-?kg', ('2', '3')), ('kg\\s?1', ('3', '4')), ('kg\\s?2', ('4', '5'))]
_EN_NUM = {'two': '2', 'three': '3', 'four': '4', 'five': '5', 'six': '6', 'one': '1'}
EN_MUST = re.compile(r'\b(?:ages?\s+)?(?:3|three)\s*(?:to|-|–|—|and)\s*(?:5|five)\b', re.I)
_EN_TAG = re.compile(r'<[^>]+>')


def _en_norm(text):
    t = _EN_TAG.sub(' ', _SCRIPT.sub(' ', str(text or '')))
    t = re.sub(r'&(?:#x27|#39|rsquo|apos);', "'", t)
    t = re.sub(r'&(?:ndash|#8211|mdash|#8212);', '-', t)
    t = re.sub(r'&nbsp;|&#160;', ' ', t)
    return re.sub(r'\s+', ' ', t)


def check_en_text(text):
    """Reasons to reject English page text; empty list means clean."""
    t = _en_norm(text)
    bad = []
    for name, rx in EN_BANS:
        m = rx.search(t)
        if m:
            bad.append('%s: "%s"' % (name, m.group(0)[:45]))
    for pat, (lo, hi) in _EN_STAGES:
        for m in re.finditer(r'\b' + pat + r'\b\s*[(:,\-–]?\s*(?:ages?\s+)?(\d|one|two|three|four|five|six)\s*(?:to|-|–|—)\s*(\d|one|two|three|four|five|six)\b', t, re.I):
            a = _EN_NUM.get(m.group(1).lower(), m.group(1)); b = _EN_NUM.get(m.group(2).lower(), m.group(2))
            if (a, b) != (lo, hi):
                bad.append('stage age: "%s"' % m.group(0)[:45])
    if not EN_MUST.search(t):
        bad.append('missing our age range (3 to 5)')
    return bad


def check_en_article(a):
    parts = [a.get('title') or '', a.get('metaDescription') or '', a.get('seoTitle') or '',
             a.get('bodyHtml') or '']
    for x in (a.get('faq') or []):
        parts.append('%s %s' % (x.get('q', ''), x.get('a', '')))
    return check_en_text(' . '.join(parts))


# حدود الكتل جملٌ منفصلة: بدونها تلتصق قائمة التنقّل («برامجنا») والعنوان
# وبطاقات المقالات ذات الصلة في «جملة» واحدة، فيُنسب عنوان مقال عن التمهيدي إلينا.
_BLOCK_TAG = re.compile(r'</?(?:p|li|ul|ol|h[1-6]|div|nav|header|footer|section|aside|summary|details'
                        r'|title|td|th|tr|table|figure|figcaption|main|article|span|small|br|button)\b[^>]*>', re.I)


def check_html(html):
    """يفحص صفحة منشورة."""
    body = _SCRIPT.sub(' ', str(html or ''))
    return check_text(_TAG.sub(' ', _BLOCK_TAG.sub(' . ', body)))


def audit_dir(root):
    """يمسح كل index.html تحت المسار ويرجّع [(path, reasons)] للمخالف فقط."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in ('assets', '_status')]
        for fn in filenames:
            if fn != 'index.html':
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding='utf-8', errors='ignore') as f:
                    reasons = check_html(f.read())
            except (IOError, OSError) as ex:
                reasons = ['تعذّرت القراءة: %s' % ex]
            if reasons:
                out.append((p, reasons))
    return out
