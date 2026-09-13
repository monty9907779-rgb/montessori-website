# -*- coding: utf-8 -*-
"""استيراد Excel شهري آمن مع معاينة قبل الكتابة."""
import base64
import csv
import io
import json
import os
import re
from calendar import monthrange
from copy import copy
from datetime import date, datetime

import pytz
from openpyxl import Workbook, load_workbook

from odoo import fields, http
from odoo.http import request

from .roles import WEBSITE, _manager_by_token


MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_TOTAL_BYTES = 24 * 1024 * 1024


SHEET_URL_PARAM = 'nursery.excel_sheet_url'
SHEET_EXPORT = 'https://docs.google.com/spreadsheets/d/%s/export?format=xlsx'
_SHEET_ID_RE = re.compile(r'/spreadsheets/d/(?:e/)?([A-Za-z0-9_-]{20,})')


def _sheet_id(url):
    """يستخرج معرّف الشيت من أي صيغة رابط جوجل."""
    raw = str(url or '').strip()
    if not raw:
        return ''
    match = _SHEET_ID_RE.search(raw)
    if match:
        return match.group(1)
    # لو المديرة لصقت المعرّف وحده
    if re.match(r'^[A-Za-z0-9_-]{20,}$', raw):
        return raw
    return ''


def _download_sheet(sheet_id):
    """ينزّل الشيت كـ xlsx. يرجّع (bytes, error_message)."""
    import requests
    response = requests.get(SHEET_EXPORT % sheet_id, timeout=60,
                            allow_redirects=True, stream=True)
    ctype = (response.headers.get('Content-Type') or '').lower()
    # جوجل بيحوّل الطلب غير المصرّح له لصفحة دخول HTML بكود 200،
    # فالكود لوحده مش دليل نجاح — لازم نتأكد من نوع المحتوى.
    if response.status_code in (401, 403) or 'html' in ctype:
        return None, ('الشيت مش متاح للقراءة بالرابط. من جوجل شيت: '
                      'مشاركة ← أي شخص لديه الرابط ← مُشاهد.')
    if response.status_code == 404:
        return None, 'الشيت غير موجود على هذا الرابط.'
    if response.status_code != 200:
        return None, 'تعذّر تنزيل الشيت من جوجل (كود %s).' % response.status_code
    content = b''
    for chunk in response.iter_content(65536):
        content += chunk
        if len(content) > MAX_FILE_BYTES:
            return None, 'الشيت أكبر من 12 ميجابايت.'
    if not content:
        return None, 'الشيت رجع فاضياً.'
    if not content.startswith(b'PK'):
        return None, 'الملف النازل من جوجل ليس ملف Excel صالحاً.'
    return content, None


MONTHS = {
    1: ('يناير', 'january', 'jan'),
    2: ('فبراير', 'february', 'feb'),
    3: ('مارس', 'march', 'mar'),
    4: ('أبريل', 'april', 'apr'),
    5: ('مايو', 'may'),
    6: ('يونيو', 'june', 'jun'),
    7: ('يوليو', 'july', 'jul'),
    8: ('أغسطس', 'august', 'aug'),
    9: ('سبتمبر', 'september', 'sep'),
    10: ('أكتوبر', 'october', 'oct'),
    11: ('نوفمبر', 'november', 'nov'),
    12: ('ديسمبر', 'december', 'dec'),
}

ALIASES = {
    'name': ('student name', 'student', 'name', 'اسم الطالب', 'الاسم', 'اسم الطفل',
             'اسم المصروف', 'expense', 'expense name', 'البيان', 'teacher name'),
    'serial': ('serial', 'no', 'number', 'الرقم', 'رقم', 'رقم الطالب'),
    'db_id': ('id', 'student id', 'studentid', 'معرف الطالب', 'كود الطالب'),
    'class_name': ('class', 'class name', 'الفصل', 'الصف', 'المستوى'),
    'joining_date': ('joining date', 'join date', 'تاريخ الالتحاق', 'تاريخ الانضمام'),
    'fees': ('agreed monthly fees', 'monthly fees', 'fees', 'monthly fee',
             'الرسوم الشهرية', 'الاشتراك الشهري', 'قيمة الاشتراك'),
    'paid': ('last payment amount', 'last payment', 'fees paid', 'paid', 'amount paid',
             'المبلغ المدفوع', 'آخر دفعة', 'المدفوع'),
    'paid_date': ('payment date', 'paid date', 'تاريخ الدفع', 'تاريخ آخر دفعة'),
    'paid_until': ('paid until date', 'paid until', 'مدفوع حتى', 'مدفوع حتى تاريخ'),
    'books': ('books', 'book fees', 'books fees', 'الكتب', 'رسوم الكتب'),
    'book_paid': ('books paid', 'book paid', 'paid books', 'رسوم الكتب المحصلة',
                  'الكتب المحصلة', 'المدفوع للكتب'),
    'book_remaining': ('books remaining', 'book remaining', 'remaining books',
                       'باقي رسوم الكتب', 'باقي الكتب', 'المتبقي من الكتب'),
    'remaining': ('remaining', 'balance', 'المتبقي', 'الباقي', 'الرصيد المتبقي'),
    'method': ('payment method', 'method', 'طريقة الدفع', 'طريقة السداد'),
    'guardian_name': ('guardian name', 'parent name', 'اسم ولي الأمر'),
    'guardian_phone': ('guardian phone', 'parent phone', 'phone', 'هاتف ولي الأمر',
                       'تليفون ولي الأمر'),
    'note': ('note', 'notes', 'remark', 'remarks', 'ملاحظات', 'ملاحظة'),
    'amount': ('amount', 'value', 'expense amount', 'المبلغ', 'القيمة', 'التكلفة'),
    'date': ('date', 'expense date', 'التاريخ', 'تاريخ المصروف'),
    'teacher': ('teacher name', 'teacher', 'employee', 'اسم المعلمة', 'المعلمة',
                'اسم الموظف'),
}


def _norm(value):
    value = '' if value is None else str(value)
    value = value.strip().lower()
    value = value.translate(str.maketrans({
        'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ة': 'ه',
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
    }))
    value = re.sub(r'[\u200f\u200e]', '', value)
    value = re.sub(r'[^0-9a-z\u0600-\u06ff]+', ' ', value)
    return re.sub(r'\s+', ' ', value).strip()


def _student_name_key(value):
    raw = '' if value is None else str(value).strip().lower()
    raw = re.split(r'[/\\]', raw, 1)[0]
    key = _norm(raw)
    key = re.sub(r'\b(?:kg\s*\d|pre\s*kg|pre|summer)\b$', '', key).strip()
    parts = []
    aliases = {
        'ahmad': 'ahmed', 'sheehab': 'shehab',
        'mohamad': 'mohamed', 'mohammad': 'mohamed', 'mohammed': 'mohamed',
        'mousa': 'musa',
        'yones': 'younis', 'younes': 'younis', 'yunis': 'younis',
        'yousef': 'youssef',
        'hamzah': 'hamza',
        'marya': 'maria',
        'lulia': 'lolia',
        'dialaa': 'dyala', 'diala': 'dyala',
    }
    for part in key.split():
        if re.search(r'\d', part):
            continue
        parts.append(aliases.get(part, part))
    return ' '.join(parts)


def _student_excel_name_key(value):
    """Normalize an Excel name without applying site-name aliases."""
    raw = '' if value is None else str(value).strip().lower()
    raw = re.split(r'[/\\]', raw, 1)[0]
    key = _norm(raw)
    return re.sub(r'\b(?:kg\s*\d|pre\s*kg|pre|summer)\b$', '', key).strip()


def _student_level_key(value):
    key = _norm(value)
    if 'summer' in key:
        return 'summer'
    if 'pre' in key:
        return 'prekg'
    match = re.search(r'\bkg\s*([123])\b', key)
    return 'kg%s' % match.group(1) if match else ''


def _student_record_level(record):
    return _student_level_key(record.get('class_name') or record.get('name'))


def _student_model_level(student):
    return (_student_level_key(student.class_id.name if student.class_id else '')
            or _student_level_key(student.name))


def _clean(value, limit=200):
    if value is None:
        return ''
    return str(value).replace('<', '').replace('>', '').strip()[:limit]


