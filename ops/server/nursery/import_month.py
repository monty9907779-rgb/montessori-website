# -*- coding: utf-8 -*-
"""استيراد شهر محاسبي من ملف Excel من داخل السيرفر — بما فيها الشهور المقفولة.

هذا هو المسار الوحيد لتعديل شهر مقفول. الموقع (زر «مزامنة Excel» و«مزامنة لينك
الشيت») يرفض أي شهر حالته closed، فالتعديل بعد إقفال الشهر يتم فقط من هنا
بواسطة من يملك صلاحية الدخول للسيرفر.

تشغيل (على السيرفر):

    odoo shell -d <DB> --no-http < /dev/null  # للتأكد من اسم القاعدة
    odoo shell -d <DB> --no-http -c /etc/odoo/odoo.conf <<'EOF'
    exec(open('/opt/odoo/addons/nursery/import_month.py').read())
    run(env, '/root/sep_montesori.xlsx', '2026-09', lock=True)
    EOF

- يعيد بناء الشهر بالكامل من الشيت (نفس وضع «استبدال» في الموقع).
- لو الشهر مقفول يفتحه مؤقتاً ثم يقفله بنفس التوقيت والمستخدم بعد الاستيراد.
- lock=True يقفل الشهر بعد الاستيراد حتى لو كان مفتوحاً.
- يطبع ملخص الأرقام (المحصّل، كاش رندة، المصروفات، في يد رندة، الرواتب، الطلاب).
"""
import base64
import json
import os
import sys


def run(env, path, ym, lock=True, roster=True):
    from odoo import fields
    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else ''
    sys.path.insert(0, here or os.getcwd())
    from nursery import excel_import  # noqa: E402  (the installed addon)

    if not excel_import._valid_ym(ym):
        raise SystemExit('شهر غير صالح: %s' % ym)
    with open(path, 'rb') as handle:
        raw = handle.read()
    files = [{'name': os.path.basename(path),
              'content': base64.b64encode(raw).decode('ascii')}]
    parsed = excel_import._parse_records(files, ym)
    if not parsed['students'] and not parsed['entries']:
        raise SystemExit('لم أجد جداول مفهومة في %s' % path)

    Month = env['nursery.month'].sudo()
    month = Month.search([('ym', '=', ym)], limit=1)
    was_closed = bool(month and month.state == 'closed')
    closed_by = month.closed_by.id if was_closed else False
    if was_closed:
        month.write({'state': 'open'})
    try:
        summary = excel_import._replace_month_from_excel(parsed, ym, env, roster=roster)
    except Exception:
        if was_closed:
            month.write({'state': 'closed'})
        raise
    month = Month.search([('ym', '=', ym)], limit=1)
    if lock or was_closed:
        month.write({'state': 'closed', 'closed_at': fields.Datetime.now(),
                     'closed_by': closed_by or env.user.id})
    env.cr.commit()

    metrics = summary.get('metrics') or {}
    print(json.dumps({
        'ym': ym, 'state': month.state,
        'students': summary.get('students_active'),
        'collected': metrics.get('collected'),
        'randa_cash': metrics.get('randa_cash'),
        'bank_transfer': metrics.get('bank_transfer'),
        'expenses': metrics.get('expenses'),
        'on_hand_randa': metrics.get('on_hand_randa'),
        'salaries': metrics.get('salaries'),
        'net': metrics.get('net'),
        'warnings': [w for w in parsed.get('warnings', []) if not w.startswith('تم تجاهل شيت')],
    }, ensure_ascii=False, indent=1))
    return summary
