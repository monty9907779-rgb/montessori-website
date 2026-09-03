# -*- coding: utf-8 -*-
from datetime import datetime, time, timedelta

import json
import pytz
import werkzeug.exceptions

from odoo import fields, http
from odoo.http import request

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
<title>داشبورد الحضانة</title>
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
<h1>📊 داشبورد حضانة مونتيسوري</h1>
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
  let h='<table><tr><th>الموظفة</th><th>غياب</th><th>تأخير</th><th>أيام الخصم</th></tr>';
  rows.forEach(r=>{ h+='<tr><td>'+esc(r.name)+'</td><td>'+r.absences+'</td><td>'+r.lates+'</td><td><span class="tag t-amber">'+r.days+'</span></td></tr>'; });
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
            by_month.setdefault(k, {'income': 0.0, 'salaries': 0.0, 'other': 0.0})
            return by_month[k]

        for p in pays:
            if p.date:
                k = p.date.strftime('%Y-%m')
                if k >= START:
                    _slot(k)['income'] += p.amount
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
        try:
            ext = json.loads(icp0.get_param('nursery.ext_fin', '') or '{}')
            for k, v in (ext.items() if isinstance(ext, dict) else []):
                if k >= START and isinstance(v, dict):
                    by_month[k] = {
                        'income': float(v.get('income', 0) or 0),
                        'salaries': float(v.get('salaries', 0) or 0),
                        'other': float(v.get('other', 0) or 0),
                    }
        except Exception:
            pass

        for v in by_month.values():
            v['net'] = v['income'] - v['salaries'] - v['other']

        months = sorted(by_month.keys())[-9:]
        income_total = sum(v['income'] for v in by_month.values())
        salary_total = sum(v['salaries'] for v in by_month.values())
        expense_total = sum(v['other'] for v in by_month.values())   # مصاريف أخرى (غير المرتبات)
        net_total = income_total - salary_total - expense_total

        # ---- الطلاب والدفع ----
        students = Stu.search([])
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
        icp = env['ir.config_parameter'].sudo()
        try:
            h, m = (int(x) for x in (icp.get_param('nursery.work_start', '08:00') or '08:00').split(':'))
        except ValueError:
            h, m = 8, 0
        work_start = tz.localize(datetime.combine(today, time(h, m)))
        staff_rows = []
        late_today = 0
        for emp in Emp.search([('user_id', '!=', False)]):
            first = Att.search([('employee_id', '=', emp.id),
                                ('check_in', '>=', day_start_utc)],
                               limit=1, order='check_in asc')
            late_min = 0
            if first and not emp.attendance_exempt:
                ci_local = pytz.utc.localize(first.check_in).astimezone(tz)
                late_min = max(0, int((ci_local - work_start).total_seconds() // 60))
                if late_min >= 10:
                    late_today += 1
            staff_rows.append({
                'name': emp.name,
                'exempt': emp.attendance_exempt,
                'check_in': _fmt(first.check_in) if first else False,
                'check_out': _fmt(first.check_out) if first and first.check_out else False,
                'late_min': late_min if late_min >= 10 else 0,
            })

        # ---- خصومات الشهر ----
        month_start = today.replace(day=1)
        deds = Ded.search([('date', '>=', month_start),
                           ('state', '!=', 'cancelled')])
        ded_by_emp = {}
        for d in deds:
            r = ded_by_emp.setdefault(d.employee_id.name,
                                      {'absences': 0, 'lates': 0, 'days': 0.0})
            if d.dtype in ('absence', 'absence_auth'):
                r['absences'] += 1
            elif d.dtype == 'late':
                r['lates'] += 1
            r['days'] += d.days

        return {
            'money': {
                'income_total': income_total,
                'salary_total': salary_total,
                'expense_total': expense_total,
                'net': net_total,
                'income_today': sum(pays_today.mapped('amount')),
                'count_today': len(pays_today),
                'by_month': [{'label': k, **by_month[k]} for k in months],
            },
            'students': {
                'total': len(students),
                'paid': len(students.filtered('paid')),
                'overdue_count': len(overdue),
                'overdue': overdue[:12],
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
            },
        }