def _number(value):
    if value is None or value is False or value == '':
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value).strip().replace(',', '').replace('٬', '').replace('٫', '.')
    raw = raw.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
    raw = re.sub(r'[^\d.\-]', '', raw)
    if not raw or raw in ('-', '.', '-.'):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _date_string(value):
    if value is None or value is False or value == '':
        return ''
    if isinstance(value, datetime):
        return value.date().strftime('%Y-%m-%d')
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    raw = str(value).strip()
    raw = raw.translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
    for fmt in ('%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y',
                '%m/%d/%Y', '%d.%m.%Y'):
        try:
            return datetime.strptime(raw[:10], fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return raw[:10] if re.match(r'^\d{4}-\d{2}-\d{2}$', raw[:10]) else ''


def _entry_date_string(value, target_ym):
    """Expense/salary dates relative to the imported month.

    The workbook types short dates like ``28/8`` (text, no year) and ``1/9``
    (which Excel stores as January 9 under a month/day locale). Both belong
    to the imported month or the month right before it, so a date outside
    that window whose day/month can be swapped into the window is repaired.
    """
    if value in (None, False, ''):
        return ''
    try:
        year, month = int(str(target_ym)[:4]), int(str(target_ym)[5:7])
    except (TypeError, ValueError):
        return _date_string(value)
    previous = (year, month - 1) if month > 1 else (year - 1, 12)

    def in_window(item):
        return (item.year, item.month) in ((year, month), previous)

    parsed = None
    if isinstance(value, datetime):
        parsed = value.date()
    elif isinstance(value, date):
        parsed = value
    else:
        raw = str(value).strip().translate(str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789'))
        short = re.match(r'^(\d{1,2})\s*[/.\-]\s*(\d{1,2})$', raw)
        if not short:
            return _date_string(value)
        first, second = int(short.group(1)), int(short.group(2))
        for day, mon in ((first, second), (second, first)):
            try:
                candidate = date(year, mon, day)
            except ValueError:
                continue
            if in_window(candidate):
                return candidate.strftime('%Y-%m-%d')
        try:
            return date(year, second, first).strftime('%Y-%m-%d')
        except ValueError:
            return ''
    if not in_window(parsed) and parsed.day <= 12:
        try:
            swapped = date(parsed.year, parsed.day, parsed.month)
        except ValueError:
            swapped = None
        if swapped and in_window(swapped):
            parsed = swapped
    return parsed.strftime('%Y-%m-%d')


def _summary_values(rows):
    """Read labeled summary cells without inventing a value from other rows."""
    result = {}
    labels = {
        'total received': 'collected', 'randa cash': 'randa_cash',
        'expenses': 'expenses', 'bank transfer': 'bank_transfer',
        'salaries': 'salaries', 'students عدد الطلاب': 'student_count',
        'books fees رسوم الكتب': 'books', 'remaining الباقي': 'remaining_total',
        'net': 'net', 'expected salaries': 'expected_salaries',
        'on hand randa': 'on_hand_randa', 'delta': 'delta',
    }
    for row_index, row in enumerate(rows or []):
        for column, cell in enumerate(row or []):
            label = _norm(cell)
            key = labels.get(label)
            if not key or row_index + 1 >= len(rows):
                continue
            value = rows[row_index + 1][column] if column < len(rows[row_index + 1]) else None
            if key == 'on_hand_randa':
                key = 'on_hand_randa' if row_index < 10 else 'audit_on_hand_randa'
            result[key] = _number(value)
    return result


def _ym_from_text(value, default_year):
    raw = _norm(value)
    year_match = re.search(r'(20\d{2})', raw)
    year = int(year_match.group(1)) if year_match else int(default_year)
    for month_number, names in MONTHS.items():
        if any(_norm(name) in raw for name in names):
            return '%04d-%02d' % (year, month_number)
    return ''


SEASON_MIN_YM = '2026-09'
SEASON_MAX_YM = '2027-05'


def _valid_ym(value):
    """Return a YYYY-MM string only when it names a month of this season.

    Anything else returns False so the caller can reject the request instead
    of silently importing into the current month.
    """
    text = str(value or '').strip()
    if not re.match(r'^[0-9]{4}-[0-9]{2}$', text):
        return False
    if not ('01' <= text[5:7] <= '12'):
        return False
    if not (SEASON_MIN_YM <= text <= SEASON_MAX_YM):
        return False
    return text


def _month_label(ym):
    try:
        year, month = ym.split('-')
        return '%s %s' % (MONTHS[int(month)][0], year)
    except (AttributeError, IndexError, ValueError):
        return ym


def _model_fields(model):
    return getattr(model, '_fields', {})


def _col(headers, key, exact=False):
    aliases = {_norm(item) for item in ALIASES.get(key, ())}
    for index, header in enumerate(headers):
        if _norm(header) in aliases:
            return index
    if exact:
        return None
    for index, header in enumerate(headers):
        normalized = _norm(header)
        if normalized and any(alias and (
                alias in normalized
                or (normalized in alias and len(normalized) >= max(4, len(alias) - 2)))
                for alias in aliases):
            return index
    return None


def _header_col(headers, aliases):
    normalized_aliases = {_norm(alias) for alias in aliases}
    for index, header in enumerate(headers):
        if _norm(header) in normalized_aliases:
            return index
    for index, header in enumerate(headers):
        normalized = _norm(header)
        if not normalized:
            continue
        if any(len(alias) >= 4 and len(normalized) >= 4 and (
               alias in normalized
               or (normalized in alias and len(normalized) >= max(4, len(alias) - 2)))
               for alias in normalized_aliases):
            return index
    return None


def _header_kind(headers):
    student_name_col = _header_col(headers, (
        'student name', 'student', 'name', 'اسم الطالب', 'الاسم', 'اسم الطفل'))
    amount_col = _header_col(headers, ALIASES['amount'])
    date_col = _header_col(headers, ALIASES['date'])
    if (_header_col(headers, ALIASES['teacher']) is not None
            and amount_col is not None and date_col is not None):
        return 'salary'
    exact_entry_names = {_norm(value) for value in (
        'expense name', 'اسم المصروف', 'البيان', 'name')}
    entry_name_col = next((index for index, header in enumerate(headers)
                           if _norm(header) in exact_entry_names), None)
    if entry_name_col is not None and amount_col is not None and date_col is not None:
        return 'expense'
    student_hint = any(_header_col(headers, ALIASES[key]) is not None
                       for key in ('serial', 'db_id', 'class_name'))
    if student_name_col is not None and student_hint:
        return 'student'
    return ''


def _header_rows(rows):
    found = []
    for index, row in enumerate(rows):
        headers = list(row or [])
        # Data rows can contain literal cells named "Expense Name" or "Value"
        # in a side table. A real header row in the supported workbooks is text-only.
        if any(value is not None and value != '' and not isinstance(value, str)
               for value in headers):
            continue
        kind = _header_kind(headers)
        if kind:
            found.append((index, kind, headers))
    return found


def _header_index(headers, aliases, start=0):
    """Return one header position without letting a neighbouring table win."""
    aliases = {_norm(item) for item in aliases}
    for index in range(start, len(headers)):
        if _norm(headers[index]) in aliases:
            return index
    for index in range(start, len(headers)):
        normalized = _norm(headers[index])
        if normalized and any(len(alias) >= 4 and len(normalized) >= 4
                              and (alias in normalized
                                   or (normalized in alias
                                       and len(normalized) >= max(4, len(alias) - 2)))
                              for alias in aliases):
            return index
    return None


def _table_specs(headers):
    """Find the student table and any side-by-side expense/salary table."""
    specs = []
    main_kind = _header_kind(headers)
    student_name_index = _header_index(
        headers, ('student name', 'student', 'name', 'اسم الطالب', 'الاسم', 'اسم الطفل'))
    student_hint = any(_header_index(headers, ALIASES[key]) is not None
                       for key in ('serial', 'db_id', 'class_name'))
    if main_kind == 'student' or (student_name_index is not None and student_hint):
        specs.append({'kind': 'student', 'headers': headers})

    amount_aliases = ALIASES['amount']
    date_aliases = ALIASES['date']
    teacher_index = _header_index(headers, ALIASES['teacher'])
    expense_index = _header_index(headers, ('expense name', 'اسم المصروف', 'البيان'))
    generic_name_index = _header_index(headers, ('name', 'الاسم'))

    if teacher_index is not None:
        name_index, kind = teacher_index, 'salary'
    elif expense_index is not None:
        name_index, kind = expense_index, 'expense'
    elif main_kind != 'student' and generic_name_index is not None:
        name_index, kind = generic_name_index, 'expense'
    else:
        name_index, kind = None, ''

    if name_index is not None:
        amount_index = _header_index(headers, amount_aliases, start=name_index + 1)
        date_index = _header_index(headers, date_aliases, start=name_index + 1)
        if amount_index is not None and date_index is not None:
            note_index = _header_index(headers, ALIASES['note'], start=name_index + 1)
            indexes = [name_index, amount_index, date_index]
            table_headers = [headers[index] for index in indexes]
            if note_index is not None and note_index not in indexes:
                indexes.append(note_index)
                table_headers.append(headers[note_index])
            specs.append({'kind': kind, 'headers': table_headers, 'indexes': indexes})
    return specs


def _embedded_table_specs(rows, header_index, next_index):
    """Find entry tables whose header starts inside a student data row."""
    specs = []
    scan_end = min(next_index, header_index + 7)
    for row_index in range(header_index + 1, scan_end):
        row = list(rows[row_index] or [])
        row_specs = []
        for start in range(len(row)):
            if not isinstance(row[start], str) or not _norm(row[start]):
                continue
            max_end = min(len(row), start + 10)
            for end in range(start + 3, max_end + 1):
                segment = row[start:end]
                if any(value not in (None, '') and not isinstance(value, str)
                       for value in segment):
                    continue
                kind = _header_kind(segment)
                if kind not in ('expense', 'salary'):
                    continue
                indexes = list(range(start, end))
                if any(existing['kind'] == kind
                       and set(existing['indexes']).intersection(indexes)
                       for existing in row_specs):
                    break
                row_specs.append({
                    'kind': kind,
                    'headers': segment,
                    'indexes': indexes,
                    'data_start': row_index + 1,
                })
                break
        specs.extend(row_specs)
    return specs


def _project_row(row, indexes):
    return [row[index] if index < len(row) else None for index in indexes]


def _read_xlsx(raw):
    from openpyxl import load_workbook
    workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    out = []
    for sheet in workbook.worksheets:
        rows = []
        for row in sheet.iter_rows(values_only=True):
            rows.append(list(row[:80]))
            if len(rows) >= 2500:
                break
        out.append((sheet.title, rows))
    return out


def _read_xls(raw):
    import xlrd
    workbook = xlrd.open_workbook(file_contents=raw)
    return [(sheet.name, [list(sheet.row_values(i)[:80])
                          for i in range(min(sheet.nrows, 2500))])
            for sheet in workbook.sheets()]


def _read_csv(raw):
    text = None
    for encoding in ('utf-8-sig', 'utf-8', 'cp1256'):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        text = raw.decode('utf-8', errors='replace')
    return [('CSV', [row for row in csv.reader(io.StringIO(text))])]


def _read_file(filename, raw):
    lower = filename.lower()
    if lower.endswith('.csv'):
        return _read_csv(raw)
    if lower.endswith('.xls') and not lower.endswith('.xlsx'):
        return _read_xls(raw)
    return _read_xlsx(raw)


def _student_record(headers, row, source, is_master, target_ym=None):
    name_index = _col(headers, 'name')
    raw_name = row[name_index] if name_index is not None and name_index < len(row) else ''
    if isinstance(raw_name, (int, float)):
        return None
    name = _clean(raw_name)
    normalized_name = _norm(name)
    if (not name or normalized_name in {'student', 'student name', 'اسم الطالب', 'الاسم',
                                        'number', 'رقم'}
            or any(value in normalized_name for value in
                   ('amount', 'المبلغ', 'total', 'اجمالي', 'إجمالي'))):
        return None
    def val(key, exact=False):
        index = _col(headers, key, exact=exact)
        return row[index] if index is not None and index < len(row) else None
    source_columns = {
        key for key in ('serial', 'class_name', 'joining_date', 'fees', 'paid',
                        'paid_date', 'paid_until', 'books', 'book_paid',
                        'book_remaining', 'remaining', 'method', 'guardian_name',
                        'guardian_phone', 'note')
        if _col(headers, key) is not None
    }
    paid_cell = None if is_master else val('paid')
    record = {
        'kind': 'student', 'name': name, 'source': source,
        'db_id': _number(val('db_id', exact=True)),
        'serial': _number(val('serial', exact=True)),
        # Excel's student count is based on numbered rows. Rows without a
        # serial can still carry a payment, so keep them in the month ledger
        # but do not make them active roster students.
        'active': _number(val('serial', exact=True)) is not None,
        'class_name': _clean(val('class_name'), 80),
        'joining_date': _date_string(val('joining_date')),
        'fees': _number(val('fees')),
        'paid': _number(paid_cell),
        'paid_present': paid_cell is not None and str(paid_cell).strip() != '',
        # A payment date belongs to the imported month (or the one before);
        # short d/m text and day/month swaps are repaired like entry dates.
        'paid_date': (_entry_date_string(val('paid_date'), target_ym) if target_ym
                      else _date_string(val('paid_date'))),
        'paid_until': _date_string(val('paid_until')),
        'books': _number(val('books')),
        'book_paid': _number(val('book_paid')),
        'book_remaining': _number(val('book_remaining')),
        'remaining': _number(val('remaining')),
        'source_columns': source_columns,
        'fees_present': 'fees' in source_columns,
        'books_present': 'books' in source_columns,
        'book_paid_present': 'book_paid' in source_columns,
        'book_remaining_present': 'book_remaining' in source_columns,
        'remaining_present': 'remaining' in source_columns,
        'method': _clean(val('method'), 40),
        'guardian_name': _clean(val('guardian_name'), 120),
        'guardian_phone': _clean(val('guardian_phone'), 50),
        'note': _clean(val('note')),
    }
    if not record['fees'] and is_master:
        record['fees'] = _number(val('fees'))
    if not any(record.get(key) not in (None, '') for key in (
        'db_id', 'serial', 'class_name', 'fees', 'paid', 'paid_until',
            'guardian_name', 'guardian_phone', 'remaining')):
        return None
    return record


def _entry_record(headers, row, source, kind, target_ym=None, extra_note=''):
    name_index = _col(headers, 'name')
    amount_index = _col(headers, 'amount')
    date_index = _col(headers, 'date')
    name = _clean(row[name_index] if name_index is not None and name_index < len(row) else '')
    amount = _number(row[amount_index] if amount_index is not None and amount_index < len(row) else None)
    if not name or amount is None:
        return None
    date_cell = row[date_index] if date_index is not None and date_index < len(row) else None
    note = _clean(row[_col(headers, 'note')] if _col(headers, 'note') is not None
                  and _col(headers, 'note') < len(row) else '')
    if extra_note:
        note = ('%s · %s' % (note, extra_note)) if note else extra_note
    return {
        'kind': kind, 'name': name, 'amount': amount,
        'date': (_entry_date_string(date_cell, target_ym) if target_ym
                 else _date_string(date_cell)),
        'note': note[:200],
        'source': source,
    }


def _salary_name_key(value):
    """Match Excel staff names to existing employee cards without changing names."""
    key = _norm(value)
    parts = [part for part in key.split()
             if part not in {'mr', 'mrs', 'ms', 'miss', 'teacher'}]
    aliases = {
        'nesreen': 'nesrin',
        'suzie': 'suzi',
        'latefah': 'latifa',
        'noura': 'nora',
        'siette': 'sittie',
    }
    return ' '.join(aliases.get(part, part) for part in parts)


def _sync_salary_records(records, term, env):
    """Make the current term's employee salary cards an exact Excel projection."""
    Salary = env['nursery.salary'].sudo()
    Employee = env['hr.employee'].sudo()
    employees = Employee.search([('active', '=', True)])
    by_key = {}
    for employee in employees:
        key = _salary_name_key(employee.name)
        if key and key not in by_key:
            by_key[key] = employee

    # The workbook is authoritative for the selected term. Remove stale salary
    # rows first, then create exactly one row per salary row in Excel.
    old_rows = Salary.search([('term', '=', term)])
    if old_rows:
        old_rows.unlink()

    synced = 0
    for record in records or []:
        name = _clean(record.get('name'), 200)
        amount = float(record.get('amount') or 0.0)
        if not name:
            continue
        employee = by_key.get(_salary_name_key(name))
        if not employee:
            employee = Employee.create({'name': name, 'active': True})
            by_key[_salary_name_key(name)] = employee
        Salary.create({
            'teacher': employee.name,
            'employee_id': employee.id,
            'expected': amount,
            'actual': 0.0,
            'paid_date': False,
            'term': term,
            'notes': '',
        })
        synced += 1
    return synced


def _parse_records(files, target_ym):
    students, entries, warnings = [], [], []
    summary = {}
    named_month_sheets = False
    loaded = []
    target_year = int(target_ym[:4])
    for item in files or []:
        filename = _clean(item.get('name'), 160)
        try:
            raw = base64.b64decode(item.get('content') or '', validate=True)
        except (ValueError, TypeError):
            warnings.append('الملف %s مشفّر أو تالف ولا يمكن قراءته.' % filename)
            continue
        if not filename or len(raw) > MAX_FILE_BYTES:
            warnings.append('الملف %s أكبر من الحجم المسموح.' % (filename or 'بدون اسم'))
            continue
        try:
            sheets = _read_file(filename, raw)
            loaded.extend((filename, title, rows) for title, rows in sheets)
        except Exception as exc:
            warnings.append('تعذر قراءة %s: %s' % (filename, _clean(exc, 180)))
    for _, title, _ in loaded:
        if _ym_from_text(title, target_year):
            named_month_sheets = True
            break
    row_count = 0
    for filename, title, rows in loaded:
        sheet_ym = _ym_from_text(title, target_year)
        title_norm = _norm(title)
        if 'paid students' in title_norm or 'paid student' in title_norm:
            continue
        if sheet_ym and sheet_ym != target_ym:
            warnings.append('تم تجاهل شيت %s لأنه خاص بشهر %s.' %
                            (title, _month_label(sheet_ym)))
            continue
        if named_month_sheets and not sheet_ym and title_norm not in ('master file', 'master'):
            continue
        if sheet_ym == target_ym:
            summary.update(_summary_values(rows))
        blocks = _header_rows(rows)
        if not blocks:
            continue
        for header_index, kind, headers in blocks:
            next_index = next((index for index, _, _ in blocks
                               if index > header_index), len(rows))
            specs = _table_specs(headers)
            if kind == 'student':
                specs.extend(_embedded_table_specs(rows, header_index, next_index))
            if not specs:
                specs = [{'kind': kind, 'headers': headers}]
            source = '%s / %s / صف %s' % (filename, title, header_index + 1)
            carried_class = ''
            for row_number in range(header_index + 1, next_index):
                row = rows[row_number]
                if not any(value not in (None, '') for value in row):
                    continue
                for spec in specs:
                    if row_number < spec.get('data_start', header_index + 1):
                        continue
                    spec_kind = spec['kind']
                    spec_headers = spec['headers']
                    spec_row = (_project_row(row, spec['indexes'])
                                if 'indexes' in spec else row)
                    if spec_kind == 'student':
                        record = _student_record(spec_headers, spec_row, source,
                                                 title_norm in ('master file', 'master'),
                                                 target_ym)
                        if record:
                            if record.get('class_name'):
                                carried_class = record['class_name']
                            elif carried_class:
                                record['class_name'] = carried_class
                            students.append(record)
                            row_count += 1
                        continue

                    name_index = _col(spec_headers, 'name')
                    amount_index = _col(spec_headers, 'amount')
                    date_index = _col(spec_headers, 'date')
                    relevant = [spec_row[index] for index in (name_index, amount_index, date_index)
                                if index is not None and index < len(spec_row)]
                    if not any(value not in (None, '') for value in relevant):
                        continue
                    entry_name = _norm(spec_row[name_index] if name_index is not None
                                       and name_index < len(spec_row) else '')
                    amount_value = (spec_row[amount_index] if amount_index is not None
                                    and amount_index < len(spec_row) else None)
                    date_value = (spec_row[date_index] if date_index is not None
                                  and date_index < len(spec_row) else None)
                    if any(marker in _norm(value) for value in spec_row
                           if isinstance(value, str)
                           for marker in ('total', 'اجمالي')):
                        continue
                    if not entry_name and amount_value in (None, '', 0, 0.0) and not date_value:
                        continue
                    if 'total' in entry_name or 'اجمالي' in entry_name:
                        continue
                    # Cells typed right after an expense/salary table (e.g. a
                    # name and amount beside a line) are kept as the entry note.
                    extra_note = ''
                    if 'indexes' in spec:
                        last = max(spec['indexes'])
                        taken = set()
                        for other in specs:
                            if other is not spec:
                                taken.update(other.get('indexes') or [])
                        extras = [row[index] for index in range(last + 1, min(len(row), last + 4))
                                  if index not in taken and row[index] not in (None, '')]
                        extra_note = ' '.join(
                            _clean(_norm_value(value), 60) for value in extras).strip()
                    record = _entry_record(spec_headers, spec_row, source, spec_kind,
                                           target_ym, extra_note)
                    if record:
                        entries.append(record)
                        row_count += 1
                    elif any(value not in (None, '') for value in spec_row):
                        warnings.append('تم تجاهل صف غير مكتمل في %s.' % source)
    return {
        'students': _merge_records(students, 'student'),
        'entries': _merge_records(entries, 'entry'),
        'summary': summary,
        'warnings': warnings,
        'rows': row_count,
    }


def _record_key(record, kind):
    if kind == 'student':
        if record.get('db_id') is not None:
            return 'id:%s' % int(record['db_id'])
        if record.get('serial') is not None:
            return 'serial:%s' % int(record['serial'])
        return 'name:%s' % _norm(record.get('name'))
    return '%s:%s:%s' % (record.get('kind'), _norm(record.get('name')),
                         record.get('date') or '')


def _merge_records(records, kind):
    if kind == 'student':
        id_names = {}
        for record in records:
            if record.get('db_id') is not None:
                identifier = int(record['db_id'])
                id_names.setdefault(identifier, set()).add(_student_name_key(record.get('name')))
        conflicting_ids = {identifier for identifier, names in id_names.items()
                           if len(names) > 1}
        records = [dict(record, db_id=None)
                   if record.get('db_id') is not None
                   and int(record['db_id']) in conflicting_ids else dict(record)
                   for record in records]
        return _merge_student_records(records)
    merged = {}
    order = []
    aliases = {}
    for record in records:
        if kind != 'student':
            key = _record_key(record, kind)
        else:
            identity_keys = []
            if record.get('db_id') is not None:
                identity_keys.append('id:%s' % int(record['db_id']))
            elif record.get('serial') is not None and record.get('class_name'):
                identity_keys.append('class-serial:%s:%s' % (
                    _norm(record['class_name']), int(record['serial'])))
            identity_keys.append('name:%s' % _norm(record.get('name')))
            key = next((aliases[item] for item in identity_keys if item in aliases), None)
            if key is None:
                key = identity_keys[0]
        if key not in merged:
            merged[key] = dict(record)
            order.append(key)
        else:
            previous = merged[key]
            for field, value in record.items():
                if field in ('source', 'paid_present', 'source_columns'):
                    continue
                if value not in (None, ''):
                    previous[field] = value
            previous['paid_present'] = previous.get('paid_present') or record.get('paid_present')
            previous['source_columns'] = set(previous.get('source_columns') or set()) | set(
                record.get('source_columns') or set())
            previous['source'] = '%s + %s' % (
                previous.get('source', ''), record.get('source', ''))
        if kind == 'student':
            for identity_key in identity_keys:
                aliases[identity_key] = key
    return [merged[key] for key in order]


def _merge_student_values(previous, record):
    for field, value in record.items():
        if field in ('source', 'paid_present', 'source_columns'):
            continue
        if field == 'class_name' and previous.get('class_name'):
            continue
        if value not in (None, ''):
            previous[field] = value
    previous['paid_present'] = previous.get('paid_present') or record.get('paid_present')
    previous['source_columns'] = set(previous.get('source_columns') or set()) | set(
        record.get('source_columns') or set())
    if record.get('active') is not None:
        previous['active'] = record.get('active')
    previous['source'] = '%s + %s' % (
        previous.get('source', ''), record.get('source', ''))


def _merge_student_records(records):
    merged = {}
    order = []
    for record in (item for item in records if item.get('db_id') is not None):
        key = 'id:%s' % int(record['db_id'])
        if key not in merged:
            merged[key] = dict(record)
            order.append(key)
        else:
            _merge_student_values(merged[key], record)

    for record in (item for item in records if item.get('db_id') is None):
        name = _student_excel_name_key(record.get('name'))
        class_name = _norm(record.get('class_name'))
        serial = (int(record['serial']) if record.get('serial') is not None else None)
        candidates = [key for key in order
                      if _student_excel_name_key(merged[key].get('name')) == name
                      and (not class_name or _norm(merged[key].get('class_name')) == class_name)
                      and (serial is None or merged[key].get('serial') is not None
                           and int(merged[key].get('serial')) == serial)]
        if len(candidates) == 1:
            _merge_student_values(merged[candidates[0]], record)
            continue
        if serial is not None:
            key = 'class-serial:%s:%s' % (class_name, serial)
        else:
            key = 'class-name:%s:%s' % (class_name, name)
        if key not in merged:
            merged[key] = dict(record)
            order.append(key)
        else:
            _merge_student_values(merged[key], record)
    return [merged[key] for key in order]


def _field_exists(model, name):
    return name in _model_fields(model)


def _method(value):
    raw = _norm(value)
    if raw in ('cash', 'كاش', 'نقدي') or 'cash' in raw or 'كاش' in raw or 'نقد' in raw:
        return 'cash'
    if (raw in ('transfer', 'bank transfer', 'تحويل', 'تحويل بنكي')
            or 'transfer' in raw or 'تحويل' in raw):
        return 'transfer'
    if raw in ('card', 'بطاقه', 'بطاقة') or 'card' in raw or 'بطاق' in raw:
        return 'card'
    if raw:
        return 'other'
    return 'cash'


def _class_candidates(name, env):
    if not name:
        return env['nursery.class'].sudo().browse()
    Class = env['nursery.class'].sudo()
    matches = Class.search([('name', '=ilike', name), ('active', '=', True)], limit=2)
    if matches:
        return matches
    normalized = _norm(name).replace('-', ' ')
    prefixes = {
        'kg1': 'kg1', 'kg2': 'kg2', 'kg3': 'kg3',
        'pre kg': 'pre kg', 'prekg': 'pre kg', 'summer': 'summer',
    }
    prefix = prefixes.get(normalized)
    if not prefix:
        return Class.browse()
    candidates = Class.search([('active', '=', True)])
    return candidates.filtered(
        lambda item: _norm(item.name).replace('-', ' ').startswith(prefix))


def _class_for(name, env):
    candidates = _class_candidates(name, env)
    return candidates[0] if len(candidates) == 1 else False


def _ensure_class_for(name, env, target_ym=None):
    """Use the Excel class literally; create it when the exact name is new."""
    cleaned = _clean(name, 80)
    if not cleaned:
        return False
    Class = env['nursery.class'].sudo()
    exact = Class.search([('name', '=ilike', cleaned)], limit=1)
    if exact:
        return exact
    term = 'term_2026' if str(target_ym or '')[:4] == '2026' else 'term_2027'
    return Class.create({'name': cleaned, 'term': term})


def _apply_class_map(parsed, class_map, env):
    class_map = class_map if isinstance(class_map, dict) else {}
    Class = env['nursery.class'].sudo()
    for record in parsed['students']:
        selected = class_map.get(record.get('name'))
        if not selected:
            continue
        try:
            selected = Class.browse(int(selected))
        except (TypeError, ValueError):
            continue
        allowed = _class_candidates(record.get('class_name'), env)
        if selected.exists() and selected.active and selected.id in allowed.ids:
            record['class_name'] = selected.name


def _class_choices(parsed, env):
    # Excel is authoritative. Ambiguous broad names are not guessed and are
    # not sent to a chooser; commit creates the exact name from the sheet.
    return []


def _find_student(record, env):
    Student = env['nursery.student'].sudo()
    # The workbook is authoritative for names and the ID in that workbook is
    # the only cross-system identity. Do not let a similar site name, or a
    # reused class-local serial, redirect an Excel row to another student.
    if record.get('db_id') is not None:
        student = Student.browse(int(record['db_id']))
        if not student.exists():
            return False, 'الـ ID %s الموجود في Excel غير موجود في الموقع.' % int(record['db_id'])
        if _student_name_key(student.name) != _student_name_key(record.get('name')):
            return False, 'الـ ID %s يخص الطالب %s وليس %s.' % (
                int(record['db_id']), student.name, record.get('name'))
        return student, ''
    excel_name = _student_excel_name_key(record.get('name'))
    if excel_name:
        # Archived rows are searched too: unnumbered workbook rows are kept
        # inactive on the site, and a re-import must find them instead of
        # creating a duplicate. When several rows share a name, the single
        # active one wins.
        candidates = Student.with_context(active_test=False).search([])
        exact = candidates.filtered(
            lambda item: _student_excel_name_key(item.name) == excel_name)

        def single(items):
            if len(items) == 1:
                return items
            if not items:
                return False
            active = items.filtered('active')
            if len(active) == 1:
                return active
            if not active:
                # Only archived copies exist (earlier re-imports duplicated
                # unnumbered rows): reuse the newest copy instead of adding one.
                return items.sorted(key=lambda item: item.id, reverse=True)[:1]
            return False

        class_rec = _class_for(record.get('class_name'), env) if record.get('class_name') else False
        if class_rec and _field_exists(Student, 'class_id'):
            same_class = single(exact.filtered(lambda item: item.class_id.id == class_rec.id))
            if same_class:
                return same_class, ''
        if record.get('serial') is not None and _field_exists(Student, 'serial'):
            same_serial = single(exact.filtered(lambda item: item.serial == int(record['serial'])))
            if same_serial:
                return same_serial, ''
        if record.get('serial') is None and not class_rec:
            alone = single(exact)
            if alone:
                return alone, ''
        if len(exact) > 1:
            # Excel remains authoritative when its row has no ID. Do not pick
            # one of several site records; let this row be created as-is.
            return False, ''
    return False, ''


def _month(env, ym):
    return env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)


def _month_fee(month, student):
    if not month or not student:
        return False
    Fee = month.env['nursery.month.fee'].sudo()
    return Fee.search([('month_id', '=', month.id), ('student_id', '=', student.id)], limit=1)


def _norm_value(value):
    if isinstance(value, date):
        return value.strftime('%Y-%m-%d')
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _same_value(old, new):
    if old in (False, None, '') and new in (False, None, ''):
        return True
    if isinstance(old, float) or isinstance(new, float):
        try:
            return abs(float(old or 0) - float(new or 0)) < 0.005
        except (TypeError, ValueError):
            return False
    return _norm_value(old) == _norm_value(new)


def _append_change(changes, field, old, new):
    if not _same_value(old, new):
        changes.append({'field': field, 'old': _norm_value(old), 'new': _norm_value(new)})


def _student_preview(record, month, env):
    student, error = _find_student(record, env)
    if error:
        return {'kind': 'student', 'name': record['name'], 'status': 'warning',
                'status_label': 'يحتاج مراجعة', 'warning': error, 'changes': []}, True
    class_rec = _class_for(record.get('class_name'), env) if record.get('class_name') else False
    class_warning = ('سيتم إنشاء الفصل %s بنفس الاسم المكتوب في Excel.' %
                     record['class_name']) if record.get('class_name') and not class_rec else ''
    fee = _month_fee(month, student) if student else False
    changes = []
    if not student:
        for field in ('name', 'serial', 'class_name', 'fees', 'joining_date',
                      'guardian_name', 'guardian_phone', 'books', 'remaining'):
            value = record.get(field)
            if value not in (None, ''):
                _append_change(changes, field, None, value)
        if record.get('paid_present'):
            _append_change(changes, 'paid', None, record.get('paid'))
        return {'kind': 'student', 'name': record['name'], 'status': 'new',
                'status_label': 'طالب جديد', 'changes': changes,
                'warning': class_warning}, False
    for field, source_field in (
        ('name', 'name'), ('serial', 'serial'), ('joining_date', 'joining_date'),
        ('guardian_name', 'guardian_name'), ('guardian_phone', 'guardian_phone'),
        ('note', 'note'),
    ):
        value = record.get(source_field)
        if field == 'serial' and record.get('db_id') is None:
            continue
        if value not in (None, '') and _field_exists(student, field):
            _append_change(changes, field, getattr(student, field), value)
    if class_rec and record.get('db_id') is not None and _field_exists(student, 'class_id'):
        _append_change(changes, 'class_name', student.class_id.name if student.class_id else '',
                       class_rec.name)
    if record.get('fees') is not None and fee:
        _append_change(changes, 'fees', fee.fees, record['fees'])
    elif record.get('fees') is not None and not fee:
        _append_change(changes, 'fees', None, record['fees'])
    if record.get('paid_present'):
        _append_change(changes, 'paid', fee.paid if fee else None, record.get('paid'))
    if record.get('paid_date'):
        _append_change(changes, 'paid_date', fee.paid_date if fee else None, record['paid_date'])
    if record.get('paid_until') and _field_exists(student, 'paid_until'):
        _append_change(changes, 'paid_until', student.paid_until, record['paid_until'])
    if record.get('method'):
        _append_change(changes, 'method', fee.method if fee else '', _method(record['method']))
    if record.get('books') is not None and record['books'] > 0 and _field_exists(student, 'books_fees'):
        _append_change(changes, 'books', student.books_fees, record['books'])
    if record.get('remaining_present') and fee and _field_exists(fee, 'excel_remaining'):
        _append_change(changes, 'remaining', fee.excel_remaining, record.get('remaining') or 0.0)
    return {'kind': 'student', 'name': student.name, 'status': 'update',
            'status_label': 'تحديث', 'changes': changes}, False


def _entry_preview(record, month, kind, env):
    date_value = record.get('date') or '%s-01' % month.ym
    Entry = env['nursery.month.entry'].sudo()
    entry = Entry.search([('month_id', '=', month.id), ('etype', '=', kind),
                          ('name', '=ilike', record['name']), ('date', '=', date_value)],
                         limit=1) if month else False
    changes = []
    _append_change(changes, 'amount', entry.amount if entry else None, record['amount'])
    _append_change(changes, 'date', entry.date if entry else None, date_value)
    _append_change(changes, 'note', entry.note if entry else '', record.get('note') or '')
    return {'kind': kind, 'name': record['name'],
            'status': 'update' if entry else 'new',
            'status_label': 'تحديث' if entry else 'جديد', 'changes': changes}, False


def _preview(parsed, target_ym, env):
    month = _month(env, target_ym)
    warnings = list(parsed['warnings'])
    blocking = [warning for warning in warnings
                if not warning.startswith('تم تجاهل شيت')]
    if month and month.state == 'closed':
        blocking.append('الشهر %s مقفول، لذلك تم منع التحديث.' % _month_label(target_ym))
    changes = []
    for record in parsed['students']:
        item, blocked = _student_preview(record, month, env)
        changes.append(item)
        if blocked:
            blocking.append('%s: %s' % (record.get('source'), item.get('warning')))
    if month:
        for record in parsed['entries']:
            item, blocked = _entry_preview(record, month, record['kind'], env)
            changes.append(item)
    else:
        for record in parsed['entries']:
            changes.append({
                'kind': record['kind'], 'name': record['name'], 'status': 'new',
                'status_label': 'جديد',
                'changes': [{'field': 'amount', 'old': None, 'new': record['amount']},
                            {'field': 'date', 'old': None,
                             'new': record.get('date') or '%s-01' % target_ym}],
            })
    for warning in blocking:
        if warning not in warnings:
            warnings.append(warning)
    changes = [item for item in changes
               if item.get('changes') or item.get('status') == 'warning']
    return {
        'ok': True, 'target_ym': target_ym, 'target_label': _month_label(target_ym),
        'summary': {
            'rows': parsed['rows'], 'students': len(parsed['students']),
            'entries': len(parsed['entries']),
        },
        'changes': changes, 'warnings': warnings,
        'blocked': bool(blocking), 'can_commit': bool(changes) and not blocking,
    }


def _open_month(env, ym):
    Month = env['nursery.month'].sudo()
    current = Month.search([('ym', '=', ym)], limit=1)
    if current:
        return current
    opener = getattr(Month, '_open_month', None)
    if opener:
        result = opener(ym)
        if result:
            return result[0] if isinstance(result, tuple) else result
    previous = Month.search([('ym', '<', ym)], order='ym desc', limit=1)
    if previous:
        # The monthly workbook carries the cash closing balance forward, not
        # the accounting net.  The model method is the shared source for this
        # calculation when available.
        closing_fn = getattr(previous, '_month_closing', None)
        opening = float(closing_fn() if closing_fn else (previous.opening_balance or 0.0))
        if not closing_fn:
            opening += sum((f.paid or 0.0) for f in previous.fee_ids
                           if getattr(f, 'method', False) in (False, 'cash'))
            opening += sum(e.amount for e in previous.entry_ids
                           if e.etype in ('income', 'reservation'))
    else:
        opening = 0.0
    month = Month.create({'ym': ym, 'opening_balance': opening})
    Fee = env['nursery.month.fee'].sudo()
    source = previous.fee_ids if previous else env['nursery.student'].sudo().search(
        [('active', '=', True)], order='name')
    for row in source:
        student = getattr(row, 'student_id', row)
        vals = {'month_id': month.id, 'student_id': student.id,
                'name': student.name if student else row.name}
        if _field_exists(Fee, 'fees'):
            vals['fees'] = getattr(row, 'fees', 0.0) if previous else getattr(student, 'fees', 0.0)
        Fee.create(vals)
    return month


def _student_vals(record, class_rec, target_ym):
    vals = {}
    columns = record.get('source_columns') or set()
    if record.get('db_id') is not None and record.get('name'):
        # Keep the site's stored name aligned with the authoritative Excel row
        # after the ID has safely identified the existing student.
        vals['name'] = record['name']
    if record.get('serial') is not None:
        vals['serial'] = int(record['serial'])
    if 'joining_date' in columns:
        vals['joining_date'] = record.get('joining_date') or False
    if 'guardian_name' in columns:
        vals['guardian_name'] = record.get('guardian_name') or False
    if 'guardian_phone' in columns:
        vals['guardian_phone'] = record.get('guardian_phone') or False
    if 'note' in columns:
        vals['remark'] = record.get('note') or False
    if class_rec:
        vals['class_id'] = class_rec.id
    level = _student_record_level(record)
    if level in ('prekg', 'kg1', 'kg2', 'kg3'):
        vals['level'] = level
    if record.get('fees_present'):
        vals['fees'] = float(record.get('fees') or 0.0)
    if record.get('books_present'):
        vals['books_fees'] = float(record.get('books') or 0.0)
    if record.get('paid_present') or 'paid' in columns:
        vals['paid'] = record.get('paid', 0) > 0
        vals['paid_at'] = record.get('paid_date') or False
        vals['payment_method'] = (_method(record.get('method'))
                                  if record.get('paid') else False)
    if 'paid_until' in columns:
        vals['paid_until'] = record.get('paid_until') or False
    return vals


def _fee_amount_from_record(record):
    """Return only the explicit agreed-fees cell; never derive it."""
    return float(record.get('fees') or 0.0) if record.get('fees_present') else 0.0


def _upsert_payment(student, fee, record, month, env):
    if not record.get('paid_present'):
        return False
    amount = float(record.get('paid') or 0.0)
    payment_date = record.get('paid_date') or '%s-01' % month.ym
    method = _method(record.get('method'))
    Payment = env['nursery.fee.payment'].sudo()
    period = _month_label(month.ym)
    payment = fee.payment_id if fee and getattr(fee, 'payment_id', False) else False
    if not payment:
        domain = [('student_id', '=', student.id), ('period', '=', period)]
        if _field_exists(Payment, 'payment_type'):
            domain.append(('payment_type', '=', 'tuition'))
        payment = Payment.search(domain, order='id desc', limit=1)
    if amount > 0:
        pvals = {'student_id': student.id, 'date': payment_date, 'amount': amount,
                 'payment_type': 'tuition', 'method': method, 'period': period}
        if payment:
            payment.write(pvals)
        else:
            payment = Payment.create(pvals)
        fee.write({'paid': amount, 'paid_date': payment_date, 'method': method,
                   'payment_id': payment.id})
        student.write({'paid': True, 'paid_at': payment_date,
                       'payment_method': method,
                       'paid_until': record.get('paid_until') or '%s-%02d' % (
                           month.ym, monthrange(int(month.ym[:4]),
                                                int(month.ym[5:7]))[1])})
        return True
    if payment and payment.period == period:
        payment.unlink()
    fee.write({'paid': 0.0, 'paid_date': False, 'payment_id': False})
    return True


def _upsert_student(record, month, env, target_ym):
    Student = env['nursery.student'].sudo()
    student, _ = _find_student(record, env)
    class_rec = (_ensure_class_for(record.get('class_name'), env, target_ym)
                 if record.get('class_name') else False)
    vals = _student_vals(record, class_rec, target_ym)
    if student:
        if record.get('db_id') is None:
            vals.pop('serial', None)
            vals.pop('class_id', None)
        if vals:
            student.write(vals)
    else:
        vals.update({'name': record['name'], 'term': 'term_2026' if target_ym[:4] == '2026' else 'term_2027'})
        student = Student.create(vals)
    fee = _month_fee(month, student)
    Fee = env['nursery.month.fee'].sudo()
    if not fee:
        fee_vals = {'month_id': month.id, 'student_id': student.id, 'name': student.name}
        fee_vals['excel_remaining'] = (float(record.get('remaining') or 0.0)
                                       if record.get('remaining_present') else 0.0)
        if record.get('fees_present'):
            fee_vals['fees'] = _fee_amount_from_record(record)
        elif _field_exists(student, 'fees'):
            fee_vals['fees'] = student.fees or 0.0
        fee = Fee.create(fee_vals)
    else:
        fee.write({'name': student.name})
        fee.write({'excel_remaining': (float(record.get('remaining') or 0.0)
                                       if record.get('remaining_present') else 0.0)})
        if record.get('fees_present'):
            fee.write({'fees': _fee_amount_from_record(record)})
    _upsert_payment(student, fee, record, month, env)
    return student


def _upsert_entry(record, month, env):
    Entry = env['nursery.month.entry'].sudo()
    date_value = record.get('date') or '%s-01' % month.ym
    entry = Entry.search([('month_id', '=', month.id), ('etype', '=', record['kind']),
                          ('name', '=ilike', record['name']), ('date', '=', date_value)],
                         limit=1)
    vals = {'month_id': month.id, 'etype': record['kind'], 'name': record['name'],
            'amount': float(record['amount']), 'date': date_value,
            'note': record.get('note') or ''}
    if record['kind'] == 'expense':
        Expense = env['nursery.expense'].sudo()
        expense = entry.expense_id if entry and getattr(entry, 'expense_id', False) else False
        expense_vals = {'date': date_value, 'value': float(record['amount']),
                        'note': record.get('note') or record['name']}
        if expense:
            expense.write(expense_vals)
        else:
            vals['expense_id'] = Expense.create(expense_vals).id
    elif record['kind'] == 'salary':
        Salary = env['nursery.salary'].sudo()
        term = 'term_2026' if month.ym[:4] == '2026' else 'term_2027'
        salary = Salary.search([('teacher', '=ilike', record['name']),
                                ('term', '=', term)], limit=1)
        salary_vals = {'teacher': record['name'], 'expected': float(record['amount']),
                       'actual': 0.0, 'paid_date': False, 'term': term,
                       'notes': record.get('note') or ''}
        if salary:
            salary.write(salary_vals)
        else:
            Salary.create(salary_vals)
    if entry:
        entry.write(vals)
    else:
        entry = Entry.create(vals)
    return entry


def _excel_month_metrics(parsed, target_ym):
    """Return the September summary using the workbook's own arithmetic.

    The workbook intentionally has three payment rows without a serial. They
    belong in collected cash/bank totals, while the student count remains the
    count of numbered rows. Keeping both measures separate is what makes the
    site match the workbook instead of silently normalizing it.
    """
    students = parsed.get('students') or []
    entries = parsed.get('entries') or []
    summary = parsed.get('summary') or {}
    calculated_collected = sum(float(row.get('paid') or 0.0) for row in students)
    calculated_cash = sum(float(row.get('paid') or 0.0) for row in students
               if row.get('paid') and _method(row.get('method')) == 'cash')
    calculated_transfer = sum(float(row.get('paid') or 0.0) for row in students
               if row.get('paid') and _method(row.get('method')) == 'transfer')
    calculated_books = sum(float(row.get('books') or 0.0) for row in students)
    calculated_due = sum(float(row.get('fees') or 0.0) for row in students
                         if row.get('fees_present'))
    book_paid = sum(float(row.get('book_paid') or 0.0) for row in students
                    if row.get('book_paid_present'))
    book_remaining = sum(float(row.get('book_remaining') or 0.0) for row in students
                         if row.get('book_remaining_present'))
    expense_rows = [row for row in entries if row.get('kind') == 'expense']
    calculated_expenses = sum(float(row.get('amount') or 0.0) for row in expense_rows)
    # The first positive expense line is the workbook's opening cash brought
    # in by Nesrin.  It is kept as a source entry, but is also stored as the
    # month's opening balance so it is not counted twice in the closing cash.
    opening_row = next(
        (row for row in expense_rows
         if float(row.get('amount') or 0.0) > 0
         and 'نسرين' in str(row.get('name') or '')),
        None,
    )
    opening_balance = float(opening_row.get('amount') or 0.0) if opening_row else 0.0
    expenses_paid_out = sum(
        float(row.get('amount') or 0.0)
        for row in expense_rows
        if row is not opening_row and float(row.get('amount') or 0.0) < 0
    )
    calculated_cash_closing = opening_balance + calculated_cash + expenses_paid_out
    calculated_salaries = sum(float(row.get('amount') or 0.0) for row in entries
                   if row.get('kind') == 'salary')
    calculated_numbered_students = sum(1 for row in students if row.get('serial') is not None)
    calculated_remaining_total = sum(
        float(row.get('remaining') or 0.0)
        for row in students
        if row.get('serial') is not None and row.get('remaining_present')
    )
    def exact(name, fallback):
        value = summary.get(name)
        return float(value) if value is not None else float(fallback)

    collected = exact('collected', calculated_collected)
    cash = exact('randa_cash', calculated_cash)
    transfer = exact('bank_transfer', calculated_transfer)
    books = exact('books', calculated_books)
    expenses = exact('expenses', calculated_expenses)
    salaries = exact('salaries', calculated_salaries)
    numbered_students = int(exact('student_count', calculated_numbered_students))
    remaining_total = exact('remaining_total', calculated_remaining_total)
    on_hand_randa = exact('on_hand_randa', calculated_cash_closing)
    cash_closing = on_hand_randa
    randa_on_hand = exact('audit_on_hand_randa', 0.0)
    excel_delta = exact('delta', randa_on_hand - salaries)
    net = exact('net', collected - expenses - salaries)
    return {
        'ym': target_ym,
        'student_count': numbered_students,
        'payment_rows': sum(1 for row in students if float(row.get('paid') or 0.0) > 0),
        'collected': collected,
        'randa_cash': cash,
        'bank_transfer': transfer,
        'books': books,
        'due_total': calculated_due,
        'books_due_total': books,
        'books_paid_total': book_paid,
        'books_remaining_total': book_remaining,
        'remaining_total': remaining_total,
        'expenses': expenses,
        'expenses_paid_out': expenses_paid_out,
        'opening_balance': opening_balance,
        'opening_source': (opening_row.get('name') if opening_row else ''),
        'cash_closing': cash_closing,
        'cash_after_salaries': cash_closing - salaries,
        'salaries': salaries,
        'expected_salaries': salaries,
        'on_hand_randa': on_hand_randa,
        'randa_on_hand': randa_on_hand,
        'delta': excel_delta,
        'net': net,
    }


def _replace_month_from_excel(parsed, target_ym, env, roster=True):
    """Replace one month from the authoritative workbook, without upserts.

    This path is deliberately destructive only inside the selected accounting
    month. It clears that month's fees/payments/entries, archives active
    roster rows absent from the numbered Excel rows, and then writes every
    Excel row exactly once. It is used by the explicit `replace` import mode.
    """
    month = _open_month(env, target_ym)
    if month.state == 'closed':
        raise ValueError('الشهر مقفول — لا يمكن استبدال بياناته.')
    metrics = _excel_month_metrics(parsed, target_ym)
    # The positive Nesrin line is the opening cash source. Keep the original
    # entry for auditability, but do not count it again in cash closing.
    month.write({'opening_balance': metrics['opening_balance']})

    Fee = env['nursery.month.fee'].sudo()
    Payment = env['nursery.fee.payment'].sudo()
    Entry = env['nursery.month.entry'].sudo()
    Student = env['nursery.student'].sudo()
    period = _month_label(target_ym)

    # Remove the selected month's linked documents first. The period filter
    # also catches payment rows that were created by an earlier bad import.
    month_fees = Fee.search([('month_id', '=', month.id)])
    linked_payments = month_fees.mapped('payment_id')
    if linked_payments:
        linked_payments.unlink()
    period_payments = Payment.search([('period', '=', period)])
    if period_payments:
        period_payments.unlink()

    old_entries = Entry.search([('month_id', '=', month.id)])
    linked_expenses = old_entries.mapped('expense_id')
    if old_entries:
        old_entries.unlink()
    if linked_expenses:
        linked_expenses.unlink()
    if month_fees:
        month_fees.unlink()

    canonical_active_ids = set()
    created = 0
    updated = 0
    fee_count = 0
    payment_count = 0
    skipped_unmatched = 0

    for record in parsed.get('students') or []:
        student = False
        db_id = record.get('db_id')
        if db_id is not None:
            student = Student.browse(int(db_id))
            if not student.exists():
                student = False
        else:
            # Rows without an ID were created by an earlier import; find them
            # by name/class/serial so a re-import never duplicates them.
            student, _unused = _find_student(record, env)
        if student:
            updated += 1
        elif not roster:
            # Payments-only mode never touches the roster. An Excel row with
            # no matching student is reported, not created.
            skipped_unmatched += 1
            continue
        else:
            student = Student.create({
                'name': record.get('name') or 'بدون اسم',
                'term': 'term_2026' if target_ym[:4] == '2026' else 'term_2027',
            })
            created += 1

        # Payments-only mode leaves student fields untouched: a back-month
        # workbook must not resurrect old class, fees or guardian values.
        if roster:
            vals = {
                'name': record.get('name') or student.name,
                'active': bool(record.get('active')),
                'serial': int(record['serial']) if record.get('serial') is not None else False,
                'joining_date': record.get('joining_date') or False,
                'guardian_name': record.get('guardian_name') or False,
                'guardian_phone': record.get('guardian_phone') or False,
                'remark': record.get('note') or False,
                'fees': float(record.get('fees') or 0.0),
                'books_fees': float(record.get('books') or 0.0),
                'paid': float(record.get('paid') or 0.0) > 0,
                'paid_at': record.get('paid_date') or False,
                'paid_until': record.get('paid_until') or False,
                'payment_method': (_method(record.get('method'))
                                   if float(record.get('paid') or 0.0) > 0 else False),
            }
            # The class name is copied literally from Excel. A new exact name is
            # created instead of guessing one of the existing subgroups.
            class_rec = (_ensure_class_for(record.get('class_name'), env, target_ym)
                         if record.get('class_name') else False)
            if class_rec:
                vals['class_id'] = class_rec.id
            elif not db_id:
                vals['class_id'] = False
            level = _student_record_level(record)
            if level in ('prekg', 'kg1', 'kg2', 'kg3'):
                vals['level'] = level
            student.write(vals)

        if record.get('active'):
            canonical_active_ids.add(student.id)

        amount = float(record.get('paid') or 0.0)
        fee_vals = {
            'month_id': month.id,
            'student_id': student.id,
            'name': record.get('name') or student.name,
            'fees': _fee_amount_from_record(record),
            'excel_remaining': (float(record.get('remaining') or 0.0)
                                if record.get('remaining_present') else 0.0),
            'paid': amount,
            'paid_date': record.get('paid_date') or False,
            'method': (_method(record.get('method')) if amount > 0 else False),
            'note': record.get('note') or False,
        }
        fee = Fee.create(fee_vals)
        fee_count += 1
        if amount > 0:
            payment = Payment.create({
                'student_id': student.id,
                'date': record.get('paid_date') or '%s-01' % target_ym,
                'amount': amount,
                'payment_type': 'tuition',
                'method': _method(record.get('method')),
                'period': period,
            })
            fee.write({'payment_id': payment.id})
            payment_count += 1

    # The live roster must have exactly the numbered Excel students. Rows
    # without a serial remain as inactive historical/payment records above.
    if roster:
        active_students = Student.search([('active', '=', True)])
        to_archive = active_students.filtered(lambda item: item.id not in canonical_active_ids)
        if to_archive:
            to_archive.write({'active': False})

    for record in parsed.get('entries') or []:
        _upsert_entry(record, month, env)

    salary_term = 'term_2026' if target_ym[:4] == '2026' else 'term_2027'
    salary_count = _sync_salary_records(
        [record for record in parsed.get('entries') or []
         if record.get('kind') == 'salary'],
        salary_term,
        env,
    )

    icp = env['ir.config_parameter'].sudo()
    icp.set_param('nursery.excel_month_%s' % target_ym, json.dumps(metrics, ensure_ascii=False))
    # The dashboard has a compact monthly override for the financial chart.
    ext = {}
    try:
        ext = json.loads(icp.get_param('nursery.ext_fin', '') or '{}')
    except Exception:
        ext = {}
    if not isinstance(ext, dict):
        ext = {}
    ext[target_ym] = {
        'ym': target_ym,
        'income': metrics['collected'],
        'student_income': metrics['collected'],
        'extra_income': 0.0,
        'salaries': metrics['salaries'],
        'other': metrics['expenses'],
        'cash': metrics['randa_cash'],
        'transfer': metrics['bank_transfer'],
        'books': metrics['books'],
        'books_due_total': metrics['books_due_total'],
        'books_paid_total': metrics['books_paid_total'],
        'books_remaining_total': metrics['books_remaining_total'],
        'remaining_total': metrics['remaining_total'],
        'payment_rows': metrics['payment_rows'],
        'student_count': metrics['student_count'],
        'on_hand_randa': metrics['on_hand_randa'],
        'randa_on_hand': metrics['randa_on_hand'],
        'delta': metrics['delta'],
        'opening_balance': metrics['opening_balance'],
        'opening_source': metrics['opening_source'],
        'expenses_paid_out': metrics['expenses_paid_out'],
        'cash_closing': metrics['cash_closing'],
        'cash_after_salaries': metrics['cash_after_salaries'],
        'net': metrics['net'],
    }
    icp.set_param('nursery.ext_fin', json.dumps(ext, ensure_ascii=False))

    return {
        'students_created': created,
        'students_updated': updated,
        'students_skipped_unmatched': skipped_unmatched,
        'roster_applied': bool(roster),
        'students_active': len(canonical_active_ids),
        'fees_rebuilt': fee_count,
        'payments_rebuilt': payment_count,
        'expenses_rebuilt': sum(1 for r in parsed.get('entries') or []
                                if r.get('kind') == 'expense'),
        'salaries_rebuilt': salary_count,
        'metrics': metrics,
    }


def _student_export_workbook(env):
    template = os.path.join(os.path.dirname(__file__), '..', 'assets',
                            'student-export-template.xlsx')
    if os.path.exists(template):
        book = load_workbook(template)
        sheet = book['الطلاب']
    else:
        book = Workbook()
        sheet = book.active
        sheet.title = 'الطلاب'
        sheet.append(['الاسم', 'الصف', 'حالة الدفع', 'إجمالي المدفوع',
                      'آخر دفعة', 'مدفوع حتى', 'مرتبط بولي الأمر',
                      'اسم ولي الأمر', 'هاتف ولي الأمر', 'ID', 'ملاحظات'])

    students = env['nursery.student'].sudo().search([], order='name')
    style_cells = [copy(sheet.cell(2, column)._style) for column in range(1, 12)]
    today = datetime.now(pytz.timezone('Asia/Riyadh')).date()
    for row_number, student in enumerate(students, 2):
        last = student.payment_ids.sorted(
            lambda payment: (payment.date or today, payment.id), reverse=True)[:1]
        if student.paid_until and student.paid_until < today:
            status = 'overdue'
        elif student.paid:
            status = 'paid'
        else:
            status = 'unpaid'
        values = [
            student.name or '', student.class_id.name or '', status,
            student.total_paid or 0.0, last.amount if last else 0.0,
            student.paid_until or '', 'نعم' if student.parent_user_id else 'لا',
            student.guardian_name or '', student.guardian_phone or '',
            student.id, student.remark or '',
        ]
        for column, value in enumerate(values, 1):
            cell = sheet.cell(row_number, column, value)
            cell._style = copy(style_cells[column - 1])
        sheet.row_dimensions[row_number].height = 30
    sheet.freeze_panes = 'A2'
    return book, students


class NurseryExcelImport(http.Controller):
    @http.route('/api/manager/excel/export', type='http', auth='public', methods=['GET'], csrf=False, cors=WEBSITE)
    def api_manager_excel_export(self, mt=None, **kw):
        if not _manager_by_token(mt):
            return request.make_response('unauthorized', headers=[('Content-Type', 'text/plain')], status=401)
        groups = [('الفصول','nursery.class',['id','name','level','teacher_id','active']),('المدفوعات','nursery.fee.payment',['id','student_id','date','amount','method','period','note']),('الحضور','nursery.attendance',['id','student_id','date','status','arrival','departure','by_parent','note']),('الكتب','nursery.book',['id','name','code','level','price','cost','received_qty','issued_qty','stock_qty','note','active']),('حركة الكتب','nursery.book.move',['id','book_id','move_type','qty','date','student_id','paid','note']),('المرتبات','nursery.salary',['id','teacher','employee_id','expected','actual','paid_date','term','notes']),('المصروفات','nursery.expense',['id','date','value','term','note']),('الشهور','nursery.month',['id','ym','state','opening_balance','closed_at']),('رسوم الشهور','nursery.month.fee',['id','month_id','student_id','name','fees','paid','paid_date','method','note']),('قيود الشهور','nursery.month.entry',['id','month_id','etype','name','amount','date','note']),('الإجازات','nursery.holiday',['id','name','date_from','date_to','note'])]
        book, students = _student_export_workbook(request.env)
        student_header_styles = [copy(book['الطلاب'].cell(1, column)._style)
                                 for column in range(1, 12)]
        overview = book.create_sheet('ملخص التصدير', 0); overview.append(['المجموعة','عدد السجلات'])
        overview.append(['الطلاب', len(students)])
        for title, model_name, names in groups:
            model = request.env[model_name].sudo(); fmap = model.fields_get(names); names = [n for n in names if n in fmap]
            sheet = book.create_sheet(title[:31]); sheet.append([fmap[n].get('string') or n for n in names]); records = model.search([])
            for rec in records:
                row = []
                for name in names:
                    value = getattr(rec, name, '')
                    if hasattr(value, 'display_name'): value = value.display_name
                    elif isinstance(value, (date, datetime)): value = str(value)
                    elif isinstance(value, bool): value = 'نعم' if value else 'لا'
                    row.append(value if value is not False else '')
                sheet.append(row)
            sheet.freeze_panes = 'A2'; sheet.auto_filter.ref = sheet.dimensions
            for column, cell in enumerate(sheet[1], 1):
                cell._style = copy(student_header_styles[min(column, 11) - 1])
            overview.append([title, len(records)])
        output = io.BytesIO(); book.save(output); output.seek(0)
        filename = 'montessori-export-%s.xlsx' % datetime.now(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d')
        return request.make_response(output.getvalue(), headers=[('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),('Content-Disposition','attachment; filename="%s"' % filename),('Cache-Control','no-store')])

    # ---- مزامنة من لينك Google Sheets ----------------------------------
    # الشيت هو نفسه ملف Excel؛ الفرق الوحيد إنه بيتسحب من جوجل بدل ما
    # يترفع يدوياً. بنرجّع نفس شكل files[] عشان المعاينة والاعتماد
    # يعدّوا على /api/manager/excel/import من غير أي ازدواج في المنطق.
    @http.route('/api/manager/excel/sheet', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_excel_sheet(self, mt=None, action='get', url=None, **kw):
        if not _manager_by_token(mt):
            return {'ok': False, 'error': 'unauthorized'}
        icp = request.env['ir.config_parameter'].sudo()
        saved = (icp.get_param(SHEET_URL_PARAM) or '').strip()

        if action == 'save':
            raw = str(url or '').strip()
            if not raw:
                icp.set_param(SHEET_URL_PARAM, '')
                return {'ok': True, 'url': '', 'sheet_id': ''}
            sheet_id = _sheet_id(raw)
            if not sheet_id:
                return {'ok': False,
                        'error': 'الرابط ليس رابط Google Sheets صالحاً.'}
            icp.set_param(SHEET_URL_PARAM, raw)
            return {'ok': True, 'url': raw, 'sheet_id': sheet_id}

        if action == 'get':
            return {'ok': True, 'url': saved, 'sheet_id': _sheet_id(saved)}

        if action != 'fetch':
            return {'ok': False, 'error': 'إجراء غير صالح.'}

        target = str(url or '').strip() or saved
        if not target:
            return {'ok': False, 'error': 'ما فيش لينك شيت محفوظ بعد.'}
        sheet_id = _sheet_id(target)
        if not sheet_id:
            return {'ok': False,
                    'error': 'الرابط ليس رابط Google Sheets صالحاً.'}
        try:
            content, err = _download_sheet(sheet_id)
        except Exception:
            content, err = None, 'تعذّر الوصول إلى Google Sheets الآن.'
        if err:
            return {'ok': False, 'error': err}
        return {'ok': True, 'sheet_id': sheet_id, 'url': target,
                'files': [{'name': 'google-sheet-%s.xlsx' % sheet_id[:8],
                           'content': base64.b64encode(content).decode('ascii')}]}

    @http.route('/api/manager/excel/import', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_excel_import(self, mt=None, mode='preview', files=None,
                                 class_map=None, replace=False, **kw):
        manager = _manager_by_token(mt)
        if not manager:
            return {'ok': False, 'error': 'unauthorized'}
        files = files if isinstance(files, list) else []
        total = 0
        for item in files:
            content = item.get('content') if isinstance(item, dict) else ''
            try:
                total += len(base64.b64decode(content or '', validate=True))
            except (ValueError, TypeError):
                return {'ok': False, 'error': 'يوجد ملف غير صالح أو تالف.'}
        if not files or total > MAX_TOTAL_BYTES:
            return {'ok': False, 'error': 'اختاري ملفات Excel بإجمالي لا يتجاوز 24 ميجابايت.'}
        today = datetime.now(pytz.timezone('Asia/Riyadh')).date()
        current_ym = today.strftime('%Y-%m')
        requested = kw.get('target_ym')
        if requested in (None, '', current_ym):
            target_ym = current_ym
        else:
            target_ym = _valid_ym(requested)
            if not target_ym:
                # Reject outright: silently falling back to the current month
                # would import one month's numbers into another.
                return {'ok': False,
                        'error': 'الشهر المطلوب غير صالح. اختاري شهراً من الموسم الحالي.'}
        # A month other than the running one imports payments only. Rewriting
        # the roster from an old workbook would archive every student who
        # joined after it and restore stale class and guardian values.
        roster = (target_ym == current_ym)
        parsed = _parse_records(files, target_ym)
        _apply_class_map(parsed, class_map, request.env)
        if not parsed['students'] and not parsed['entries']:
            return {'ok': False, 'error': 'لم أجد جداول مفهومة. تأكدي من وجود أعمدة الاسم والمبلغ/الرسوم.'}
        if mode == 'replace' or replace:
            try:
                summary = _replace_month_from_excel(parsed, target_ym, request.env, roster=roster)
            except ValueError as exc:
                return {'ok': False, 'error': _clean(exc, 180)}
            return {'ok': True, 'target_ym': target_ym,
                    'target_label': _month_label(target_ym),
                    'summary': summary, 'warnings': parsed['warnings']}
        if mode == 'preview':
            result = _preview(parsed, target_ym, request.env)
            result['class_choices'] = _class_choices(parsed, request.env)
            return result
        if mode != 'commit':
            return {'ok': False, 'error': 'وضع استيراد غير صالح.'}
        preview = _preview(parsed, target_ym, request.env)
        choices = _class_choices(parsed, request.env)
        if choices:
            return {'ok': False, 'error': 'اختاري الفصل الصحيح للطلاب الجدد قبل الاعتماد.',
                    'class_choices': choices}
        if preview.get('blocked'):
            return {'ok': False, 'error': 'لا يمكن الاعتماد قبل حل التحذيرات.', 'warnings': preview.get('warnings', [])}
        month = _open_month(request.env, target_ym)
        if month.state == 'closed':
            return {'ok': False, 'error': 'الشهر مقفول — لا يمكن التعديل.'}
        # Excel is the accounting master. Commit must rebuild the selected
        # month from the parsed workbook so its summary values, remaining
        # balances, and roster cannot retain data from an older import.
        summary = _replace_month_from_excel(parsed, target_ym, request.env, roster=roster)
        return {'ok': True, 'target_ym': target_ym, 'target_label': _month_label(target_ym),
                'summary': summary, 'warnings': parsed['warnings']}
