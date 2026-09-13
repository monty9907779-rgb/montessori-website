# Nursery Facts Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** يمنع الناشر اليومي نشر أي مقال يخالف حقائق الحضانة، وتُصحَّح المقالات المنشورة المخالفة من مصدرها.

**Architecture:** مرجع حقائق واحد (`facts.py`) مصدره المستودع ويُنشر إلى `/opt/nursery-facts/` على السيرفر. يستورده كلٌّ من الناشر `/opt/seo/publish.py` ومولّد GEO `/opt/geo-watch/geo_autopilot.py`. الناشر يفحص المقال قبل كتابته على القرص. تصحيح المحتوى يتم في `queue.json` لأن `repair_published_articles()` تعيد توليد الـHTML منه يومياً.

**Tech Stack:** Python 3 بالمكتبة القياسية فقط (لا تبعيات خارجية — الخادم يفتقر إلى pytest، والاختبارات تعمل بـ`unittest`). الاختبارات تعمل محلياً على الماك (Python 3.9) ثم يُنشر الملف إلى الخادم (Python 3.12)، فيُمنع استخدام صياغة 3.10+ مثل `match` أو `int | None`.

**Spec:** `docs/superpowers/specs/2026-09-13-nursery-facts-gate-design.md`

## Global Constraints

- **سلّم المراحل المرجعي:** ما قبل الروضة `prekg` سنتان–3 · المستوى الأول `kg1` 3–4 · المستوى الثاني `kg2` 4–5 · التمهيدي `kg3` 5–6.
- **صيغة الاستقبال المعلنة:** «من عمر سنتين إلى ٥ سنوات» — لا تتغيّر، مصدرها `src/lib/site-facts.ts`.
- **المكتبة القياسية فقط.** لا تُضاف أي تبعية إلى أي سكربت خادم.
- **قواعد المنع على اقتران اسم المرحلة بعمرها، لا على الأرقام المجردة.** «التمهيدي 5–6» يمر، «الروضة 4–6» تُرفض. منع الرقم `6` وحده يرفض محتوى صحيحاً.
- **نسخة احتياطية قبل كل تعديل على ملف خادم:** `cp -p <file> <file>.bak-factsgate-$(date +%Y%m%d-%H%M%S)`.
- **لا تُصحَّح صفحة HTML لمقال موجود في `queue.json`** — يُلغى التصحيح في اليوم التالي 05:00. المصدر هو الطابور.
- **الناشر يعمل بمستخدم `www-data`.** أي ملف جديد يقرأه يجب أن يكون مقروءاً له.

## File Structure

| الملف | المسؤولية |
|---|---|
| `ops/server/nursery-facts/facts.py` (جديد) | مرجع الحقائق الوحيد: الثوابت + دوال الفحص. مصدر الحقيقة في المستودع. |
| `ops/server/nursery-facts/test_facts.py` (جديد) | اختبارات الوحدة بجمل حقيقية من مقالات منشورة. |
| `/opt/nursery-facts/facts.py` (نشر) | نسخة التشغيل على الخادم. |
| `/opt/seo/publish.py` (تعديل) | إضافة الحاجز قبل الكتابة + بند في تقرير الصحة + وضع `--audit`. |
| `/opt/geo-watch/geo_autopilot.py` (تعديل) | استيراد الثوابت من المرجع المشترك بدل تعريفها محلياً. |
| `ops/server/seo/publish.py` (مرآة) | نسخة المستودع من الناشر بعد التعديل، للتأريخ. |
| `ops/server/geo-watch/geo_autopilot.py` (مرآة) | نسخة المستودع من المولّد بعد التعديل، للتأريخ. |
| `/opt/seo/queue.json` (تعديل بيانات) | تصحيح 23 مقالاً. |

---

### Task 1: مرجع الحقائق ودوال الفحص

**Files:**
- Create: `ops/server/nursery-facts/facts.py`
- Test: `ops/server/nursery-facts/test_facts.py`

**Interfaces:**
- Consumes: لا شيء. هذه أول مهمة.
- Produces:
  - `FACTS: str` · `RULES: str` — كتل نصية تُحقن في مطالبة التوليد
  - `BANS: list` من `(name: str, rx: compiled regex)`
  - `MUST: compiled regex`
  - `check_text(text: str) -> list[str]` — الأساس، تُرجع أسباب الرفض
  - `check_article(a: dict) -> list[str]` — تجمع حقول عنصر الطابور وتنادي `check_text`
  - `check_html(html: str) -> list[str]` — تنزع الوسوم ثم تنادي `check_text`
  - `audit_dir(root: str) -> list[tuple]` — تُرجع `(path, reasons)` لكل ملف مخالف

- [ ] **Step 1: اكتب الاختبار الفاشل**

أنشئ `ops/server/nursery-facts/test_facts.py`. الجمل المغلوطة منقولة حرفياً من مقالات منشورة، والصحيحة من الصفحة الرئيسية وملف الحقائق:

```python
# -*- coding: utf-8 -*-
"""اختبارات مرجع الحقائق — جمل حقيقية من مقالات منشورة على montessori-ksa.com"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import facts

INTAKE = ' نستقبل الأطفال من عمر سنتين إلى 5 سنوات. '

BAD = [
    ('السلّم المغلوط كاملاً',
     'نقدّم برنامجين: الحضانة (1-2 سنة)، والتمهيدي (2-4 سنوات)، والروضة (4-6 سنوات)'),
    ('التمهيدي بعمر خاطئ',
     'البرنامج التمهيدي (2-4 سنوات): بناء الاستقلالية والمهارات الاجتماعية.'),
    ('الروضة بعمر خاطئ',
     'برنامج الروضة (4-6 سنوات): تهيئة أكاديمية متكاملة قبل المدرسة.'),
    ('التسمية القديمة بعد قرار 13/9',
     'التمهيدي (٣–٤ سنوات) والروضة (٤–٥ سنوات) لكل مرحلة معلّماتها.'),
    ('وظيفة بمرحلة خاطئة',
     'معلمة تمهيدي (2–4 سنوات): تنمية المهارات الحركية واللغوية.'),
]

GOOD = [
    ('مدى الاستقبال الكلي على الرئيسية',
     'تمهيدي وروضة للأطفال 2–5 سنوات في بيئة آمنة ومُعدّة بعناية.'),
    ('السلّم السعودي الصحيح',
     'ما قبل الروضة (سنتان–3)، المستوى الأول (3–4)، المستوى الثاني (4–5)، '
     'والتمهيدي (5–6).'),
    ('التمهيدي كسنة أخيرة',
     'التمهيدي: السنة الأخيرة قبل الابتدائي (5–6 سنوات) — تهيئة أكاديمية مباشرة.'),
    ('صيغة الاستقبال الرسمية',
     'نستقبل الأطفال من عمر سنتين إلى 5 سنوات في حي الفيصلية بجدة.'),
]


class TestBadContentRejected(unittest.TestCase):
    def test_each_bad_sentence_is_rejected(self):
        for label, text in BAD:
            reasons = facts.check_text(text + INTAKE)
            self.assertTrue(reasons, 'كان يجب رفض: %s' % label)

    def test_program_count_mismatch_is_named(self):
        text = ('نقدّم برنامجين: الحضانة (1-2 سنة)، والتمهيدي (2-4 سنوات)، '
                'والروضة (4-6 سنوات).') + INTAKE
        reasons = ' '.join(facts.check_text(text))
        self.assertIn('عدد البرامج', reasons)


class TestGoodContentAccepted(unittest.TestCase):
    def test_each_good_sentence_passes(self):
        for label, text in GOOD:
            reasons = facts.check_text(text + INTAKE)
            self.assertEqual([], reasons, 'رفض محتوى صحيح (%s): %s' % (label, reasons))

    def test_arabic_indic_digits_are_understood(self):
        self.assertEqual([], facts.check_text('التمهيدي (٥–٦ سنوات).' + INTAKE))


class TestIntakeRangeRequired(unittest.TestCase):
    def test_missing_intake_range_is_rejected(self):
        reasons = ' '.join(facts.check_text('مرحبا بكم في روضتنا بجدة.'))
        self.assertIn('نطاق أعمارنا', reasons)


class TestExistingBansStillWork(unittest.TestCase):
    def test_invented_price_rejected(self):
        reasons = facts.check_text('رسومنا تبدأ من 1500 ريال شهرياً.' + INTAKE)
        self.assertTrue(reasons)

    def test_review_count_rejected(self):
        reasons = facts.check_text('لدينا 70 مراجعة على خرائط جوجل.' + INTAKE)
        self.assertTrue(reasons)

    def test_infant_claim_rejected(self):
        reasons = facts.check_text('نستقبل الرضّع من عمر سنة.' + INTAKE)
        self.assertTrue(reasons)


class TestHtmlAndArticleWrappers(unittest.TestCase):
    def test_check_html_strips_tags(self):
        html = ('<html><body><p>برنامج الروضة (4-6 سنوات)</p>'
                '<script>var x = 1;</script></body></html>' + INTAKE)
        self.assertTrue(facts.check_html(html))

    def test_check_article_reads_all_text_fields(self):
        article = {
            'title': 'دليل الحضانات',
            'metaDescription': 'وصف عادي',
            'bodyHtml': '<p>البرنامج التمهيدي (2-4 سنوات)</p>' + INTAKE,
            'faq': [{'q': 'سؤال', 'a': 'جواب'}],
        }
        self.assertTrue(facts.check_article(article))


if __name__ == '__main__':
    unittest.main(verbosity=2)
```

- [ ] **Step 2: شغّل الاختبار للتأكد من فشله**

```bash
cd ~/Documents/Codex/montessori-website/ops/server/nursery-facts && python3 test_facts.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'facts'`

- [ ] **Step 3: اكتب المرجع**

أنشئ `ops/server/nursery-facts/facts.py`:

