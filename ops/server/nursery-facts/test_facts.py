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
    ('سعر منسوب رغم عبارة عمومية داخل نفس الجملة',
     'رسومنا للمستوى الأول 1500 ريال شهرياً.'),
    ('عمومية في جملة والنسبة في جملة تانية لا تغسّل السعر',
     'أسعار الحضانات في جدة عموماً مرتفعة. رسومنا 1200 ريال.'),
    ('مدى بالكلمة بعمر خاطئ لما قبل الروضة',
     'ما قبل الروضة (سنتان–5) هي أول مرحلة عندنا.'),
    ('مدى بالكلمتين بعمر خاطئ للتمهيدي',
     'التمهيدي (ثلاث–أربع سنوات).'),
    ('سعر منسوب للمنشأة رغم ظرف "في السوق"',
     'سعر الروضة في السوق عموماً يبدأ من 1500 ريال شهرياً.'),
    ('سعر منسوب بصيغة "سعرنا" رغم ظرف "في السوق"',
     'سعرنا في السوق عموماً 1500 ريال.'),
    ('سعر منسوب بـ"عندنا" رغم ظرف "عموماً"',
     'الأسعار عموماً مرتفعة، والقيمة عندنا 1300 ريال.'),
    ('سعر منسوب بـ"تكلفتنا" رغم "في المتوسط"',
     'تكلفتنا 900 ريال في المتوسط.'),
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
    ('سعر سوق عام بلا نسبة إلينا',
     'تتراوح أسعار الحضانات في جدة عموماً بين 800 و1500 ريال شهرياً حسب المنطقة.'),
    ('متوسط أسعار الروضات كسوق لا كذاتنا',
     'متوسط أسعار الروضات في جدة قارب 1200 ريال هذا العام.'),
    ('مدى بالكلمة لما قبل الروضة',
     'ما قبل الروضة (سنتان–3) هي أول مرحلة عندنا.'),
    ('مدى بالكلمتين للمستوى الأول',
     'المستوى الأول (ثلاث–أربع سنوات).'),
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

    def test_sleep_hours_range_is_not_read_as_stage_age(self):
        reasons = facts.check_text('طفل التمهيدي ينام 10-13 ساعة يومياً.' + INTAKE)
        self.assertEqual([], reasons)

    def test_correct_stage_age_with_range_still_accepted(self):
        reasons = facts.check_text('التمهيدي (5–6 سنوات) مرحلة التهيئة.' + INTAKE)
        self.assertEqual([], reasons)


class TestNonAgeUnitDoesNotMaskWrongAge(unittest.TestCase):
    def test_wrong_stage_age_is_still_rejected(self):
        reasons = facts.check_text('التمهيدي (3–4 سنوات) مرحلة التهيئة.' + INTAKE)
        self.assertTrue(reasons)


class TestIntakeRangeRequired(unittest.TestCase):
    def test_missing_intake_range_is_rejected(self):
        reasons = ' '.join(facts.check_text('مرحبا بكم في روضتنا بجدة.'))
        self.assertIn('نطاق أعمارنا', reasons)


class TestExistingBansStillWork(unittest.TestCase):
    def test_nursery_word_as_a_stage_with_an_age_is_rejected(self):
        """«الحضانة (3-4)» مرحلة مخترعة: كانت تمرّ لأن القواعد تعرف
        «الروضة» فقط، فسلّم صفحة الأسعار الحيّة عدّى بلا اعتراض."""
        bad = 'نقدّم برامجنا: الحضانة (3-4 سنوات) ثم المستوى الثاني (4-5 سنوات)'
        self.assertTrue(facts._ours_only(facts.normalize(bad),
                                         facts._check_orphan_stage_ages))

    def test_nursery_word_without_an_age_still_passes(self):
        """اسم النشاط نفسه مسموح — الاقتران بعمر هو المخالفة."""
        good = ('حضانتنا في حي الفيصلية بجدة نستقبل الأطفال من سنتين إلى ٥ سنوات '
                'عبر المستوى الأول (3-4 سنوات) والتمهيدي (5-6 سنوات).')
        self.assertEqual(facts._ours_only(facts.normalize(good),
                                          facts._check_orphan_stage_ages), [])

    def test_market_nursery_prices_keep_their_common_wording(self):
        """وصف السوق يحتفظ بتسميته (قرار المالك) فلا يُرفض."""
        market = 'أسعار الحضانات في جدة عموماً بين 800 و1500 ريال شهرياً.'
        self.assertEqual(facts._ours_only(facts.normalize(market),
                                          facts._check_orphan_stage_ages), [])

    def test_invented_price_rejected(self):
        reasons = facts.check_text('رسومنا تبدأ من 1500 ريال شهرياً.' + INTAKE)
        self.assertTrue(reasons)

    def test_review_count_in_digits_glued_to_arabic_rejected(self):
        # «71 تقييماً» أفلت من الحاجز لأن \\b لا يقع بعد حرف عربي
        self.assertTrue(facts.check_text('من 71 تقييماً على خرائط جوجل.' + INTAKE))

    def test_review_count_written_in_words_rejected(self):
        # «واحدٍ وسبعين مراجعة» أفلت لأن القاعدة كانت تطلب رقماً، والتنوين ليس \\w
        self.assertTrue(facts.check_text('من واحدٍ وسبعين مراجعة على جوجل.' + INTAKE))

    def test_rating_without_a_count_is_accepted(self):
        self.assertEqual([], facts.check_text('بتقييم 4.7★ على خرائط جوجل.' + INTAKE))

    def test_review_count_rejected(self):
        reasons = facts.check_text('لدينا 70 مراجعة على خرائط جوجل.' + INTAKE)
        self.assertTrue(reasons)

    def test_infant_claim_rejected(self):
        reasons = facts.check_text('نستقبل الرضّع من عمر سنة.' + INTAKE)
        self.assertTrue(reasons)


class TestHtmlAndArticleWrappers(unittest.TestCase):
    def test_check_article_strips_tags_before_matching(self):
        """أرقام أسماء الوسوم ليست أرقام محتوى: «رسوم حضانتنا …</h2>»
        كانت تُقرأ سعراً مخترعاً لأن «2» في اسم الوسم أشبعت القاعدة."""
        art = {'title': 'رسوم الحضانة', 'seoTitle': 'رسوم الحضانة',
               'metaDescription': 'نستقبل من سنتين إلى ٥ سنوات.',
               'bodyHtml': '<h2>رسوم حضانتنا في حي الفيصلية</h2>'
                           '<p>نستقبل الأطفال من سنتين إلى ٥ سنوات، '
                           'والرسوم تُحدَّد بمكالمة أو زيارة.</p>',
               'faq': []}
        self.assertEqual([x for x in facts.check_article(art) if 'سعر' in x], [])

    def test_closing_hour_written_without_minutes_is_rejected(self):
        """«8 صباحاً - 2 ظهراً» فاتت القاعدة: كانت تعرف «الثانية ظهر»
        و«2:00 ظهر» فقط. الدوام ينتهي الواحدة ظهراً."""
        self.assertTrue([x for x in facts.check_text(
            'دوامنا من الأحد إلى الخميس، 8 صباحاً - 2 ظهراً، '
            'ونستقبل من سنتين إلى ٥ سنوات.') if 'دوام' in x])

    def test_correct_closing_hour_passes(self):
        self.assertEqual([x for x in facts.check_text(
            'دوامنا من الثامنة صباحاً حتى الواحدة ظهراً، '
            'ونستقبل من سنتين إلى ٥ سنوات.') if 'دوام' in x], [])

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
