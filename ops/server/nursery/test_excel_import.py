# -*- coding: utf-8 -*-
"""اختبارات قارئ Excel الشهري — تشتغل بدون Odoo.

تشغيل:  python3 ops/server/nursery/test_excel_import.py

الشيت المصطنع هنا بنفس تخطيط ملف الحسابات الحقيقي (طلاب بأرقام تسلسلية
كمعادلات، جدول رواتب وجدول مصروفات جنب بعض، صف ملخص فوق) ومن غير أي
بيانات حقيقية.
"""
import base64
import importlib.util
import io
import os
import sys
import types
import unittest

from openpyxl import Workbook

HERE = os.path.dirname(os.path.abspath(__file__))


def _load_module():
    """Import excel_import.py with the Odoo imports stubbed out."""
    odoo = types.ModuleType('odoo')
    odoo_http = types.ModuleType('odoo.http')
    odoo_http.request = None
    odoo_http.Controller = object
    odoo_http.route = lambda *args, **kwargs: (lambda func: func)
    odoo.http = odoo_http
    odoo.fields = types.SimpleNamespace()
    sys.modules.setdefault('odoo', odoo)
    sys.modules.setdefault('odoo.http', odoo_http)
    package = types.ModuleType('nursery_test_pkg')
    package.__path__ = []
    roles = types.ModuleType('nursery_test_pkg.roles')
    roles.WEBSITE = ''
    roles._manager_by_token = lambda *args, **kwargs: None
    sys.modules['nursery_test_pkg'] = package
    sys.modules['nursery_test_pkg.roles'] = roles
    spec = importlib.util.spec_from_file_location(
        'nursery_test_pkg.excel_import', os.path.join(HERE, 'excel_import.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


excel_import = _load_module()

STUDENT_HEADERS = ['Class', 'Serial', 'Student', 'Joining Date', 'Agreed Monthly Fees',
                   'Last Payment Amount', 'Payment Date', 'Paid Until Date', 'Books',
                   'Fees paid', 'Remaining', 'Payment status', 'Payment Method',
                   'ملاحظات', 'مرتبط بولي الأمر', 'اسم ولي الأمر', 'هاتف ولي الأمر', 'ID']


def _workbook():
    """Two classes, one mid-month leaver, salaries + expenses side by side."""
    book = Workbook()
    sheet = book.active
    sheet.title = 'September 2026'
    sheet['A1'] = 'Accounting Summary'
    for column, label in zip('ACEGIKMOQS', [
            'Total Received', 'Randa Cash', 'Bank Transfer', 'Expenses', 'On hand Randa',
            'Salaries', 'Students\nعدد الطلاب', 'Books Fees\nرسوم الكتب',
            'Remaining\nالباقي', 'Net']):
        sheet['%s2' % column] = label
    sheet.append([])
    sheet.append([])
    sheet.append(STUDENT_HEADERS)
    rows = [
        # class, name, joined, fees, paid, paid_until, books, fees_paid, method, id, serial?
        ('KG1', 'Alpha', '2026-09-01', 1000, 8000, '2027-05-30', 1000, 7000, 'Randa Cash', 11, True),
        ('KG1', 'Beta', '2026-09-01', 1200, 2300, '2026-10-01', 1000, 1300, 'Randa Cash', 12, True),
        ('KG1', 'Gone', '2026-09-01', 1300, 1300, '2026-10-01', 500, 1800, 'Randa Cash', 13, False),
        ('KG1', 'Gamma', '2026-09-27', 1300, None, None, None, None, None, 14, True),
        ('KG2', 'Delta', '2026-09-01', 1000, 10500, '2027-05-30', 500, 10000, 'Bank Transfer', 21, True),
        ('KG2', 'Epsilon', '2026-09-01', 1100, 600, '2026-10-01', None, 600, 'Randa Cash', 22, True),
    ]
    class_start = {}
    for cls, name, joined, fees, paid, until, books, fees_paid, method, db_id, numbered in rows:
        row_number = sheet.max_row + 1
        start = class_start.setdefault(cls, row_number)
        serial = ('=IF(C{r}="","",COUNT(B${s}:B{p})+1)'.format(r=row_number, s=start, p=row_number - 1)
                  if row_number > start else '=IF(C{r}="","",1)'.format(r=row_number))
        sheet.append([
            cls if row_number == start else None,
            serial if numbered else None,
            name, joined, fees, paid, joined if paid else None, until, books, fees_paid,
            '=IF(OR(C{r}="",E{r}=""),"",MAX(0,E{r}-J{r}))'.format(r=row_number),
            'paid' if paid else None, method, None, 'لا', None, None, db_id,
        ])
    # one blank template row with formulas only, then the class counter rows
    row_number = sheet.max_row + 1
    sheet.append([None, '=IF(C{r}="","",COUNT(B$10:B{p})+1)'.format(r=row_number, p=row_number - 1),
                  None, None, None, None, None, None, None, None,
                  '=IF(OR(C{r}="",E{r}=""),"",MAX(0,E{r}-J{r}))'.format(r=row_number)])
    last_student = sheet.max_row
    sheet.append([None, None, 'Students KG2', '=COUNT(B10:B%d)' % last_student])
    kg2_count_row = sheet.max_row
    sheet.append([None, None, 'Students KG1', '=COUNT(B6:B9)'])
    kg1_count_row = sheet.max_row
    sheet.append([])

    sheet.append(['Salaries\nالرواتب', None, None, None, None, None, 'Expenses Paid by Randa'])
    sheet.append(['Teacher Name\nاسم المعلم', 'Date\nالتاريخ', 'Forecast Salary', 'Actual Salary',
                  'Notes', None, 'Serial', 'Expense Name', 'Expense Date', 'Value'])
    first_entry = sheet.max_row + 1
    entries = [
        (('Dalia', None, 4000, 4000, None), ('نسرين', '2026-08-28', 10360)),
        (('Randa', None, 3500, 2500, 'كتب'), ('قرطاسيه', '2026-08-29', -475)),
        (('Huda', None, 2200, 2200, None), ('مرتبات', None, -8700)),
        ((None, None, None, None, None), ('ايجار', '2026-09-10', -20000)),
    ]
    for salary, expense in entries:
        row_number = sheet.max_row + 1
        serial = ('=IF(H{r}="","",1)'.format(r=row_number) if row_number == first_entry
                  else '=IF(H{r}="","",COUNT(G${s}:G{p})+1)'.format(r=row_number, s=first_entry,
                                                                   p=row_number - 1))
        sheet.append(list(salary) + [None, serial] + list(expense))
    last_entry = sheet.max_row
    sheet.append(['Total Salaries\nإجمالي الرواتب', None,
                  '=SUM(C%d:C%d)' % (first_entry, last_entry),
                  '=SUM(D%d:D%d)' % (first_entry, last_entry), None, None, None,
                  'Total Expenses', None, '=SUM(J%d:J%d)' % (first_entry, last_entry)])
    total_row = sheet.max_row

    sheet['A3'] = '=SUM(F6:F%d)' % last_student
    sheet['C3'] = '=SUMIF(M6:M%d,"Randa Cash",F6:F%d)' % (last_student, last_student)
    sheet['G3'] = '=-J%d' % total_row
    sheet['I3'] = '=C3-G3'
    sheet['K3'] = '=D%d' % total_row
    sheet['M3'] = '=D%d+D%d' % (kg1_count_row, kg2_count_row)
    sheet['O3'] = '=SUM(I6:I%d)' % last_student
    sheet['Q3'] = '=SUM(K6:K%d)' % last_student
    sheet['S3'] = '=A3-G3'
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


class ExcelImportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = _workbook()
        cls.parsed = excel_import._parse_records(
            [{'name': 'sep.xlsx', 'content': base64.b64encode(raw).decode('ascii')}],
            '2026-09')
        cls.metrics = excel_import._excel_month_metrics(cls.parsed, '2026-09')

    def test_workbook_months_prefers_newest_finished_tab(self):
        files = [{'name': 'sep.xlsx', 'content': base64.b64encode(_workbook()).decode('ascii')}]
        self.assertEqual(excel_import._workbook_months(files, '2026-10'), ['2026-09'])
        self.assertEqual(excel_import._workbook_months(files, '2026-09'), ['2026-09'])
        # a tab for a month that has not started yet is never picked
        self.assertEqual(excel_import._workbook_months(files, '2026-08'), [])

    def test_import_unlock_window(self):
        import datetime
        original = excel_import.UNLOCK_FILE
        excel_import.UNLOCK_FILE = os.path.join(HERE, 'import_unlock.json')
        try:
            self.assertTrue(excel_import._import_unlocked('2026-09', datetime.date(2026, 10, 10)))
            self.assertFalse(excel_import._import_unlocked('2026-09', datetime.date(2026, 10, 11)))
            self.assertFalse(excel_import._import_unlocked('2026-10', datetime.date(2026, 10, 2)))
        finally:
            excel_import.UNLOCK_FILE = original
        excel_import.UNLOCK_FILE = os.path.join(HERE, 'does-not-exist.json')
        try:
            self.assertFalse(excel_import._import_unlocked('2026-09', datetime.date(2026, 10, 2)))
        finally:
            excel_import.UNLOCK_FILE = original

    def test_formula_serials_are_resolved(self):
        """openpyxl saves formulas without cached values; serials still count."""
        by_name = {row['name']: row for row in self.parsed['students']}
        self.assertEqual([by_name[n]['serial'] for n in ('Alpha', 'Beta', 'Gamma')], [1, 2, 3])
        self.assertEqual([by_name[n]['serial'] for n in ('Delta', 'Epsilon')], [1, 2])
        self.assertIsNone(by_name['Gone']['serial'])
        self.assertFalse(by_name['Gone']['active'])
        self.assertEqual(self.metrics['student_count'], 5)

    def test_remaining_formula_treats_blank_paid_as_zero(self):
        by_name = {row['name']: row for row in self.parsed['students']}
        self.assertEqual(by_name['Gamma']['remaining'], 1300)
        self.assertEqual(by_name['Epsilon']['remaining'], 500)
        self.assertEqual(by_name['Alpha']['remaining'], 0)
        self.assertEqual(self.metrics['remaining_total'], 1800)

    def test_staff_rows_are_not_students(self):
        names = {row['name'] for row in self.parsed['students']}
        self.assertNotIn('Dalia', names)
        self.assertEqual(len(self.parsed['students']), 6)

    def test_salary_and_expense_tables_are_split(self):
        salaries = [row for row in self.parsed['entries'] if row['kind'] == 'salary']
        expenses = [row for row in self.parsed['entries'] if row['kind'] == 'expense']
        self.assertEqual([(r['name'], r['amount'], r['expected']) for r in salaries],
                         [('Dalia', 4000, 4000), ('Randa', 2500, 3500), ('Huda', 2200, 2200)])
        self.assertEqual([(r['name'], r['amount']) for r in expenses],
                         [('نسرين', 10360), ('قرطاسيه', -475), ('مرتبات', -8700), ('ايجار', -20000)])
        self.assertEqual(expenses[0]['date'], '2026-08-28')

    def test_metrics_match_the_workbook_arithmetic(self):
        m = self.metrics
        self.assertEqual(m['collected'], 22700)
        self.assertEqual(m['randa_cash'], 12200)
        self.assertEqual(m['bank_transfer'], 10500)
        self.assertEqual(m['salaries'], 8700)
        self.assertEqual(m['expected_salaries'], 9700)
        self.assertEqual(m['expenses'], 18815)           # -(10360 - 475 - 8700 - 20000)
        self.assertEqual(m['opening_balance'], 10360)
        self.assertEqual(m['salary_payout'], 8700)
        self.assertEqual(m['other_expenses'], 20475)     # 475 + 20000
        self.assertEqual(m['on_hand_randa'], 12200 + 10360 - 29175)
        self.assertEqual(m['net'], 22700 - 18815)
        # dashboard identity: income - salaries - other == workbook net
        self.assertEqual((m['collected'] + m['opening_balance']) - m['salaries'] - m['other_expenses'],
                         m['net'])
        self.assertEqual(m['books'], 3000)


if __name__ == '__main__':
    unittest.main()