```python
# -*- coding: utf-8 -*-
"""مرجع حقائق روضة كوكب الطفل الحر — المصدر الوحيد لما يُسمح بنشره.

يستورده الناشر اليومي /opt/seo/publish.py ومولّد GEO
/opt/geo-watch/geo_autopilot.py. المكتبة القياسية فقط.

سلّم المراحل هو التسمية السعودية الرسمية (قرار المالك 2026-09-13):
    ما قبل الروضة سنتان-3 · المستوى الأول 3-4 · المستوى الثاني 4-5 · التمهيدي 5-6
مطابق لمستويات أودو prekg/kg1/kg2/kg3.
"""
import os
import re

DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')

FACTS = """حقائق المنشأة المسموح ذكرها (ولا تذكر أي حقيقة غيرها عنها):
- الاسم: روضة كوكب الطفل الحر، جدة.
- الموقع: حي الفيصلية، شارع محمد عبدالكريم، جدة.
- الأعمار: من سنتين إلى ٥ سنوات فقط.
- المراحل: ما قبل الروضة (سنتان–٣) · المستوى الأول (٣–٤) · المستوى الثاني (٤–٥)
  · التمهيدي (٥–٦) · برنامج صيفي · ضيافة بالساعة.
- الدوام: الأحد إلى الخميس، من الثامنة صباحاً حتى الواحدة ظهراً.
- المنهج: مونتيسوري الأصيل + اللغة العربية الفصحى + الإنجليزية + تعليم القرآن.
- المزايا: بيئة مُعدّة، معلمات مؤهلات، كاميرات مراقبة، تطبيق تواصل مع الأسرة.
- التواصل: واتساب 0541558173.
- التقييم: 4.7 من 5 على خرائط جوجل (لا تذكر عدد المراجعات إطلاقاً — الرقم يتغيّر).
"""

RULES = """قواعد ملزمة:
1. ممنوع منعاً باتاً ذكر أي سعر أو رقم رسوم أو "يبدأ من" أو نطاق أسعار للمنشأة.
   القاعدة الصحيحة: الرسوم تُحدَّد حسب عمر الطفل وعدد الأيام وساعات الدوام،
   ويُحدَّد الرقم الدقيق عبر مكالمة أو زيارة. اشرح هذه القاعدة بوضوح.
   يجوز الحديث عن أسعار سوق الحضانات في جدة بصيغة عامة دون نسبتها إلينا.
2. ممنوع ذكر أعمار غير ٢–٥ للمنشأة، وممنوع ذكر مرحلة "رضّع" أو "أقل من سنتين".
   لو السؤال عن عمر خارج نطاقنا، قل بصراحة إننا نستقبل من سنتين إلى ٥ ووجّه لغيره بلطف.
   لازم تذكر نطاق «من سنتين إلى ٥ سنوات» صراحةً بهذه الصيغة مرة على الأقل.
3. أسماء المراحل هي التسمية السعودية الرسمية حصراً: ما قبل الروضة (سنتان–٣)،
   المستوى الأول (٣–٤)، المستوى الثاني (٤–٥)، التمهيدي (٥–٦).
   ممنوع تسمية أي مرحلة "الحضانة (١–٢)" أو "التمهيدي (٢–٤)" أو "الروضة (٤–٦)".
4. ممنوع اختراع تراخيص أو اعتمادات أو جوائز أو عدد أطفال أو سنوات خبرة.
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

# مدى يلي اسم المرحلة مباشرة: '(2-4 سنوات)' أو ' من 2 إلى 4'
_RANGE = r'[^\w؀-ۿ]{0,12}(\d{1,2})\s*(?:إلى|الى|حتى|[-–—])\s*(\d{1,2})'

_STAGE_WORD = re.compile(
    r'PREKG|(?:ال)?مستوى الأول|(?:ال)?مستوى الثاني|(?:ال)?تمهيدي|(?:ال)?حضانة|(?:ال)?روضة')

BANS = [
    ('سعر مخترع', re.compile(r'(\d[\d,\.]{2,})\s*(ريال|ر\.س|SAR)')),
    ('سعر مخترع', re.compile(r'(رسومنا|أسعارنا|رسوم حضانتنا)[^.]{0,40}\d')),
    ('ادعاء عمر غلط',
     re.compile(r'(?:نستقبل|نرحّب ب|نقبل|لدينا برنامج)[^.؟]{0,45}'
                r'(?:رضّع|الرضع|عمر سنة|عمر عام|أقل من سنتين|1[–-]2 سنة)')),
    ('مرحلة غير موجودة', re.compile(r'(?:برنامج )?الحضانة\s*\(\s*(?:0|1)\s*[-–]\s*[12]')),
    ('دوام غلط', re.compile(r'الثانية ظهر|14:00|2:00 ظهر')),
    ('عدد مراجعات', re.compile(r'\d+\s*(?:مراجعة|مراجعات|تقييم(?:اً|ات)?)\b')),
    ('وسوم ممنوعة', re.compile(r'<(html|head|body|script|style)\b')),
]

# ضمان إيجابي: لازم يذكر نطاقنا صراحةً.
# سابقة موثّقة (autopilot.log 8/8): الحاجز كان يطلب ٣–٥ بعد توحيد الأعمار على
# ٢–٥ فصار يرفض المحتوى الصحيح. أي تغيير هنا يتبعه تشغيل الاختبارات.
MUST = re.compile(
    r'(?:سنتين|سنتان|عامين|٢|2)\s*(?:إلى|الى|حتى|[–-])\s*(?:٥|5|خمس|الخامسة)')

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
            got = (int(r.group(1)), int(r.group(2)))
            if got != (lo, hi):
                out.append('عمر مرحلة خاطئ — %s: وجد %d-%d والصحيح %d-%d'
                           % (label, got[0], got[1], lo, hi))
    return out


def _check_orphan_stage_ages(t):
    """'الروضة' اسم المنشأة لا اسم مرحلة، فأي مدى ملتصق بها يعني تسمية قديمة."""
    out = []
    for m in re.finditer(r'(?:برنامج |مرحلة |معلمة )?(?:ال)?روضة', t):
        tail = t[m.end():m.end() + 30]
        nxt = _STAGE_WORD.search(tail)
        if nxt:
            tail = tail[:nxt.start()]
        r = re.match(_RANGE, tail)
        if not r:
            continue
        got = (int(r.group(1)), int(r.group(2)))
        if got != (2, 5):  # مدى الاستقبال الكلي مسموح
            out.append('«الروضة» مقترنة بعمر مرحلة (%d-%d) — التسمية الصحيحة '
                       'المستوى الأول/الثاني/التمهيدي' % got)
    return out


def _check_program_count(t):
    out = []
    for m in re.finditer(r'برنامج(?:ين|ان)\b', t):
        span = re.split(r'[.؟!]', t[m.end():m.end() + 200])[0]
        n = len(_STAGE_WORD.findall(span))
        if n >= 3:
            out.append('عدد البرامج: قال «برنامجين» وعدّد %d' % n)
    return out


def check_text(text):
    """يرجّع قائمة أسباب الرفض — فاضية يعني سليم."""
    t = normalize(text)
    bad = []
    for name, rx in BANS:
        m = rx.search(t)
        if m:
            bad.append('%s: «%s»' % (name, m.group(0)[:45]))
    bad.extend(_check_stage_ages(t))
    bad.extend(_check_orphan_stage_ages(t))
    bad.extend(_check_program_count(t))
    if not MUST.search(t):
        bad.append('ما ذكرش نطاق أعمارنا (٢–٥) صراحةً')
    return bad


def check_article(a):
    """يفحص عنصر طابور قبل نشره."""
    parts = [a.get('title') or '', a.get('metaDescription') or '',
             a.get('bodyHtml') or '', a.get('seoTitle') or '']
    for x in (a.get('faq') or []):
        parts.append('%s %s' % (x.get('q', ''), x.get('a', '')))
    return check_text(' '.join(parts))


def check_html(html):
    """يفحص صفحة منشورة."""
    body = _SCRIPT.sub(' ', str(html or ''))
    return check_text(_TAG.sub(' ', body))


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
```

