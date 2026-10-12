# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import io
import json
import pytz
import werkzeug.exceptions
from openpyxl import Workbook

from odoo import fields, http
from odoo.http import request
from .roles import WEBSITE as WEBSITE_ORIGIN, _manager_by_token

NURSERY_TZ = 'Asia/Riyadh'


def _allowed():
    u = request.env.user
    return (u.has_group('nursery.group_nursery_manager')
            or u.has_group('base.group_system'))


def _tz():
    return pytz.timezone(NURSERY_TZ)


def _fmt(dt):
    if not dt:
        return False
    return pytz.utc.localize(dt).astimezone(_tz()).strftime('%H:%M')


DASH_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="theme-color" content="#0f172a"/>
<title>داشبورد روضة كوكب الطفل الحر</title>
<style>
 * { box-sizing:border-box; margin:0; padding:0; font-family:-apple-system,"Segoe UI",Tahoma,sans-serif; }
 body { background:#0f172a; color:#e2e8f0; min-height:100vh; padding:16px; }
 h1 { font-size:20px; margin-bottom:2px; } .sub { color:#64748b; font-size:12px; margin-bottom:16px; }
 .kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:14px; }
 .kpi { background:#1e293b; border-radius:14px; padding:14px; border-right:4px solid #334155; }
 .kpi .v { font-size:22px; font-weight:800; margin-top:4px; }
 .kpi .l { font-size:12px; color:#94a3b8; }
 .kpi.green { border-color:#22c55e; } .kpi.green .v { color:#4ade80; }
 .kpi.red { border-color:#ef4444; } .kpi.red .v { color:#f87171; }
 .kpi.amber { border-color:#f59e0b; } .kpi.amber .v { color:#fbbf24; }
 .kpi.violet { border-color:#8b5cf6; } .kpi.violet .v { color:#a78bfa; }
 .kpi.blue { border-color:#3b82f6; } .kpi.blue .v { color:#60a5fa; }
 .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:12px; }
 .card { background:#1e293b; border-radius:14px; padding:14px; }
 .card h3 { font-size:14px; color:#94a3b8; margin-bottom:12px; }
 .bars { display:flex; align-items:flex-end; gap:8px; height:130px; }
 .bar { flex:1; display:flex; flex-direction:column; justify-content:flex-end; align-items:center; height:100%; }
 .bar i { display:block; width:100%; background:linear-gradient(180deg,#4ade80,#16a34a); border-radius:6px 6px 0 0; min-height:2px; }
 .bar.exp i { background:linear-gradient(180deg,#f87171,#dc2626); }
 .bar.att i { background:linear-gradient(180deg,#60a5fa,#2563eb); }
 .bar b { font-size:10px; color:#e2e8f0; margin-bottom:2px; }
 .bar span { font-size:9px; color:#64748b; margin-top:4px; white-space:nowrap; }
 table { width:100%; border-collapse:collapse; font-size:13px; }
 th { color:#64748b; font-weight:600; text-align:right; padding:6px 4px; border-bottom:1px solid #334155; font-size:11px; }
 td { padding:7px 4px; border-bottom:1px solid #24344d; }
 .tag { padding:1px 8px; border-radius:8px; font-size:11px; font-weight:700; }
 .t-green { background:#14532d; color:#4ade80; } .t-red { background:#7f1d1d; color:#fca5a5; }
 .t-amber { background:#78350f; color:#fcd34d; } .t-gray { background:#334155; color:#94a3b8; }
 .empty { color:#475569; text-align:center; padding:14px; font-size:13px; }
</style>
</head>
<body>
<div style="display:flex; align-items:center; gap:10px; margin-bottom:14px; flex-wrap:wrap;">
  <a href="/odoo" style="background:#334155;color:#e2e8f0;text-decoration:none;padding:9px 16px;border-radius:10px;font-size:13px;font-weight:700;">◀ رجوع للنظام</a>
  <a href="/odoo/action-nursery.action_nursery_student" style="background:#1e293b;color:#94a3b8;text-decoration:none;padding:9px 14px;border-radius:10px;font-size:13px;">👧 الطلاب</a>
  <a href="/odoo/action-nursery.action_nursery_fee_payment" style="background:#1e293b;color:#94a3b8;text-decoration:none;padding:9px 14px;border-radius:10px;font-size:13px;">💳 المدفوعات</a>
  <a href="/odoo/action-nursery.action_nursery_deduction" style="background:#1e293b;color:#94a3b8;text-decoration:none;padding:9px 14px;border-radius:10px;font-size:13px;">⏰ الخصومات</a>
  <a href="/nursery-roles" style="background:#1e293b;color:#94a3b8;text-decoration:none;padding:9px 14px;border-radius:10px;font-size:13px;">👥 توزيع الأدوار</a>
  <a href="__REVIEW_URL__" style="background:#1e293b;color:#94a3b8;text-decoration:none;padding:9px 14px;border-radius:10px;font-size:13px;">📝 مراجعة أولياء الأمور</a>
</div>
<h1>📊 داشبورد روضة كوكب الطفل الحر</h1>
<div class="sub" id="stamp">... جاري التحميل</div>
<div class="kpis" id="kpis"></div>
<div class="grid" id="grid"></div>
<script>
function esc(s){const d=document.createElement('div');d.textContent=s==null?'':String(s);return d.innerHTML;}
function money(v){return (Math.round(v*100)/100).toLocaleString('en') + ' ر.س';}

async function load() {
  const r = await fetch('/nursery-dashboard/data', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({jsonrpc:'2.0',method:'call',params:{}})});
  const d = (await r.json()).result;
  document.getElementById('stamp').textContent = 'آخر تحديث: ' + new Date().toLocaleTimeString('ar-EG') + ' — بيتحدث لوحده كل دقيقة';

  document.getElementById('kpis').innerHTML =
    kpi('green','إجمالي المحصَّل', money(d.money.income_total)) +
    kpi('red','إجمالي المصروفات', money(d.money.expense_total)) +
    kpi(d.money.net>=0?'green':'red','الصافي', money(d.money.net)) +
    kpi('blue','محصَّل النهارده', money(d.money.income_today) + ' (' + d.money.count_today + ' دفعة)') +
    kpi('violet','الطلاب', d.students.total + ' — مدفوع ' + d.students.paid) +
    kpi(d.students.overdue_count?'amber':'green','متأخرين في الدفع', d.students.overdue_count) +
    kpi('blue','حضور الأطفال النهارده', d.att_today.present + ' / ' + d.students.total) +
    kpi(d.staff.late_today?'amber':'green','تأخيرات الموظفين النهارده', d.staff.late_today);

  let g = '';
  g += card('💰 الإيرادات مقابل المصروفات (بالشهر)', dualBars(d.money.by_month));
  g += card('👶 حضور الأطفال — آخر 14 يوم', bars(d.att_14, 'att'));
  g += card('🧑‍🏫 الموظفين النهارده', staffTable(d.staff.today));
  g += card('⛔ الطلاب المتأخرين في الدفع', overdueTable(d.students.overdue));
  g += card('👧 غياب الأطفال النهارده', absentList(d.att_today));
  g += card('⏰ خصومات الموظفين (الشهر ده)', dedTable(d.staff.deductions));
  document.getElementById('grid').innerHTML = g;
}
function kpi(c,l,v){return '<div class="kpi '+c+'"><div class="l">'+l+'</div><div class="v">'+v+'</div></div>';}
function card(t,body){return '<div class="card"><h3>'+t+'</h3>'+body+'</div>';}

function dualBars(rows){
  if(!rows.length) return '<div class="empty">بعد لا يوجد بيانات</div>';
  const mx = Math.max(...rows.map(r=>Math.max(r.income,r.expense)),1);
  let h='<div class="bars">';
  rows.forEach(r=>{
    h+='<div class="bar"><b>'+Math.round(r.income/1000)+'k</b><i style="height:'+(r.income/mx*100)+'%"></i><span>'+esc(r.label)+'</span></div>';
    h+='<div class="bar exp"><b>'+Math.round(r.expense/1000)+'k</b><i style="height:'+(r.expense/mx*100)+'%"></i><span>مصروف</span></div>';
  });
  return h+'</div>';
}
function bars(rows, cls){
  if(!rows.length) return '<div class="empty">بعد لا يوجد تسجيل حضور للأطفال</div>';
  const mx = Math.max(...rows.map(r=>r.value),1);
  let h='<div class="bars">';
  rows.forEach(r=>{ h+='<div class="bar '+cls+'"><b>'+r.value+'</b><i style="height:'+(r.value/mx*100)+'%"></i><span>'+esc(r.label)+'</span></div>'; });
  return h+'</div>';
}
function staffTable(rows){
  if(!rows.length) return '<div class="empty">لا يوجد موظفين مسجلين حضور النهارده</div>';
  let h='<table><tr><th>الموظفة</th><th>حضور</th><th>انصراف</th><th>الحالة</th></tr>';
  rows.forEach(r=>{
    let st = r.exempt ? '<span class="tag t-gray">معفي</span>'
      : !r.check_in ? '<span class="tag t-red">لم تحضر</span>'
      : r.late_min > 0 ? '<span class="tag t-amber">متأخرة '+r.late_min+' د</span>'
      : '<span class="tag t-green">في الموعد</span>';
    h+='<tr><td>'+esc(r.name)+'</td><td>'+(r.check_in||'—')+'</td><td>'+(r.check_out||'—')+'</td><td>'+st+'</td></tr>';
  });
  return h+'</table>';
}
function overdueTable(rows){
  if(!rows.length) return '<div class="empty">🎉 لا يوجد حد متأخر في الدفع</div>';
  let h='<table><tr><th>الطالب</th><th>الرسوم</th><th>متأخر</th></tr>';
  rows.forEach(r=>{ h+='<tr><td>'+esc(r.name)+'</td><td>'+money(r.fees)+'</td><td><span class="tag t-red">'+r.days+' يوم</span></td></tr>'; });
  return h+'</table>';
}
function absentList(a){
  if(!a.marked) return '<div class="empty">بعد محدش سجل حضور أطفال النهارده</div>';
  if(!a.absent_names.length) return '<div class="empty">🎉 كل الأطفال المسجلين حاضرين</div>';
  return '<div style="font-size:13px; line-height:2">'+a.absent_names.map(n=>'👧 '+esc(n)).join('<br/>')+'</div>';
}
function dedTable(rows){
  if(!rows.length) return '<div class="empty">🎉 لا يوجد خصومات الشهر ده</div>';
  let h='<table><tr><th>الموظفة</th><th>غياب</th><th>تأخير</th><th>انصراف مبكر</th><th>الخصم (ر.س)</th></tr>';
  rows.forEach(r=>{ h+='<tr><td>'+esc(r.name)+'</td><td>'+r.absences+'</td><td>'+r.lates+'</td><td>'+(r.earlies||0)+'</td><td><span class="tag t-amber">'+Math.round(r.amount||0)+'</span></td></tr>'; });
  return h+'</table>';
}
load();
setInterval(load, 60000);
</script>
</body>
</html>"""


GALLERY_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="referrer" content="no-referrer"/>
<title>__NAME__</title>
<style>
 *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,"Segoe UI",Tahoma,sans-serif;}
 body{background:#0f172a;color:#e2e8f0;min-height:100vh;}
 header{background:linear-gradient(135deg,#7c3aed,#a855f7);padding:16px;position:sticky;top:0;z-index:5;
        display:flex;align-items:center;gap:12px;}
 header a{background:rgba(255,255,255,.2);color:#fff;text-decoration:none;padding:8px 14px;border-radius:10px;font-size:13px;font-weight:700;}
 header h1{font-size:17px;color:#fff;flex:1;} header .c{color:#e9d5ff;font-size:13px;}
 .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;padding:12px;}
 .grid a{display:block;aspect-ratio:1;border-radius:12px;overflow:hidden;background:#1e293b;}
 .grid img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .2s;}
 .grid a:hover img{transform:scale(1.05);}
 .empty{text-align:center;color:#64748b;padding:60px 20px;}
</style></head><body>
<header><a href="javascript:history.back()">◀ رجوع</a><h1>📷 __NAME__</h1><span class="c">__COUNT__ صورة</span></header>
<div class="grid">__TILES__</div>
</body></html>"""


def _attendance_report(env, days=14):
    """سجل حضور الموظفين لآخر N يوم عمل — نفس منطق /api/manager/attendance،
    مستخرَج هنا عشان يشتركه مسار الـJSON ومسار تصدير الإكسل بلا ازدواج."""
    try:
        days = max(1, min(int(days or 14), 92))
    except (TypeError, ValueError):
        days = 14
    tz = _tz()
    today = datetime.now(pytz.utc).astimezone(tz).date()
    start_day = today - timedelta(days=days - 1)
    start_utc = tz.localize(datetime.combine(start_day, time(0, 0))) \
        .astimezone(pytz.utc).replace(tzinfo=None)
    Ded = env['nursery.deduction'].sudo()
    rules = Ded.rule_text()
    rp = Ded.rule_params()
    h, m = rp['work_start'].hour, rp['work_start'].minute
    grace = rules['grace_min']
    # بداية نظيفة (قرار المالك 17/9): السجل ما يعرضش أي يوم قبل سريان اللائحة
    rule_start = rp['start_date']
    if start_day < rule_start:
        start_day = rule_start
    Emp = env['hr.employee'].sudo()
    Att = env['hr.attendance'].sudo()
    emps = Emp.search([('active', '=', True), ('user_id', '!=', False)], order='name')
    ded_by_key = {}
    for dd in Ded.search([('employee_id', 'in', emps.ids), ('date', '>=', start_day),
                          ('state', '!=', 'cancelled')], order='date, id'):
        ded_by_key.setdefault((dd.employee_id.id, dd.date), []).append(dd)
    atts = Att.search([('employee_id', 'in', emps.ids),
                       ('check_in', '>=', start_utc)], order='check_in asc')
    first, last = {}, {}
    for a in atts:
        d = pytz.utc.localize(a.check_in).astimezone(tz).date()
        first.setdefault((a.employee_id.id, d), a)
        last[(a.employee_id.id, d)] = a
    day_list = []
    d = start_day
    while d <= today:
        if d.weekday() not in (4, 5):
            day_list.append(d)
        d += timedelta(days=1)
    rows, summary = [], []
    for e in emps:
        present = late = absent = early = 0
        ded_total = 0.0
        for d in day_list:
            a = first.get((e.id, d))
            b = last.get((e.id, d))
            deds = ded_by_key.get((e.id, d), [])
            day_amount = sum(x.amount for x in deds)
            ded_total += day_amount
            if any(x.dtype == 'early' for x in deds):
                early += 1
            late_min = 0
            if a and not e.attendance_exempt:
                ci = pytz.utc.localize(a.check_in).astimezone(tz)
                ws = tz.localize(datetime.combine(d, time(h, m)))
                late_min = max(0, int((ci - ws).total_seconds() // 60))
            is_absent = (not a) and (not e.attendance_exempt) and d < today
            if a:
                present += 1
                if late_min >= grace:
                    late += 1
            if is_absent:
                absent += 1
            rows.append({
                'emp_id': e.id, 'name': e.name,
                'date': d.isoformat(), 'day': d.strftime('%d/%m'),
                'check_in': _fmt(a.check_in) if a else False,
                'check_out': _fmt(b.check_out) if b and b.check_out else False,
                'late_min': late_min if late_min >= grace else 0,
                'exempt': bool(e.attendance_exempt),
                'absent': is_absent,
                'ded_amount': day_amount,
                'ded': [{'dtype': x.dtype, 'label': Ded.DTYPE_LABELS.get(x.dtype, x.dtype),
                         'amount': x.amount, 'state': x.state} for x in deds],
            })
        summary.append({'emp_id': e.id, 'name': e.name,
                        'exempt': bool(e.attendance_exempt),
                        'present': present, 'late': late, 'absent': absent,
                        'early': early, 'ded_total': ded_total})
    no_login = Emp.search([('active', '=', True), ('user_id', '=', False)], order='name')
    if not day_list:
        summary = []
    return {'days': days, 'from': start_day.isoformat(),
            'to': today.isoformat(), 'work_days': len(day_list),
            'starts': rule_start.isoformat(),
            'grace': grace, 'work_start': '%02d:%02d' % (h, m),
            'rules': rules,
            'rows': rows, 'summary': summary,
            'no_login': [x.name for x in no_login]}


class NurseryDashboard(http.Controller):

    @http.route('/nursery-dashboard', type='http', auth='user', website=False)
    def dash_page(self, **kw):
        if not _allowed():
            raise werkzeug.exceptions.Forbidden()
        mt = request.env.user._ensure_api_token()
        review_url = 'https://montessori-ksa.com/manage/#mt=%s' % mt
        page = DASH_PAGE.replace('__REVIEW_URL__', review_url)
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    @http.route('/nursery-gallery/<int:album_id>', type='http', auth='user', website=False)
    def gallery(self, album_id, **kw):
        u = request.env.user
        if not (u.has_group('nursery.group_nursery_teacher')
                or u.has_group('nursery.group_nursery_manager')
                or u.has_group('base.group_system')):
            raise werkzeug.exceptions.Forbidden()
        album = request.env['nursery.album'].sudo().browse(album_id)
        if not album.exists():
            raise werkzeug.exceptions.NotFound()
        import re as _re
        safe = _re.compile(r'^[A-Za-z0-9_-]+$')
        tiles = []
        for p in album.photo_ids:
            if p.drive_id and safe.match(p.drive_id):
                tiles.append(
                    '<a href="https://drive.google.com/file/d/%s/view" target="_blank" '
                    'rel="noopener"><img loading="lazy" '
                    'src="https://drive.google.com/thumbnail?id=%s&sz=w400"/></a>'
                    % (p.drive_id, p.drive_id))
        name = (album.name or '').replace('<', '').replace('>', '')
        page = GALLERY_PAGE.replace('__NAME__', name).replace('__TILES__', ''.join(tiles)) \
            .replace('__COUNT__', str(len(tiles)))
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Content-Security-Policy', "img-src https://drive.google.com data:;"),
        ])

    @http.route('/nursery-dashboard/data', type='json', auth='user')
    def dash_data(self, **kw):
        if not _allowed():
            raise werkzeug.exceptions.Forbidden()
        return _build_dashboard_data(request.env)

    @http.route('/api/dashboard', type='json', auth='public',
                methods=['POST'], csrf=False, cors='https://montessori-ksa.com')
    def api_dashboard(self, mt=None, **kw):
        """داشبورد الأونر على الموقع — بتوكن المدير/الأونر."""
        import re as _re
        valid = bool(mt and _re.match(r'^[0-9a-f]{32}$', mt))
        u = request.env['res.users'].sudo().search(
            [('nursery_api_token', '=', mt)], limit=1) if valid else None
        if not u or not (u.has_group('nursery.group_nursery_manager')
                         or u.has_group('base.group_system')):
            return {'error': 'unauthorized'}
        data = _build_dashboard_data(request.env)
        data['ok'] = True
        data['name'] = u.name
        return data

    @http.route('/api/manager/attendance', type='json', auth='public',
                methods=['POST'], csrf=False, cors='https://montessori-ksa.com')
    def api_manager_attendance(self, mt=None, days=14, **kw):
        """سجل حضور الموظفين لآخر N يوم عمل — للمديرة/الأونر بالتوكن.

        صف لكل (موظف × يوم): أول حضور، آخر انصراف، دقائق التأخير، غياب.
        الجمعة والسبت عطلة. اليوم الحالي لا يُحسب غياباً قبل انتهائه.
        """
        import re as _re
        valid = bool(mt and _re.match(r'^[0-9a-f]{32}$', mt))
        u = request.env['res.users'].sudo().search(
            [('nursery_api_token', '=', mt)], limit=1) if valid else None
        if not u or not (u.has_group('nursery.group_nursery_manager')
                         or u.has_group('base.group_system')):
            return {'error': 'unauthorized'}
        data = _attendance_report(request.env, days)
        data['ok'] = True
        return data

    @http.route('/api/manager/attendance/export', type='http', auth='public',
                methods=['GET'], csrf=False, cors=WEBSITE_ORIGIN)
    def api_manager_attendance_export(self, mt=None, days=14, **kw):
        """نفس سجل الحضور أعلاه بس كملف Excel — عشان المديرة تصدّره وقت ما تحب."""
        if not _manager_by_token(mt):
            return request.make_response(
                'unauthorized', headers=[('Content-Type', 'text/plain')], status=401)
        data = _attendance_report(request.env, days)
        book = Workbook()
        sheet = book.active
        sheet.title = 'حضور الموظفين'
        sheet.append(['الموظف', 'التاريخ', 'اليوم', 'حضور', 'انصراف',
                      'دقائق التأخير', 'غائب', 'الخصم (ر.س)', 'نوع الخصم', 'معفى من الحضور'])
        for r in data['rows']:
            sheet.append([
                r['name'], r['date'], r['day'],
                r['check_in'] or '', r['check_out'] or '',
                r['late_min'], 'نعم' if r['absent'] else 'لا',
                r['ded_amount'], '، '.join(x['label'] for x in r['ded']),
                'نعم' if r['exempt'] else 'لا',
            ])
        sheet.freeze_panes = 'A2'
        sheet.auto_filter.ref = sheet.dimensions
        for column_cells in sheet.columns:
            width = max((len(str(c.value)) for c in column_cells if c.value is not None), default=8)
            sheet.column_dimensions[column_cells[0].column_letter].width = min(max(width + 2, 10), 28)
        summary_sheet = book.create_sheet('الملخص')
        summary_sheet.append(['الموظف', 'أيام الحضور', 'أيام التأخير', 'أيام الغياب',
                              'انصراف مبكر', 'إجمالي الخصم (ر.س)', 'معفى من الحضور'])
        for r in data['summary']:
            summary_sheet.append([
                r['name'], r['present'], r['late'], r['absent'],
                r['early'], r['ded_total'],
                'نعم' if r['exempt'] else 'لا',
            ])
        summary_sheet.freeze_panes = 'A2'
        summary_sheet.auto_filter.ref = summary_sheet.dimensions
        for column_cells in summary_sheet.columns:
            width = max((len(str(c.value)) for c in column_cells if c.value is not None), default=8)
            summary_sheet.column_dimensions[column_cells[0].column_letter].width = min(max(width + 2, 10), 28)
        output = io.BytesIO()
        book.save(output)
        output.seek(0)
        filename = 'attendance-%s-to-%s.xlsx' % (data['from'], data['to'])
        return request.make_response(output.getvalue(), headers=[
            ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('Content-Disposition', 'attachment; filename="%s"' % filename),
            ('Cache-Control', 'no-store'),
        ])


def _sheet_count(v, name):
    """عدد من صف الشيت كما هو (int)؛ None لو الحمولة ما كتبتش المفتاح أصلاً
    (أو كتبته بقيمة مش رقمية) — مش صفر كاذب."""
    val = v.get(name) if isinstance(v, dict) else None
    if val in (None, ''):
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def _sheet_float(v, name):
    """رقم من ملخص الشيت (float)؛ None لو المفتاح مش موجود أصلاً — مش صفر كاذب."""
    val = v.get(name) if isinstance(v, dict) else None
    if val in (None, ''):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _merge_ext_fin(by_month, ext, START, _slot, month_param=None):
    """دمج صفوف `nursery.ext_fin` (ملخص شيت راندا الشهري) في by_month.

    أي شهر ≥ START موجود في ext يكون هو المرجع: بنكتب كل مفاتيح العقد
    بقيم افتراضية آمنة لو مفتاح ناقص (float للمبالغ، int للأعداد).
    month_param (اختياري): دالة ym → dict بملخص الشهر نفسه
    (`nursery.excel_month_<ym>`)؛ المستورد بيكتبه مع صف ext في نفس العملية،
    وبنكمّل منه بس المفاتيح اللي صف ext ما كتبهاش (الصفوف القديمة كتبت
    expected_salaries هناك بس مثلاً). صف ext دايمًا له الأولوية.

    المفاتيح اللي ملهاش مفتاح قديم بنفس المعنى (expected_salaries +
    الأعداد الثلاثة student_count / paid_students / unpaid_students) بتطلع
    None لو مفيش مصدر كتبها — مش صفر كاذب: الواجهة بتقرا None كـ«ناقص»
    وترجع للعدّ الحيّ من السجلات، لكن الصفر بتعرضه كرقم حقيقي (10/10: كان
    بيعرض «الدافعين 0 / غير الدافعين 0» لأكتوبر لأن الصف القديم ما فيهوش
    المفتاحين). نفس القيم بالظبط بتتكتب في sheet تحت عشان المصدرين ما يختلفوش.
    بترجع {ym: {'explicit_net': bool, 'sheet': {...}}} للشهور اللي اندمجت:
    - explicit_net: الشيت كتب «الصافي» بنفسه (حتى لو صفر) فممنوع يتحسب تاني.
    - sheet: أعداد الطلاب زي ما الشيت قالها (نفس قيم صف by_month).
    """
    merged = {}
    for k, v in (ext.items() if isinstance(ext, dict) else []):
        if k >= START and isinstance(v, dict):
            src = {}
            if month_param is not None:
                try:
                    mp = month_param(k)
                    if isinstance(mp, dict):
                        src.update(mp)
                except Exception:
                    pass
            src.update(v)
            v = src
            current = _slot(k)
            payment_rows = v.get('payment_rows')
            current.update({
                'ym': k,
                'income': float(v.get('income', 0) or 0),
                'student_income': float(v.get('student_income', v.get('income', 0)) or 0),
                'extra_income': float(v.get('extra_income', 0) or 0),
                # إجمالي المحصّل (A5)؛ الحمولة القديمة ما فيهاش المفتاح،
                # ودخل الطلاب هو نفس الرقم بالضبط عند المستورد.
                'collected': float(v.get('collected', v.get('student_income', v.get('income', 0))) or 0),
                'salaries': float(v.get('salaries', 0) or 0),
                # الرواتب المتوقعة (D5): مفيش مفتاح قديم بنفس المعنى → None لو ناقص.
                'expected_salaries': _sheet_float(v, 'expected_salaries'),
                # الرواتب المصروفة (D9) = مفتاح salaries القديم (نفس المعنى).
                'salaries_paid': float(v.get('salaries_paid', v.get('salaries', 0)) or 0),
                'other': float(v.get('other', 0) or 0),
                'expenses': float(v.get('expenses', v.get('other', 0)) or 0),
                'cash': float(v.get('cash', 0) or 0),
                'transfer': float(v.get('transfer', 0) or 0),
                'books': float(v.get('books', 0) or 0),
                'books_due_total': float(v.get('books_due_total', 0) or 0),
                'books_paid_total': float(v.get('books_paid_total', 0) or 0),
                'books_remaining_total': float(v.get('books_remaining_total', 0) or 0),
                # This is the workbook's explicit remaining total.
                # Do not derive it from billed or collected amounts.
                'remaining_total': float(v.get('remaining_total', 0) or 0),
                # أعداد الشيت (G3/G5/G7): int لو الشيت عدّها، None لو المفتاح ناقص.
                'student_count': _sheet_count(v, 'student_count'),
                'paid_students': _sheet_count(v, 'paid_students'),
                'unpaid_students': _sheet_count(v, 'unpaid_students'),
                'payment_rows': (int(payment_rows)
                                 if payment_rows is not None else None),
                'on_hand_randa': float(v.get('on_hand_randa', 0) or 0),
                'randa_on_hand': float(v.get('randa_on_hand', 0) or 0),
                'delta': float(v.get('delta', 0) or 0),
                'opening_balance': float(v.get('opening_balance', 0) or 0),
                'opening_source': v.get('opening_source') or '',
                'expenses_paid_out': float(v.get('expenses_paid_out', 0) or 0),
                'cash_closing': float(v.get('cash_closing', v.get('on_hand_randa', 0)) or 0),
                'cash_after_salaries': float(v.get('cash_after_salaries', 0) or 0),
                'net': float(v.get('net', 0) or 0),
            })
            merged[k] = {
                'explicit_net': v.get('net') is not None,
                'sheet': {
                    'ym': k,
                    'student_count': current['student_count'],
                    'paid_students': current['paid_students'],
                    'unpaid_students': current['unpaid_students'],
                },
            }
    return merged


def _build_dashboard_data(env):
    if True:
        tz = _tz()
        now_local = datetime.now(pytz.utc).astimezone(tz)
        today = now_local.date()
        Pay = env['nursery.fee.payment'].sudo()
        Exp = env['nursery.expense'].sudo()
        Stu = env['nursery.student'].sudo()
        Att = env['hr.attendance'].sudo()
        SAtt = env['nursery.attendance'].sudo()
        Ded = env['nursery.deduction'].sudo()
        Emp = env['hr.employee'].sudo()

        # ---- المال (على طريقة تطبيق الحسابات: إيرادات − مرتبات − مصاريف = صافي) ----
        # البداية الصح = يونيو 2026؛ نتجاهل أي بيانات أقدم (النظام القديم).
        icp0 = env['ir.config_parameter'].sudo()
        START = icp0.get_param('nursery.fin_start', '2026-06')
        Sal = env['nursery.salary'].sudo()
        pays = Pay.search([])
        exps = Exp.search([])
        sals = Sal.search([])
        pays_today = pays.filtered(lambda p: p.date == today)
        by_month = {}   # month -> {income, salaries, other}

        def _slot(k):
            # الافتراضيات بتغطّي كل مفاتيح عقد الشيت (15 قيمة ملخص راندا +
            # مفاتيح الرسم القديمة) عشان أي شهر بلا استيراد إكسل يطلع بنفس الشكل.
            by_month.setdefault(k, {
                'income': 0.0, 'student_income': 0.0, 'extra_income': 0.0,
                'collected': 0.0,
                'salaries': 0.0, 'expected_salaries': 0.0, 'salaries_paid': 0.0,
                'other': 0.0, 'expenses': 0.0, 'cash': 0.0, 'transfer': 0.0,
                'books': 0.0, 'books_due_total': 0.0, 'books_paid_total': 0.0,
                'books_remaining_total': 0.0, 'remaining_total': 0.0,
                'student_count': 0, 'paid_students': 0, 'unpaid_students': 0,
                'payment_rows': None,
                'on_hand_randa': 0.0, 'cash_closing': 0.0, 'cash_after_salaries': 0.0,
                'randa_on_hand': 0.0, 'delta': 0.0,
                'opening_balance': 0.0, 'opening_source': '',
                'expenses_paid_out': 0.0, 'net': 0.0,
            })
            return by_month[k]

        for p in pays:
            if p.date:
                k = p.date.strftime('%Y-%m')
                if k >= START:
                    _slot(k)['income'] += p.amount
                    _slot(k)['student_income'] += p.amount
        for e in exps:
            if e.date and e.value > 0:
                k = e.date.strftime('%Y-%m')
                if k >= START:
                    _slot(k)['other'] += e.value
        for s in sals:
            # المرتبات ليس لها شهر صريح → ننسبها لشهر الصرف إن وُجد، وإلا لشهر البداية
            k = s.paid_date.strftime('%Y-%m') if s.paid_date else START
            if k < START:
                k = START
            _slot(k)['salaries'] += (s.expected or 0.0)

        # ---- مزامنة تطبيق الحسابات (dev2): أي شهر ≥ البداية موجود هناك يكون هو المرجع ----
        def _month_param(k):
            # ملخص الشهر نفسه (`nursery.excel_month_<ym>`) لتكملة المفاتيح اللي
            # صف ext القديم ما كتبهاش؛ أي خطأ هنا بيتلقط جوّه _merge_ext_fin لكل شهر لوحده.
            raw = icp0.get_param('nursery.excel_month_%s' % k, '') or ''
            return json.loads(raw) if raw else {}

        ext_months = {}
        try:
            ext = json.loads(icp0.get_param('nursery.ext_fin', '') or '{}')
            ext_months = _merge_ext_fin(by_month, ext, START, _slot, _month_param)
        except Exception:
            pass

        # الصافي القديم (دخل − مرتبات − مصاريف) للشهور اللي ما جاتش من الشيت بس؛
        # لو الشيت كتب «الصافي» صراحةً (حتى لو صفر) بنسيبه زي ما هو.
        for k, v in by_month.items():
            if not ext_months.get(k, {}).get('explicit_net'):
                v['net'] = v['income'] - v['salaries'] - v['other']

        months = sorted(by_month.keys())[-9:]
        income_total = sum(v['income'] for v in by_month.values())
        salary_total = sum(v['salaries'] for v in by_month.values())
        expense_total = sum(v['other'] for v in by_month.values())   # مصاريف أخرى (غير المرتبات)
        net_total = income_total - salary_total - expense_total

        # ---- الطلاب والدفع ----
        # 15/9: كان بيفضّل رقم مجمّد من ملخص آخر استيراد إكسل (excel_summary
        # .student_count) على العدّ الحيّ، ويقصر العدّ على الصفوف اللي ليها
        # رقم تسلسلي بس. النتيجة: الكارت فضل عالق على 77 رغم إن سجلات
        # nursery.student النشطة الحقيقية بقت 79 (مطابقة تماماً لعدّاد الشيت
        # الديناميكي الجديد اللي بيعدّ أي طالب مُسمّى — بسيريال أو من غيره).
        # دلوقتي العدّ حيّ دايماً، بنفس منطق الشيت: كل طالب نشط بيتحسب.
        students = Stu.search([('active', '=', True)])
        excel_summary = by_month.get(today.strftime('%Y-%m'), {})
        # أعداد الشهر الحالي زي ما الشيت قالها (عدد الطلاب/الدافعين/غير الدافعين)
        # لكروت الطلاب؛ None لو مفيش صف إكسل للشهر والواجهة ترجع للعدّ الحيّ.
        students_sheet = ext_months.get(today.strftime('%Y-%m'), {}).get('sheet')
        roster_student_count = len(students)
        paid_student_count = len(students.filtered('paid'))
        overdue = []
        for s in students:
            if s.paid_until and s.paid_until < today:
                overdue.append({'name': s.name, 'fees': s.fees,
                                'days': (today - s.paid_until).days})
        overdue.sort(key=lambda r: -r['days'])

        # ---- حضور الأطفال اليوم + آخر 14 يوم ----
        satt_today = SAtt.search([('date', '=', today)])
        present_ids = satt_today.filtered(
            lambda a: a.status == 'present').mapped('student_id').ids
        absent_names = [s.name for s in students if s.id not in present_ids] \
            if satt_today else []
        att14 = []
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            if d.weekday() in (4, 5):
                continue
            cnt = SAtt.search_count([('date', '=', d), ('status', '=', 'present')])
            att14.append({'label': d.strftime('%d/%m'), 'value': cnt})

        # ---- الموظفين اليوم ----
        day_start_utc = tz.localize(datetime.combine(today, time(0, 0))) \
            .astimezone(pytz.utc).replace(tzinfo=None)
        rp = Ded.rule_params()
        grace = rp['late_tiers'][0][0] if rp['late_tiers'] else 10
        pre_rule = today < rp['start_date']  # قبل الأحد 20/9: نعرض الأوقات بلا حكم تأخير
        work_start = tz.localize(datetime.combine(today, rp['work_start']))
        today_ded = {}
        for dd in Ded.search([('date', '=', today), ('state', '!=', 'cancelled')]):
            today_ded.setdefault(dd.employee_id.id, []).append(dd)
        staff_rows = []
        late_today = 0
        for emp in Emp.search([('user_id', '!=', False)]):
            first = Att.search([('employee_id', '=', emp.id),
                                ('check_in', '>=', day_start_utc)],
                               limit=1, order='check_in asc')
            late_min = 0
            if first and not emp.attendance_exempt and not pre_rule:
                ci_local = pytz.utc.localize(first.check_in).astimezone(tz)
                late_min = max(0, int((ci_local - work_start).total_seconds() // 60))
                if late_min >= grace:
                    late_today += 1
            deds = today_ded.get(emp.id, [])
            staff_rows.append({
                'name': emp.name,
                'exempt': emp.attendance_exempt,
                'pre_rule': pre_rule,
                'check_in': _fmt(first.check_in) if first else False,
                'check_out': _fmt(first.check_out) if first and first.check_out else False,
                'late_min': late_min if late_min >= grace else 0,
                'ded_amount': sum(x.amount for x in deds),
                'ded': [{'dtype': x.dtype, 'label': Ded.DTYPE_LABELS.get(x.dtype, x.dtype),
                         'amount': x.amount} for x in deds],
            })

        # ---- خصومات الشهر ----
        month_start = today.replace(day=1)
        deds = Ded.search([('date', '>=', month_start),
                           ('state', '!=', 'cancelled')])
        ded_by_emp = {}
        for d in deds:
            r = ded_by_emp.setdefault(d.employee_id.name,
                                      {'absences': 0, 'lates': 0, 'earlies': 0,
                                       'days': 0.0, 'amount': 0.0})
            if d.dtype in ('absence', 'absence_auth'):
                r['absences'] += 1
            elif d.dtype == 'late':
                r['lates'] += 1
            elif d.dtype == 'early':
                r['earlies'] += 1
            r['days'] += d.days
            r['amount'] += d.amount

        return {
            'money': {
                'income_total': income_total,
                'salary_total': salary_total,
                'expense_total': expense_total,
                'net': net_total,
                'income_today': sum(pays_today.mapped('amount')),
                'count_today': len(pays_today),
                'by_month': [{'label': k, **by_month[k]} for k in months],
                'excel_summary': excel_summary,
            },
            'students': {
                'total': roster_student_count,
                'paid': paid_student_count,
                'overdue_count': len(overdue),
                'overdue': overdue[:12],
                'sheet': students_sheet,
            },
            'att_today': {
                'marked': bool(satt_today),
                'present': len(present_ids),
                'absent_names': absent_names[:15],
            },
            'att_14': att14,
            'staff': {
                'today': staff_rows,
                'late_today': late_today,
                'deductions': [{'name': k, **v} for k, v in ded_by_emp.items()],
                'rules': Ded.rule_text(),
            },
        }


def _ads_block(env):
    """حالة الإعلانات المخزّنة + عمرها. stale=True لو مر أكثر من ٣ ساعات."""
    raw = env['ir.config_parameter'].sudo().get_param('nursery.ads_status')
    if not raw:
        return {'configured': False}
    try:
        d = json.loads(raw)
    except Exception:
        return {'configured': False}
    stale = True
    try:
        tz = pytz.timezone(NURSERY_TZ)
        seen = tz.localize(datetime.strptime(d.get('received_at'), '%Y-%m-%d %H:%M'))
        stale = (datetime.now(tz) - seen).total_seconds() > 3 * 3600
    except Exception:
        pass
    d['configured'] = True
    d['stale'] = stale
    # 19/8: سكربت الجامع بيقرا حالة الحملات وهو أعمى عن إيقاف الحساب نفسه —
    # يوم كامل بصرف ونقرات صفر مع حملة «مفعّلة» = مؤشر إيقاف/مشكلة حساب،
    # والقاعدة الثابتة: ممنوع الكارت يقول «كل الحملات سليمة» وهو مش متأكد.
    try:
        camps = d.get('campaigns') or []
        if d.get('ok') and camps and all(
                not (c.get('cost') or 0) and not (c.get('clicks') or 0)
                for c in camps):
            d['ok'] = False
            probs = list(d.get('problems') or [])
            probs.append('صرف ونقرات صفر رغم حملة مفعّلة — راجع حالة الحساب (إيقاف/توثيق؟)')
            d['problems'] = probs
    except Exception:
        pass
    return d


class NurseryAdsStatus(http.Controller):
    """استقبال حالة إعلانات Google من سكربت يعمل داخل حساب Ads نفسه.
    السكربت يرسل كل ساعة؛ لا نحتاج developer token ولا موافقة API."""

    @http.route('/api/ads/ingest', type='http', auth='public',
                methods=['POST'], csrf=False, save_session=False)
    def api_ads_ingest(self, **kw):
        ICP = request.env['ir.config_parameter'].sudo()
        secret = (ICP.get_param('nursery.ads_ingest_key') or '').strip()
        given = (request.httprequest.headers.get('X-Ads-Key') or '').strip()
        if not secret or given != secret:
            raise werkzeug.exceptions.Forbidden()
        try:
            raw = request.httprequest.get_data(as_text=True) or '{}'
            payload = json.loads(raw)
            assert isinstance(payload, dict)
        except Exception:
            return request.make_response('bad json', status=400)
        payload['received_at'] = datetime.now(
            pytz.timezone(NURSERY_TZ)).strftime('%Y-%m-%d %H:%M')
        ICP.set_param('nursery.ads_status', json.dumps(payload, ensure_ascii=False))
        return request.make_response('ok')

    @http.route('/api/gstatus/ingest', type='http', auth='public',
                methods=['POST'], csrf=False, save_session=False)
    def api_gstatus_ingest(self, **kw):
        """استقبال حالة منتجات جوجل من جامع يعمل على السيرفر.
        الجسم: {"section": "ga", "data": {...}} — يُخزَّن كل قسم مستقلاً."""
        ICP = request.env['ir.config_parameter'].sudo()
        secret = (ICP.get_param('nursery.ads_ingest_key') or '').strip()
        given = (request.httprequest.headers.get('X-Ads-Key') or '').strip()
        if not secret or given != secret:
            raise werkzeug.exceptions.Forbidden()
        try:
            body = json.loads(request.httprequest.get_data(as_text=True) or '{}')
            section = str(body.get('section') or '').strip()
            data = body.get('data')
            assert section and section.isalnum() and isinstance(data, dict)
        except Exception:
            return request.make_response('bad payload', status=400)
        data['received_at'] = datetime.now(
            pytz.timezone(NURSERY_TZ)).strftime('%Y-%m-%d %H:%M')
        ICP.set_param('nursery.gstatus_' + section,
                      json.dumps(data, ensure_ascii=False))

        # النقرات: نُثبّت العدّ اليومي في جدول دائم قبل أن يتدوّر سجلّ nginx
        if section == 'adclicks':
            self._store_clicks(data)
        return request.make_response('ok')

    def _store_clicks(self, data):
        """تخزين تفصيل اليوم/الحملة. الجامع يرسل إجمالي كل حملة عبر النافذة
        كاملة، وتفصيل الأيام إجمالاً — فنحتاج التفصيل المزدوج من `daily`."""
        Click = request.env['nursery.ad.click'].sudo()
        for row in (data.get('daily') or []):
            try:
                day = str(row.get('day') or '').strip()
                camp = str(row.get('campaign') or '').strip()
                n = int(row.get('clicks') or 0)
                if not day or not camp:
                    continue
                Click.record(day, camp, n)
            except Exception:
                continue

    def _clicks_history(self, days=30):
        """تاريخ النقرات من الجدول الدائم — مجمّعاً باليوم وبالحملة."""
        Click = request.env['nursery.ad.click'].sudo()
        since = (datetime.now(pytz.timezone(NURSERY_TZ)).date()
                 - timedelta(days=days))
        recs = Click.search([('day', '>=', since.strftime('%Y-%m-%d'))])
        by_day, by_camp = {}, {}
        for r in recs:
            d = r.day.strftime('%Y-%m-%d')
            by_day[d] = by_day.get(d, 0) + r.clicks
            by_camp[r.campaign] = by_camp.get(r.campaign, 0) + r.clicks
        return {
            'by_day': [{'day': d, 'clicks': by_day[d]} for d in sorted(by_day)],
            'campaigns': [{'id': c, 'clicks': n} for c, n in
                          sorted(by_camp.items(), key=lambda kv: -kv[1])],
            'total': sum(by_day.values()),
            'days': len(by_day),
        }

    @http.route('/api/google/status', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE_ORIGIN)
    def api_google_status(self, mt=None, **kw):
        """كل حالات منتجات جوجل في نداء واحد — لصفحة /google/."""
        import re as _re
        valid = bool(mt and _re.match(r'^[0-9a-f]{32}$', mt))
        u = request.env['res.users'].sudo().search(
            [('nursery_api_token', '=', mt)], limit=1) if valid else None
        if not u or not (u.has_group('nursery.group_nursery_manager')
                         or u.has_group('base.group_system')):
            return {'ok': False, 'error': 'unauthorized'}
        ICP = request.env['ir.config_parameter'].sudo()
        out = {'ok': True, 'name': u.name}
        out['ads'] = _ads_block(request.env)
        for key, section in (('nursery.gstatus_ga', 'ga'),
                             ('nursery.gstatus_gsc', 'gsc'),
                             ('nursery.gstatus_cloud', 'cloud'),
                             ('nursery.gstatus_drive', 'drive'),
                             ('nursery.gstatus_gbp', 'gbp'),
                             ('nursery.gstatus_adclicks', 'adclicks'),
                             # مين على الموقع دلوقتي — من سجلات nginx
                             ('nursery.gstatus_visitors', 'visitors')):
            raw = ICP.get_param(key)
            try:
                out[section] = json.loads(raw) if raw else None
            except Exception:
                out[section] = None
        try:
            out['clicks_history'] = self._clicks_history()
        except Exception:
            out['clicks_history'] = None
        return out