- [ ] **Step 4: شغّل الاختبارات حتى تنجح كلها**

```bash
cd ~/Documents/Codex/montessori-website/ops/server/nursery-facts && python3 test_facts.py
```

Expected: `OK` — كل الاختبارات ناجحة.

إن رسب اختبار من `TestGoodContentAccepted` فهذا **إنذار كاذب في الحاجز** وليس محتوى خاطئاً: عدّل القاعدة لا الاختبار. هذه بالضبط سابقة 8/8 الموثّقة في الوثيقة.

- [ ] **Step 5: كوميت**

```bash
cd ~/Documents/Codex/montessori-website
git add ops/server/nursery-facts/
git commit -m "feat(facts): shared nursery facts reference with stage-age gate

Single source of truth for what may be published. Rules bind a stage
name to its age, not bare numbers, so the correct 'التمهيدي 5-6' passes
while 'الروضة 4-6' is refused.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: نشر المرجع وتدقيق خط الأساس

**Files:**
- Deploy: `ops/server/nursery-facts/facts.py` → `/opt/nursery-facts/facts.py`
- Create: `docs/superpowers/plans/2026-09-13-baseline-audit.txt` (ناتج التدقيق)

**Interfaces:**
- Consumes: `facts.audit_dir(root)` من المهمة 1.
- Produces: ملف قائمة المخالفات الحقيقية على الموقع الحي — تعتمد عليه المهام 5 و6 و8.

- [ ] **Step 1: انشر المرجع إلى الخادم**

```bash
cd ~/Documents/Codex/montessori-website
ssh root@187.127.79.242 'mkdir -p /opt/nursery-facts'
scp ops/server/nursery-facts/facts.py root@187.127.79.242:/opt/nursery-facts/facts.py
ssh root@187.127.79.242 'chown root:root /opt/nursery-facts/facts.py && chmod 644 /opt/nursery-facts/facts.py'
```

- [ ] **Step 2: تأكد أن `www-data` يستطيع استيراده**

```bash
ssh root@187.127.79.242 'sudo -u www-data python3 -c "import sys; sys.path.insert(0,\"/opt/nursery-facts\"); import facts; print(\"ok\", len(facts.BANS), \"bans\")"'
```

Expected: `ok 7 bans`

- [ ] **Step 3: انسخ الاختبارات وشغّلها على الخادم أيضاً**

الخادم على Python 3.12 والماك على 3.9 — التشغيل على الاثنين يثبت التوافق.

```bash
scp ops/server/nursery-facts/test_facts.py root@187.127.79.242:/opt/nursery-facts/
ssh root@187.127.79.242 'cd /opt/nursery-facts && python3 test_facts.py'
```

Expected: `OK`

- [ ] **Step 4: شغّل تدقيق خط الأساس واحفظ الناتج**

```bash
ssh root@187.127.79.242 'cd /opt/nursery-facts && python3 -c "
import facts, json
rows = facts.audit_dir(\"/var/www/montessori-ksa/blog\")
print(\"VIOLATING FILES:\", len(rows))
for p, r in sorted(rows):
    print(p)
    for x in r: print(\"   -\", x)
"' | tee docs/superpowers/plans/2026-09-13-baseline-audit.txt
```

Expected: قائمة غير فارغة. سجّل العدد — هو الرقم الذي يجب أن يصل إلى صفر في المهمة 8.

- [ ] **Step 5: كوميت**

```bash
cd ~/Documents/Codex/montessori-website
git add docs/superpowers/plans/2026-09-13-baseline-audit.txt
git commit -m "chore(facts): baseline audit of live articles before the fix

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: الحاجز داخل الناشر اليومي

**Files:**
- Modify: `/opt/seo/publish.py` — الاستيراد أعلى الملف، بند في `seo_healthcheck()`، الحاجز في `main()`، وضع `--audit`
- Create: `ops/server/seo/publish.py` (مرآة المستودع بعد التعديل)

**Interfaces:**
- Consumes: `facts.check_article(a) -> list[str]` و `facts.audit_dir(root)` من المهمة 1.
- Produces: عنصر طابور مرفوض يحمل المفتاحين `blocked: True` و `blocked_reasons: list[str]`. تقرأهما المهمة 8.

- [ ] **Step 1: خذ نسخة احتياطية**

```bash
ssh root@187.127.79.242 'cp -p /opt/seo/publish.py /opt/seo/publish.py.bak-factsgate-$(date +%Y%m%d-%H%M%S) && ls -la /opt/seo/publish.py.bak-factsgate-*'
```

- [ ] **Step 2: أضف الاستيراد**

في `/opt/seo/publish.py`، بعد سطر `import json, re, html as H, datetime, pathlib, subprocess, urllib.request, sys` مباشرة:

```python
sys.path.insert(0, "/opt/nursery-facts")
import facts  # مرجع الحقائق المشترك — يُستخدم قبل نشر أي مقال
```

- [ ] **Step 3: أضف بند فحص الحقائق إلى تقرير الصحة**

في `seo_healthcheck()`، قبل `return` مباشرة، أضف:

```python
    # 6) فحص الحقائق على المقالات المنشورة — نفس قواعد الحاجز قبل النشر
    viol = facts.audit_dir(str(ROOT/'blog'))
    if viol:
        add('فحص الحقائق', 'fail',
            '%d مقالاً يخالف حقائق المنشأة: %s'
            % (len(viol), ', '.join(pathlib.Path(p).parent.name for p, _ in viol[:5])))
    else:
        add('فحص الحقائق', 'ok', 'كل المقالات المنشورة مطابقة')
```

- [ ] **Step 4: ضع الحاجز قبل الكتابة على القرص**

في `main()`، استبدل السطر `a=pending[0]` بالكتلة التالية. تختار أول مقال سليم، وتعلّم الراسبين، وتُرسل تنبيهاً:

```python
    # حاجز الحقائق — لا يُكتب أي ملف قبل اجتيازه (تصميم 2026-09-13)
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
```

**ملاحظة للمنفّذ:** السطر `d=today` كان موجوداً بعد `a=pending[0]` مباشرة — أُبقي عليه في نهاية الكتلة ولا يُكرَّر.

- [ ] **Step 5: أضف وضع التدقيق**

في نهاية `/opt/seo/publish.py`، استبدل كتلة التشغيل `if __name__ == '__main__':` بما يلي (إن لم تكن موجودة فأضفها):

```python
if __name__ == '__main__':
    if '--audit' in sys.argv:
        rows = facts.audit_dir(str(ROOT/'blog'))
        for p, why in sorted(rows):
            print(p)
            for x in why:
                print('   -', x)
        print('VIOLATING FILES:', len(rows))
        sys.exit(1 if rows else 0)
    main()
```

- [ ] **Step 6: تحقق من سلامة الملف دون تشغيل النشر**

```bash
ssh root@187.127.79.242 'python3 -m py_compile /opt/seo/publish.py && echo "compile ok"'
ssh root@187.127.79.242 'cd /opt/seo && python3 publish.py --audit | tail -3'
```

Expected: `compile ok` ثم قائمة المخالفات بنفس عدد المهمة 2.

- [ ] **Step 7: اختبر أن الحاجز يرفض فعلاً ولا يكتب ملفاً**

اختبار حي على نسخة معزولة من الطابور — لا يلمس الإنتاج:

```bash
ssh root@187.127.79.242 'python3 - <<PY
import sys, json
sys.path.insert(0, "/opt/nursery-facts")
import facts
q = json.load(open("/opt/seo/queue.json"))
bad = {"slug":"gate-probe","title":"اختبار","metaDescription":"وصف",
       "bodyHtml":"<p>نقدّم برنامجين: الحضانة (1-2 سنة)، والتمهيدي (2-4 سنوات)، والروضة (4-6 سنوات). نستقبل من سنتين إلى 5 سنوات.</p>",
       "faq":[{"q":"س","a":"ج"}]}
why = facts.check_article(bad)
print("REJECTED" if why else "ACCEPTED — الحاجز لا يعمل!")
for x in why: print("  -", x)
import os
print("no file written:", not os.path.exists("/var/www/montessori-ksa/blog/gate-probe"))
PY'
```

Expected: `REJECTED` مع الأسباب، و `no file written: True`

- [ ] **Step 8: أنزل المرآة إلى المستودع وكوميت**

```bash
cd ~/Documents/Codex/montessori-website
mkdir -p ops/server/seo
scp root@187.127.79.242:/opt/seo/publish.py ops/server/seo/publish.py
git add ops/server/seo/publish.py
git commit -m "feat(publisher): refuse articles that fail the facts gate

The daily publisher wrote articles straight to disk with no fact check,
which is how 25 pages got a stage ladder contradicting the canonical
2-5 intake. It now checks each candidate, skips and flags the failures,
alerts by email, and reports facts status in the daily SEO table.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: توحيد مولّد GEO على المرجع المشترك

**Files:**
- Modify: `/opt/geo-watch/geo_autopilot.py` — حذف التعريفات المحلية والاستيراد من المرجع
- Create: `ops/server/geo-watch/geo_autopilot.py` (مرآة المستودع بعد التعديل)

**Interfaces:**
- Consumes: `facts.FACTS`, `facts.RULES`, `facts.BANS`, `facts.MUST` من المهمة 1.
- Produces: لا شيء جديد. الهدف إزالة النسخة المكررة من الحقائق.

- [ ] **Step 1: خذ نسخة احتياطية**

```bash
ssh root@187.127.79.242 'cp -p /opt/geo-watch/geo_autopilot.py /opt/geo-watch/geo_autopilot.py.bak-factsgate-$(date +%Y%m%d-%H%M%S)'
```

- [ ] **Step 2: احذف التعريفات المحلية واستورد**

في `/opt/geo-watch/geo_autopilot.py`، احذف كتل `FACTS` و`RULES` و`BANS` و`MUST` (تقريباً الأسطر 139–201، تبدأ عند `FACTS = """حقائق المنشأة` وتنتهي بنهاية تعريف `MUST`) وضع مكانها:

```python
sys.path.insert(0, '/opt/nursery-facts')
from facts import FACTS, RULES, BANS, MUST  # مرجع الحقائق المشترك
```

⚠️ لا تحذف `SCHEMA` ولا أي شيء بعد `MUST` — كتلة `SCHEMA` تلي `MUST` مباشرة ويجب أن تبقى.

- [ ] **Step 3: تحقق من عدم كسر الملف**

```bash
ssh root@187.127.79.242 'python3 -m py_compile /opt/geo-watch/geo_autopilot.py && echo "compile ok"'
ssh root@187.127.79.242 'cd /opt/geo-watch && python3 -c "
import sys; sys.path.insert(0,\".\")
import geo_autopilot as g
print(\"FACTS has new ladder:\", \"المستوى الأول\" in g.FACTS)
print(\"BANS:\", len(g.BANS))
print(\"validate exists:\", callable(g.validate))
"'
```

Expected: `compile ok` · `FACTS has new ladder: True` · `BANS: 7` · `validate exists: True`

- [ ] **Step 4: أنزل المرآة وكوميت**

```bash
cd ~/Documents/Codex/montessori-website
mkdir -p ops/server/geo-watch
scp root@187.127.79.242:/opt/geo-watch/geo_autopilot.py ops/server/geo-watch/geo_autopilot.py
git add ops/server/geo-watch/geo_autopilot.py
git commit -m "refactor(geo): import facts from the shared reference

The generator owned the only copy of the facts; the publisher had none.
Both now read one file, so changing a fact changes it everywhere.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: تصحيح 23 مقالاً من مصدرها في الطابور

**Files:**
- Modify: `/opt/seo/queue.json`
- Create: `docs/superpowers/plans/2026-09-13-queue-changes.diff` (قائمة التغييرات للمراجعة)

**Interfaces:**
- Consumes: `facts.check_article` للتحقق بعد التصحيح.
- Produces: طابور خالٍ من المخالفات — تعتمد عليه المهمة 8.

- [ ] **Step 1: خذ نسخة احتياطية من الطابور**

```bash
ssh root@187.127.79.242 'cp -p /opt/seo/queue.json /opt/seo/queue.json.bak-factsgate-$(date +%Y%m%d-%H%M%S) && ls -la /opt/seo/queue.json.bak-factsgate-*'
```

- [ ] **Step 2: اكتب قائمة الاستبدال في ملف واحد**

تُكتب مرة واحدة في `/root/repl_rules.py` وتُستخدم حرفياً في المعاينة والتطبيق والمقالين اليتيمين، فالمعروض على المالك هو المطبَّق بالضبط.

```bash
ssh root@187.127.79.242 'cat > /root/repl_rules.py <<PY
# -*- coding: utf-8 -*-
# قائمة الاستبدال المعتمدة — سلّم المراحل السعودي (قرار 2026-09-13)
REPL = [
    (r"نقدّم برنامجين:\s*الحضانة \(1[-–]2 سنة\)،\s*والتمهيدي \(2[-–]4 سنوات\)،\s*والروضة \(4[-–]6 سنوات\)",
     "نقدّم أربع مراحل: ما قبل الروضة (سنتان–3)، والمستوى الأول (3–4)، والمستوى الثاني (4–5)، والتمهيدي (5–6)"),
    (r"البرنامج التمهيدي \(2[-–]4 سنوات\)", "المستوى الأول (3–4 سنوات)"),
    (r"التمهيدي \(2[-–]4 سنوات\)", "المستوى الأول (3–4 سنوات)"),
    (r"التمهيدي \(2[-–]4\)", "المستوى الأول (3–4)"),
    (r"برنامج الروضة \(4[-–]6 سنوات\)", "المستوى الثاني (4–5 سنوات)"),
    (r"الروضة \(4[-–]6 سنوات\)", "المستوى الثاني (4–5 سنوات)"),
    (r"الروضة \(4[-–]6\)", "المستوى الثاني (4–5)"),
    (r"معلمة تمهيدي \(2[–-]4 سنوات\)", "معلمة المستوى الأول (3–4 سنوات)"),
    (r"معلمة روضة \(4[–-]6 سنوات\)", "معلمة المستوى الثاني (4–5 سنوات)"),
    (r"الحضانة \(1[-–]2 سنة\)،\s*", ""),
    (r"الحضانة \(1[-–]2\)،\s*", ""),
]
PY
python3 -c "exec(open(\"/root/repl_rules.py\").read()); print(len(REPL), \"rules\")"'
```

Expected: `11 rules`

- [ ] **Step 3: ولّد قائمة التغييرات المقترحة دون كتابة أي شيء**

```bash
ssh root@187.127.79.242 'python3 - <<PY > /root/queue-changes.txt
import json, re
exec(open("/root/repl_rules.py").read())
q = json.load(open("/opt/seo/queue.json"))
for a in q:
    for field in ("bodyHtml", "metaDescription", "title", "seoTitle"):
        v = a.get(field)
        if not isinstance(v, str):
            continue
        for rx, to in REPL:
            for m in re.finditer(rx, v):
                print("%s [%s]\n   - %s\n   + %s\n" % (a.get("slug"), field, m.group(0), to))
PY
wc -l /root/queue-changes.txt; head -60 /root/queue-changes.txt'
```

- [ ] **Step 4: اعرض القائمة على المالك واحصل على موافقته**

انسخ `/root/queue-changes.txt` إلى المستودع واعرضها. **قف هنا حتى يوافق.** الاستبدال الشامل ممنوع بنص الوثيقة، وأي سطر يعترض عليه المالك يُحذف من `/root/repl_rules.py` قبل الخطوة التالية.

```bash
scp root@187.127.79.242:/root/queue-changes.txt ~/Documents/Codex/montessori-website/docs/superpowers/plans/2026-09-13-queue-changes.diff
```

- [ ] **Step 5: طبّق التصحيح على الطابور**

نفس ملف القواعد المعتمد، مع الكتابة هذه المرة:

```bash
ssh root@187.127.79.242 'python3 - <<PY
import json, re
exec(open("/root/repl_rules.py").read())
q = json.load(open("/opt/seo/queue.json"))
changed = 0
for a in q:
    for field in ("bodyHtml", "metaDescription", "title", "seoTitle"):
        v = a.get(field)
        if not isinstance(v, str):
            continue
        new = v
        for rx, to in REPL:
            new = re.sub(rx, to, new)
        if new != v:
            a[field] = new; changed += 1
    for x in (a.get("faq") or []):
        for k in ("q", "a"):
            v = x.get(k) or ""
            new = v
            for rx, to in REPL:
                new = re.sub(rx, to, new)
            if new != v:
                x[k] = new; changed += 1
json.dump(q, open("/opt/seo/queue.json", "w"), ensure_ascii=False, indent=1)
print("fields changed:", changed)
PY'
```



- [ ] **Step 6: تأكد أن الطابور صار نظيفاً**

```bash
ssh root@187.127.79.242 'python3 - <<PY
import json, sys
sys.path.insert(0, "/opt/nursery-facts")
import facts
q = json.load(open("/opt/seo/queue.json"))
bad = [(a.get("slug"), facts.check_article(a)) for a in q]
bad = [(s, w) for s, w in bad if w]
print("queue items still violating:", len(bad))
for s, w in bad[:10]:
    print(" ", s, w[:2])
PY'
```

Expected: `queue items still violating: 0` — ما عدا `pre-kg-vs-kg-difference` الذي تعالجه المهمة 7. إن ظهر غيره، صحّحه قبل المتابعة.

- [ ] **Step 7: أعد توليد الـHTML من الطابور المصحَّح**

```bash
ssh root@187.127.79.242 'cd /opt/seo && sudo -u www-data python3 -c "
import sys, json, datetime, pathlib
sys.path.insert(0, \"/opt/seo\")
import publish
q = [publish.normalized_article(a) for a in json.loads(publish.QUEUE.read_text())]
publish.repair_published_articles(q, datetime.date.today())
print(\"repaired\", len([a for a in q if a.get(\"published\")]), \"articles\")
"'
```

Expected: `repaired 66 articles`

- [ ] **Step 8: كوميت**

```bash
cd ~/Documents/Codex/montessori-website
git add docs/superpowers/plans/2026-09-13-queue-changes.diff
git commit -m "fix(content): correct the stage ladder in 23 queued articles

Fixed at source in queue.json, not in the rendered HTML: the daily
repair regenerates every published article from the queue, so an HTML
edit would be reverted the next morning.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: تصحيح المقالين اليتيمين

**Files:**
- Modify: `/var/www/montessori-ksa/blog/child-independence-development/index.html`
- Modify: `/var/www/montessori-ksa/blog/child-care-hourly-jeddah/index.html`

**Interfaces:**
- Consumes: `facts.check_html` للتحقق.
- Produces: لا شيء. المقالان خارج الطابور ولا يُعاد توليدهما.

- [ ] **Step 1: خذ نسخة احتياطية**

```bash
ssh root@187.127.79.242 'for s in child-independence-development child-care-hourly-jeddah; do cp -p /var/www/montessori-ksa/blog/$s/index.html /root/$s.html.bak-factsgate; done && ls -la /root/*.bak-factsgate'
```

- [ ] **Step 2: اعرض الجمل المخالفة في الملفين**

```bash
ssh root@187.127.79.242 'cd /opt/nursery-facts && python3 -c "
import facts
for s in (\"child-independence-development\", \"child-care-hourly-jeddah\"):
    p = \"/var/www/montessori-ksa/blog/%s/index.html\" % s
    print(\"===\", s)
    for x in facts.check_html(open(p, encoding=\"utf-8\").read()):
        print(\"   -\", x)
"'
```

- [ ] **Step 3: طبّق نفس قائمة الاستبدال المعتمدة على الملفين**

```bash
ssh root@187.127.79.242 'python3 - <<PY
import re
exec(open("/root/repl_rules.py").read())
for s in ("child-independence-development", "child-care-hourly-jeddah"):
    p = "/var/www/montessori-ksa/blog/%s/index.html" % s
    t = open(p, encoding="utf-8").read()
    o = t
    for rx, to in REPL:
        t = re.sub(rx, to, t)
    if t != o:
        open(p, "w", encoding="utf-8").write(t)
    print(s, "changed" if t != o else "unchanged")
PY'
```

- [ ] **Step 4: تحقق وأصلح الملكية**

الناشر يعمل بمستخدم `www-data`، وتحرير الملف بمستخدم root يترك ملكية خاطئة.

```bash
ssh root@187.127.79.242 'chown www-data:www-data /var/www/montessori-ksa/blog/child-independence-development/index.html /var/www/montessori-ksa/blog/child-care-hourly-jeddah/index.html
cd /opt/nursery-facts && python3 -c "
import facts
for s in (\"child-independence-development\", \"child-care-hourly-jeddah\"):
    p = \"/var/www/montessori-ksa/blog/%s/index.html\" % s
    print(s, facts.check_html(open(p, encoding=\"utf-8\").read()) or \"CLEAN\")
"'
```

Expected: `CLEAN` للملفين.

---

### Task 7: إعادة صياغة مقال الفرق بين المراحل

**Files:**
- Modify: `/opt/seo/queue.json` — العنصر `pre-kg-vs-kg-difference`

**Interfaces:**
- Consumes: `facts.check_article` للتحقق.
- Produces: لا شيء لاحق يعتمد عليه.

المقال مبني كله على التسمية القديمة (التمهيدي 3–4 والروضة 4–5)، فلا يصلح فيه استبدال عبارة. البند الوحيد في هذه الخطة الذي يتطلب كتابة محتوى جديد.

- [ ] **Step 1: اقرأ المقال الحالي كاملاً**

```bash
ssh root@187.127.79.242 'python3 -c "
import json
q = json.load(open(\"/opt/seo/queue.json\"))
a = [x for x in q if x.get(\"slug\") == \"pre-kg-vs-kg-difference\"][0]
print(\"TITLE:\", a[\"title\"]); print(\"META:\", a[\"metaDescription\"])
print(a[\"bodyHtml\"])
print(\"FAQ:\", json.dumps(a.get(\"faq\"), ensure_ascii=False, indent=1))
"'
```

- [ ] **Step 2: اكتب المسودة الجديدة واعرضها على المالك**

المسودة تحفظ بنية المقال وطوله وكلمته المفتاحية، وتستبدل الإطار المفاهيمي فقط: الفرق بين **ما قبل الروضة** (سنتان–3) ومراحل الروضة الثلاث (المستوى الأول 3–4، المستوى الثاني 4–5، التمهيدي 5–6). **قف حتى يوافق المالك على النص.**

- [ ] **Step 3: اكتب المسودة المعتمدة في الطابور**

```bash
ssh root@187.127.79.242 'python3 - <<PY
import json
q = json.load(open("/opt/seo/queue.json"))
for a in q:
    if a.get("slug") == "pre-kg-vs-kg-difference":
        a["title"] = TITLE_APPROVED
        a["metaDescription"] = META_APPROVED
        a["bodyHtml"] = BODY_APPROVED
        a["faq"] = FAQ_APPROVED
json.dump(q, open("/opt/seo/queue.json", "w"), ensure_ascii=False, indent=1)
print("updated")
PY'
```

**ملاحظة للمنفّذ:** استبدل `TITLE_APPROVED` وأخواتها بالنص المعتمد فعلياً في الخطوة 2. لا تكتب أي نص لم يوافق عليه المالك.

- [ ] **Step 4: تحقق وأعد التوليد**

```bash
ssh root@187.127.79.242 'python3 - <<PY
import json, sys, datetime
sys.path.insert(0, "/opt/nursery-facts"); sys.path.insert(0, "/opt/seo")
import facts, publish
q = json.load(open("/opt/seo/queue.json"))
a = [x for x in q if x.get("slug") == "pre-kg-vs-kg-difference"][0]
print("gate:", facts.check_article(a) or "CLEAN")
PY'
ssh root@187.127.79.242 'cd /opt/seo && sudo -u www-data python3 -c "
import sys, json, datetime; sys.path.insert(0, \"/opt/seo\"); import publish
q = [publish.normalized_article(a) for a in json.loads(publish.QUEUE.read_text())]
publish.repair_published_articles(q, datetime.date.today()); print(\"repaired\")
"'
```

Expected: `gate: CLEAN` ثم `repaired`

---

### Task 8: التحقق النهائي وحارس الانحدار

**Files:**
- Create: `docs/superpowers/plans/2026-09-13-final-audit.txt`

**Interfaces:**
- Consumes: كل ما سبق.
- Produces: دليل موثَّق أن العدد وصل إلى صفر.

- [ ] **Step 1: تدقيق نهائي — المتوقع صفر**

```bash
ssh root@187.127.79.242 'cd /opt/seo && python3 publish.py --audit' | tee ~/Documents/Codex/montessori-website/docs/superpowers/plans/2026-09-13-final-audit.txt
```

Expected: `VIOLATING FILES: 0`

قارنه برقم خط الأساس من المهمة 2. إن لم يصل إلى صفر، البقية تُعالج قبل إغلاق العمل.

- [ ] **Step 2: حارس الانحدار — إعادة التوليد لا تغيّر المقالات السليمة**

```bash
ssh root@187.127.79.242 'cd /tmp && rm -rf blogsnap && cp -a /var/www/montessori-ksa/blog blogsnap
cd /opt/seo && sudo -u www-data python3 -c "
import sys, json, datetime; sys.path.insert(0, \"/opt/seo\"); import publish
q = [publish.normalized_article(a) for a in json.loads(publish.QUEUE.read_text())]
publish.repair_published_articles(q, datetime.date.today())
"
diff -rq /tmp/blogsnap /var/www/montessori-ksa/blog | head -20
echo "DIFFERING FILES: $(diff -rq /tmp/blogsnap /var/www/montessori-ksa/blog | wc -l)"'
```

Expected: `DIFFERING FILES: 0` — إعادة التوليد مرتين متتاليتين تعطي نفس الناتج بالحرف.

- [ ] **Step 3: تأكد أن التشغيل اليومي القادم سليم**

```bash
ssh root@187.127.79.242 'systemctl list-timers --all | grep -i seo; sudo -u www-data python3 -c "
import sys, json; sys.path.insert(0, \"/opt/nursery-facts\"); sys.path.insert(0, \"/opt/seo\")
import facts, publish
q = json.loads(publish.QUEUE.read_text())
pend = [a for a in q if not a.get(\"published\")]
print(\"pending:\", len(pend))
clean = [a for a in pend if not facts.check_article(a)]
print(\"would publish tomorrow:\", clean[0][\"slug\"] if clean else \"NOTHING — all blocked\")
"'
```

Expected: عدد المقالات المنتظرة، واسم المقال الذي سيُنشر غداً. إن كان `NOTHING` فالطابور كله راسب ويحتاج معالجة.

- [ ] **Step 4: حدّث ملف الذاكرة**

أضف إلى `/Users/mohamedmontaser/.claude/projects/-Users-mohamedmontaser/memory/accounts-excel-import.md` أو ملف ذاكرة جديد: أن الناشر صار له حاجز حقائق، وأن مصدر محتوى المقالات هو `queue.json` لا الـHTML، وأن سلّم المراحل المرجعي هو التسمية السعودية.

- [ ] **Step 5: كوميت نهائي**

```bash
cd ~/Documents/Codex/montessori-website
git add docs/superpowers/plans/2026-09-13-final-audit.txt
git commit -m "test(facts): final audit proves zero violating articles

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
```

---

## ما هو خارج نطاق هذه الخطة

- **28 مقالاً منشوراً خارج `queue.json`** لا يديرها أي نظام. اكتُشفت أثناء التصميم وتحتاج قراراً منفصلاً (المقالان في المهمة 6 منها، وعولجا لأنهما مخالفان).
- تنضيف سجلات الطلاب المكررة، وتقليم `legacy-desktop`، والصفحة الجديدة — بنود مستقلة في طلب المالك نفسه، لكلٍّ دورته.
