# -*- coding: utf-8 -*-
import json
import math
import re

import werkzeug.exceptions
from markupsafe import escape as html_escape

from odoo import fields, http
from odoo.http import request


def _require_internal():
    """App endpoints are for staff only — block portal/public users
    (sudo() below would otherwise bypass ACLs for them)."""
    if not request.env.user._is_internal():
        raise werkzeug.exceptions.Forbidden()


def _is_teacher():
    """مدرسة أو أعلى — العاملة ماتشوفش بيانات الأطفال."""
    u = request.env.user
    return (u.has_group('nursery.group_nursery_teacher')
            or u.has_group('nursery.group_nursery_manager')
            or u.has_group('base.group_system'))

# geofence defaults (overridable via ir.config_parameter)
DEFAULT_LAT = 21.5795281
DEFAULT_LNG = 39.194829
DEFAULT_RADIUS_M = 400


def _geo_params(env):
    icp = env['ir.config_parameter'].sudo()
    try:
        lat = float(icp.get_param('nursery.geo_lat', DEFAULT_LAT))
        lng = float(icp.get_param('nursery.geo_lng', DEFAULT_LNG))
        radius = float(icp.get_param('nursery.geo_radius', DEFAULT_RADIUS_M))
    except (TypeError, ValueError):
        lat, lng, radius = DEFAULT_LAT, DEFAULT_LNG, DEFAULT_RADIUS_M
    return lat, lng, radius


def _distance_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _employee(env):
    return env['hr.employee'].sudo().search(
        [('user_id', '=', env.user.id)], limit=1)


def _open_attendance(env, employee):
    return env['hr.attendance'].sudo().search(
        [('employee_id', '=', employee.id), ('check_out', '=', False)],
        limit=1, order='check_in desc')


def _wa_phone(phone):
    """Normalize a Saudi phone to wa.me format (9665xxxxxxxx)."""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', phone)
    if digits.startswith('00'):
        digits = digits[2:]
    if digits.startswith('05'):
        digits = '966' + digits[1:]
    elif digits.startswith('5') and len(digits) == 9:
        digits = '966' + digits
    return digits


PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>
<meta name="theme-color" content="#14532d"/>
<link rel="manifest" href="/nursery-app/manifest.webmanifest"/>
<link rel="apple-touch-icon" href="/nursery/static/description/icon.png"/>
<title>حضانة مونتيسوري</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, "Segoe UI", Tahoma, sans-serif; }
  body { background: #f0f7f2; min-height: 100vh; display: flex; flex-direction: column; }
  header { background: #14532d; color: #fff; padding: 12px 16px; display: flex; align-items: center; gap: 10px; position: sticky; top: 0; z-index: 5; }
  header img { width: 40px; height: 40px; border-radius: 10px; background:#fff; padding:3px; }
  header .t { flex: 1; }
  header h1 { font-size: 17px; }
  header .u { font-size: 12px; opacity: .85; }
  #back { display: none; background: rgba(255,255,255,.15); border: 0; color: #fff; border-radius: 10px;
          padding: 8px 14px; font-size: 15px; }
  main { flex: 1; padding: 16px; max-width: 480px; margin: 0 auto; width: 100%; padding-bottom: 40px; }
  .status { background: #fff; border-radius: 14px; padding: 14px; text-align: center;
            box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 14px; font-size: 15px; }
  .status b { color: #14532d; }
  #punch { width: 100%; padding: 20px; border: 0; border-radius: 16px; font-size: 21px;
           font-weight: 700; color: #fff; background: #16a34a; box-shadow: 0 3px 8px rgba(0,0,0,.15); }
  #punch.out { background: #dc2626; }
  #punch:disabled { background: #9ca3af; }
  #msg { margin-top: 10px; text-align: center; font-size: 14px; color: #374151; min-height: 20px; white-space: pre-line; }
  .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 18px; }
  .tile { background: #fff; border: 0; border-radius: 12px; padding: 16px 8px; text-align: center;
          color: #14532d; font-size: 15px; font-weight: 600; box-shadow: 0 1px 3px rgba(0,0,0,.06); cursor: pointer; }
  .tile span { display: block; font-size: 26px; margin-bottom: 6px; }
  .card { background: #fff; border-radius: 12px; padding: 14px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,.06); font-size: 14px; }
  .card .row { display: flex; justify-content: space-between; margin: 3px 0; }
  .card .row .l { color: #6b7280; }
  .card h3 { font-size: 15px; color: #14532d; margin-bottom: 6px; }
  .empty { text-align: center; color: #9ca3af; padding: 30px 10px; font-size: 15px; }
  .badge { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 12px; }
  .b-red { background: #fee2e2; color: #b91c1c; }
  .b-amber { background: #fef3c7; color: #b45309; }
  .b-green { background: #dcfce7; color: #15803d; }
  .b-gray { background: #f3f4f6; color: #4b5563; }
  .stud { display: flex; align-items: center; gap: 10px; }
  .stud .info { flex: 1; }
  .stud .info small { color: #9ca3af; }
  .wa { background: #25d366; color: #fff; border: 0; border-radius: 10px; padding: 8px 12px;
        font-size: 13px; font-weight: 700; text-decoration: none; display: inline-block; }
  .chatbtn { background: #14532d; color: #fff; border: 0; border-radius: 10px; padding: 8px 12px; font-size: 13px; font-weight: 700; }
  #thread { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
  .bubble { max-width: 82%; padding: 10px 12px; border-radius: 14px; font-size: 14px; white-space: pre-line; }
  .bubble.me { background: #dcfce7; align-self: flex-start; border-bottom-right-radius: 4px; }
  .bubble.them { background: #fff; align-self: flex-end; border-bottom-left-radius: 4px; }
  .bubble small { display: block; color: #9ca3af; font-size: 11px; margin-top: 4px; }
  .sendrow { display: flex; gap: 8px; position: sticky; bottom: 10px; }
  .sendrow input { flex: 1; border: 1px solid #d1d5db; border-radius: 12px; padding: 12px; font-size: 15px; }
  .sendrow button { background: #14532d; color: #fff; border: 0; border-radius: 12px; padding: 0 18px; font-size: 18px; }
  .search { width: 100%; border: 1px solid #d1d5db; border-radius: 12px; padding: 12px; font-size: 15px; margin-bottom: 12px; }
  .total { background: #14532d; color: #fff; border-radius: 12px; padding: 14px; text-align: center; margin-bottom: 12px; font-size: 15px; }
</style>
</head>
<body>
<header>
  <img src="/nursery/static/description/icon.png" alt="logo"/>
  <div class="t"><h1 id="title">حضانة مونتيسوري</h1><div class="u">__USER__</div></div>
  <button id="back">◀ رجوع</button>
</header>
<main id="main"></main>
<script>
const M = document.getElementById('main');
const backBtn = document.getElementById('back');
const title = document.getElementById('title');
let chatStudent = null;

async function rpc(path, params) {
  const r = await fetch(path, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: params || {}})
  });
  const d = await r.json();
  if (d.error) throw new Error((d.error.data && d.error.data.message) || d.error.message);
  return d.result;
}
function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }
function nav(page) { location.hash = page; }
window.addEventListener('hashchange', route);
backBtn.addEventListener('click', () => { history.length > 1 ? history.back() : nav('home'); });

function guard(fn) {
  return async function() {
    try { await fn.apply(null, arguments); }
    catch (e) { M.innerHTML = '<div class="empty">❌ حصل خطأ: ' + esc(e.message) + '<br/><small>جربي تاني أو ارجعي للرئيسية</small></div>'; }
  };
}

function route() {
  const h = (location.hash || '#home').slice(1);
  backBtn.style.display = h === 'home' ? 'none' : 'block';
  if (h === 'home') return home();
  if (h === 'salaries') return guard(salaries)();
  if (h === 'classes') return guard(classes)();
  if (h === 'chat') return guard(chatList)();
  if (h.startsWith('thread-')) {
    const sid = parseInt(h.slice(7));
    if (isNaN(sid)) return nav('chat');
    return guard(thread)(sid);
  }
  if (h === 'deductions') return guard(deductions)();
  home();
}

/* ---------- HOME ---------- */
async function home() {
  title.textContent = 'حضانة مونتيسوري';
  M.innerHTML = '<div class="status" id="status">... جاري التحميل</div>' +
    '<button id="punch" disabled>...</button><div id="msg"></div>' +
    '<div class="grid" id="tiles">' +
    '<button class="tile" onclick="nav(\\'salaries\\')"><span>💰</span>راتبي</button>' +
    '<button class="tile teach" onclick="nav(\\'classes\\')" style="display:none"><span>🏫</span>الفصول</button>' +
    '<button class="tile teach" onclick="nav(\\'chat\\')" style="display:none"><span>💬</span>شات أولياء الأمور</button>' +
    '<button class="tile" onclick="nav(\\'deductions\\')"><span>⏰</span>خصوماتي</button>' +
    '</div>';
  const btn = document.getElementById('punch');
  const msg = document.getElementById('msg');
  const statusBox = document.getElementById('status');
  function render(state) {
    if (state.error) {
      statusBox.innerHTML = '⚠️ حسابك مش مربوط بملف موظف — كلمي الإدارة';
      btn.disabled = true;
      return;
    }
    if (state.exempt) {
      statusBox.innerHTML = '✅ أنت <b>معفى من تسجيل الحضور</b>';
      btn.style.display = 'none';
      if (state.is_teacher) document.querySelectorAll('.tile.teach').forEach(t => t.style.display = '');
      return;
    }
    statusBox.innerHTML = state.checked_in
      ? 'انتي الآن <b>مسجلة حضور</b> من الساعة <b>' + esc(state.since) + '</b>'
      : 'انتي الآن <b>خارج الدوام</b>' + (state.last ? '<br/><small>آخر انصراف: ' + esc(state.last) + '</small>' : '');
    btn.textContent = state.checked_in ? 'تسجيل انصراف 🔴' : 'تسجيل حضور 🟢';
    btn.className = state.checked_in ? 'out' : '';
    btn.disabled = false;
    if (state.is_teacher) document.querySelectorAll('.tile.teach').forEach(t => t.style.display = '');
  }
  btn.addEventListener('click', () => {
    btn.disabled = true;
    msg.textContent = '📍 جاري تحديد موقعك...';
    if (!navigator.geolocation) { msg.textContent = 'المتصفح لا يدعم تحديد الموقع'; btn.disabled = false; return; }
    navigator.geolocation.getCurrentPosition(async (pos) => {
      msg.textContent = '⏳ جاري التسجيل...';
      try {
        const res = await rpc('/nursery-app/punch', {
          latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy });
        if (res.error) { msg.textContent = '❌ ' + res.error; }
        else {
          msg.textContent = res.action === 'in'
            ? '✅ تم تسجيل الحضور ' + res.time + '\\n(على بُعد ' + res.distance + ' متر)'
            : '✅ تم تسجيل الانصراف ' + res.time;
        }
        render(await rpc('/nursery-app/state'));
      } catch (e) { msg.textContent = '❌ ' + e.message; btn.disabled = false; }
    }, (err) => {
      msg.textContent = '❌ يجب السماح بالوصول إلى موقعك\\n(' + err.message + ')';
      btn.disabled = false;
    }, {enableHighAccuracy: true, timeout: 15000, maximumAge: 0});
  });
  try { render(await rpc('/nursery-app/state')); }
  catch (e) { statusBox.textContent = 'خطأ: ' + e.message; }
}

/* ---------- SALARIES ---------- */
async function salaries() {
  title.textContent = '💰 راتبي';
  M.innerHTML = '<div class="empty">... جاري التحميل</div>';
  const d = await rpc('/nursery-app/salaries');
  if (!d.rows.length) { M.innerHTML = '<div class="empty">لا توجد بيانات رواتب مسجلة بعد</div>'; return; }
  let h = '';
  d.rows.forEach(r => {
    h += '<div class="card"><h3>' + esc(r.term || 'الراتب') + '</h3>' +
      '<div class="row"><span class="l">الراتب المستحق</span><b>' + r.expected + ' ر.س</b></div>' +
      '<div class="row"><span class="l">المدفوع فعلياً</span><b>' + r.actual + ' ر.س</b></div>' +
      (r.paid_date ? '<div class="row"><span class="l">تاريخ الدفع</span><span>' + esc(r.paid_date) + '</span></div>' : '') +
      (r.notes ? '<div class="row"><span class="l">ملاحظات</span><span>' + esc(r.notes) + '</span></div>' : '') +
      '</div>';
  });
  if (d.deductions_total > 0)
    h += '<div class="card"><div class="row"><span class="l">إجمالي الخصومات المعتمدة</span><b style="color:#b91c1c">-' + d.deductions_total + ' ر.س</b></div></div>';
  M.innerHTML = h;
}

/* ---------- CLASSES ---------- */
async function classes() {
  title.textContent = '🏫 الفصول';
  M.innerHTML = '<div class="empty">... جاري التحميل</div>';
  const d = await rpc('/nursery-app/classes');
  if (!d.classes.length) {
    M.innerHTML = '<div class="empty">لا توجد فصول مسجلة بعد.<br/><small>تُضيف الإدارة الفصول من النظام: الحضانة ← الفصول</small></div>';
    return;
  }
  let h = '';
  d.classes.forEach(c => {
    h += '<div class="card"><h3>' + esc(c.name) + (c.teacher ? ' — ' + esc(c.teacher) : '') + '</h3>' +
      '<div class="row"><span class="l">عدد الأطفال</span><b>' + c.students.length + '</b></div>';
    c.students.forEach(s => { h += '<div class="row"><span>👧 ' + esc(s.name) + '</span></div>'; });
    h += '</div>';
  });
  M.innerHTML = h;
}

/* ---------- CHAT: student list ---------- */
async function chatList() {
  title.textContent = '💬 شات أولياء الأمور';
  M.innerHTML = '<div class="empty">... جاري التحميل</div>';
  const d = await rpc('/nursery-app/students');
  let h = '<input class="search" id="q" placeholder="🔍 دوري على اسم الطالب..."/><div id="list"></div>';
  M.innerHTML = h;
  const list = document.getElementById('list');
  function draw(filter) {
    let out = '';
    d.students.filter(s => !filter || s.name.includes(filter)).forEach(s => {
      out += '<div class="card stud">' +
        '<div class="info"><b>' + esc(s.name) + '</b><br/><small>' +
        (s.guardian ? esc(s.guardian) : 'ولي الأمر غير مسجل') + (s.phone ? ' • ' + esc(s.phone) : '') + '</small></div>' +
        (s.wa ? '<a class="wa" href="https://wa.me/' + s.wa + '" target="_blank">واتساب</a>' : '') +
        '<button class="chatbtn" onclick="nav(\\'thread-' + s.id + '\\')">📝 السجل</button>' +
        '</div>';
    });
    list.innerHTML = out || '<div class="empty">لا توجد نتائج</div>';
  }
  draw('');
  document.getElementById('q').addEventListener('input', e => draw(e.target.value.trim()));
}

/* ---------- CHAT: thread ---------- */
async function thread(studentId) {
  title.textContent = '💬 سجل التواصل';
  M.innerHTML = '<div class="empty">... جاري التحميل</div>';
  const d = await rpc('/nursery-app/messages', {student_id: studentId});
  title.textContent = '💬 ' + d.student;
  let h = '<div id="thread">';
  if (!d.messages.length) h += '<div class="empty">لا توجد رسائل بعد — ابدئي المحادثة</div>';
  d.messages.forEach(m => {
    h += '<div class="bubble ' + (m.mine ? 'me' : 'them') + '">' + esc(m.body) +
      '<small>' + esc(m.author) + ' • ' + esc(m.time) +
      (m.status ? ' • ' + esc(m.status) : '') + '</small></div>';
  });
  h += '</div><div class="sendrow"><input id="body" placeholder="اكتبي رسالة / ملاحظة..."/><button id="send">➤</button></div>';
  M.innerHTML = h;
  document.getElementById('send').addEventListener('click', async () => {
    const inp = document.getElementById('body');
    const txt = inp.value.trim();
    if (!txt) return;
    try {
      const r = await rpc('/nursery-app/messages/post', {student_id: studentId, body: txt});
      inp.value = '';
      if (r && r.pending) alert('تم إرسال الرسالة للمديرة للموافقة قبل وصولها لولي الأمر 💜');
      guard(thread)(studentId);
    } catch (e) { alert('الرسالة ماتبعتتش — جربي تاني: ' + e.message); }
  });
  window.scrollTo(0, document.body.scrollHeight);
}

/* ---------- DEDUCTIONS ---------- */
function daysLabel(d) {
  if (d === 0.25) return 'ربع يوم';
  if (d === 0.5) return 'نص يوم';
  if (d === 1) return 'يوم';
  if (d === 2) return 'يومين';
  return d ? d + ' يوم' : '';
}

async function deductions() {
  title.textContent = '⏰ خصوماتي';
  M.innerHTML = '<div class="empty">... جاري التحميل</div>';
  const d = await rpc('/nursery-app/deductions');
  if (!d.rows.length) { M.innerHTML = '<div class="empty">🎉 لا توجد عليكِ أي خصومات</div>'; return; }
  let h = '<div class="total">إجمالي الخصومات المعتمدة: <b>' + daysLabel(d.total_days) + '</b>' +
          (d.total > 0 ? ' (' + d.total.toFixed(2) + ' ر.س)' : '') + '</div>';
  d.rows.forEach(r => {
    const tb = r.dtype === 'absence' ? '<span class="badge b-red">غياب بدون إبلاغ</span>'
             : r.dtype === 'absence_auth' ? '<span class="badge b-amber">غياب بإذن الإدارة</span>'
             : r.dtype === 'late' ? '<span class="badge b-amber">تأخير ' + (r.minutes_late || '') + ' دقيقة</span>'
             : '<span class="badge b-gray">أخرى</span>';
    const sb = r.state === 'confirmed' ? '<span class="badge b-red">معتمد</span>'
             : r.state === 'draft' ? '<span class="badge b-gray">قيد المراجعة</span>'
             : '<span class="badge b-green">ملغي</span>';
    h += '<div class="card"><div class="row"><b>' + esc(r.date) + '</b>' + tb + '</div>' +
      '<div class="row"><span class="l">الخصم</span><b>' + daysLabel(r.days) +
      (r.amount > 0 ? ' (' + r.amount.toFixed(2) + ' ر.س)' : '') + '</b></div>' +
      '<div class="row"><span class="l">الحالة</span>' + sb + '</div>' +
      (r.note ? '<div class="row"><span class="l">' + esc(r.note) + '</span></div>' : '') +
      '</div>';
  });
  M.innerHTML = h;
}

route();
</script>
</body>
</html>"""


class NurseryApp(http.Controller):

    @http.route('/nursery-app', type='http', auth='user', website=False)
    def app_page(self, **kw):
        _require_internal()
        page = PAGE.replace('__USER__', str(html_escape(request.env.user.name)))
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
        ])

    @http.route('/nursery-app/manifest.webmanifest', type='http', auth='public')
    def app_manifest(self, **kw):
        manifest = {
            'name': 'حضانة مونتيسوري',
            'short_name': 'مونتيسوري',
            'start_url': '/nursery-app',
            'scope': '/nursery-app',
            'display': 'standalone',
            'dir': 'rtl',
            'lang': 'ar',
            'background_color': '#f0f7f2',
            'theme_color': '#14532d',
            'icons': [{
                'src': '/nursery/static/description/icon.png',
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'any',
            }],
        }
        return request.make_response(json.dumps(manifest), headers=[
            ('Content-Type', 'application/manifest+json'),
        ])

    # ---------------- attendance ----------------

    @http.route('/nursery-app/state', type='json', auth='user')
    def app_state(self, **kw):
        _require_internal()
        env = request.env
        emp = _employee(env)
        if not emp:
            return {'checked_in': False, 'last': False, 'error': 'no employee'}
        if emp.attendance_exempt:
            return {'checked_in': False, 'last': False,
                    'exempt': True, 'is_teacher': _is_teacher()}
        open_att = _open_attendance(env, emp)
        if open_att:
            since = fields.Datetime.context_timestamp(
                env.user, open_att.check_in).strftime('%H:%M')
            return {'checked_in': True, 'since': since, 'is_teacher': _is_teacher()}
        last = env['hr.attendance'].sudo().search(
            [('employee_id', '=', emp.id)], limit=1, order='check_in desc')
        last_s = False
        if last and last.check_out:
            last_s = fields.Datetime.context_timestamp(
                env.user, last.check_out).strftime('%d/%m %H:%M')
        return {'checked_in': False, 'last': last_s, 'is_teacher': _is_teacher()}

    @http.route('/nursery-app/punch', type='json', auth='user')
    def app_punch(self, latitude=None, longitude=None, accuracy=None, **kw):
        _require_internal()
        env = request.env
        emp = _employee(env)
        if not emp:
            return {'error': 'لا يوجد ملف موظف مرتبط بحسابك — يرجى التواصل مع الإدارة'}
        if emp.attendance_exempt:
            return {'error': 'أنت معفى من تسجيل الحضور والانصراف'}
        try:
            latitude, longitude = float(latitude), float(longitude)
        except (TypeError, ValueError):
            return {'error': 'لم يصل الموقع — فعّلي خدمة الموقع وحاولي تاني'}

        lat0, lng0, radius = _geo_params(env)
        dist = _distance_m(latitude, longitude, lat0, lng0)
        is_admin = env.user.has_group('base.group_system')

        open_att = _open_attendance(env, emp)
        action = 'out' if open_att else 'in'

        if action == 'in' and dist > radius and not is_admin:
            return {'error': 'أنتِ بعيدة عن الحضانة بمسافة %d متر — يجب أن تكوني داخل الحضانة لتسجيل الحضور' % int(dist)}

        now = fields.Datetime.now()
        if action == 'in':
            env['hr.attendance'].sudo().create({
                'employee_id': emp.id,
                'check_in': now,
                'in_latitude': float(latitude),
                'in_longitude': float(longitude),
            })
        else:
            open_att.sudo().write({
                'check_out': now,
                'out_latitude': float(latitude),
                'out_longitude': float(longitude),
            })
        local = fields.Datetime.context_timestamp(env.user, now).strftime('%H:%M')
        return {'action': action, 'time': local, 'distance': int(dist)}

    # ---------------- salaries ----------------

    @http.route('/nursery-app/salaries', type='json', auth='user')
    def app_salaries(self, **kw):
        _require_internal()
        env = request.env
        emp = _employee(env)
        if not emp:
            return {'rows': [], 'deductions_total': 0}
        term_labels = dict(
            env['nursery.salary']._fields['term']._description_selection(env))
        rows = env['nursery.salary'].sudo().search(
            [('employee_id', '=', emp.id)], order='id desc')
        if not rows:
            # legacy rows not yet linked to an employee — match by name only
            rows = env['nursery.salary'].sudo().search(
                [('teacher', '=', emp.name), ('employee_id', '=', False)],
                order='id desc')
        ded = env['nursery.deduction'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'confirmed')])
        return {
            'rows': [{
                'term': term_labels.get(r.term, r.term or ''),
                'expected': r.expected,
                'actual': r.actual,
                'paid_date': str(r.paid_date) if r.paid_date else False,
                'notes': r.notes or False,
            } for r in rows],
            'deductions_total': sum(ded.mapped('amount')),
        }

    # ---------------- classes ----------------

    @http.route('/nursery-app/classes', type='json', auth='user')
    def app_classes(self, **kw):
        _require_internal()
        if not _is_teacher():
            return {'classes': [], 'error': 'غير مصرح'}
        env = request.env
        emp = _employee(env)
        is_admin = env.user.has_group('base.group_system')
        domain = [] if is_admin else ['|', ('teacher_id', '=', emp.id if emp else 0),
                                      ('teacher_id', '=', False)]
        classes = env['nursery.class'].sudo().search(domain)
        return {'classes': [{
            'name': c.name,
            'teacher': c.teacher_id.name or False,
            'students': [{'id': s.id, 'name': s.name} for s in c.student_ids],
        } for c in classes]}

    # ---------------- chat ----------------

    @http.route('/nursery-app/students', type='json', auth='user')
    def app_students(self, **kw):
        _require_internal()
        if not _is_teacher():
            return {'students': [], 'error': 'غير مصرح'}
        env = request.env
        students = env['nursery.student'].sudo().search(
            [('active', '=', True)], order='name')
        return {'students': [{
            'id': s.id,
            'name': s.name,
            'guardian': s.guardian_name or False,
            'phone': s.guardian_phone or False,
            'wa': _wa_phone(s.guardian_phone),
        } for s in students]}

    @http.route('/nursery-app/messages', type='json', auth='user')
    def app_messages(self, student_id=None, **kw):
        _require_internal()
        if not _is_teacher():
            return {'student': '', 'messages': [], 'error': 'غير مصرح'}
        env = request.env
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            return {'student': '', 'messages': []}
        student = env['nursery.student'].sudo().browse(student_id)
        if not student.exists():
            return {'student': '', 'messages': []}
        # آخر 200 رسالة (الأحدث)، وبنرتبهم تصاعدي للعرض
        msgs = env['nursery.message'].sudo().search(
            [('student_id', '=', student.id)], order='create_date desc', limit=200)
        msgs = msgs.sorted('create_date')
        state_label = {'pending': '⏳ بانتظار موافقة المديرة',
                       'rejected': '🚫 رفضتها المديرة', 'approved': ''}
        return {
            'student': student.name,
            'messages': [{
                'body': m.body,
                'author': 'ولي الأمر 👨‍👩‍👧' if m.is_parent else m.author_id.name,
                'mine': (not m.is_parent) and m.author_id.id == env.user.id,
                'status': state_label.get(m.state, ''),
                'time': fields.Datetime.context_timestamp(
                    env.user, m.create_date).strftime('%d/%m %H:%M'),
            } for m in msgs],
        }

    @http.route('/nursery-app/messages/post', type='json', auth='user')
    def app_messages_post(self, student_id=None, body=None, **kw):
        _require_internal()
        if not _is_teacher():
            return {'ok': False, 'error': 'غير مصرح'}
        env = request.env
        body = (body or '').strip()
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            return {'ok': False}
        if not body or not env['nursery.student'].sudo().browse(student_id).exists():
            return {'ok': False}
        # المديرة/الأدمن رسائلهم تعدي فوراً؛ المعلمة الموثوقة كمان؛
        # غير كده الرسالة تروح "بانتظار موافقة المديرة"
        is_mgr = (env.user.has_group('nursery.group_nursery_manager')
                  or env.user.has_group('base.group_system'))
        emp = _employee(env)
        trusted = bool(emp and emp.messages_trusted)
        state = 'approved' if (is_mgr or trusted) else 'pending'
        env['nursery.message'].sudo().create({
            'student_id': student_id,
            'author_id': env.user.id,
            'body': body[:2000],
            'state': state,
        })
        return {'ok': True, 'pending': state == 'pending'}

    # ---------------- deductions ----------------

    @http.route('/nursery-app/deductions', type='json', auth='user')
    def app_deductions(self, **kw):
        _require_internal()
        env = request.env
        emp = _employee(env)
        if not emp:
            return {'rows': [], 'total': 0}
        rows = env['nursery.deduction'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '!=', 'cancelled')],
            order='date desc', limit=100)
        confirmed = rows.filtered(lambda r: r.state == 'confirmed')
        return {
            'rows': [{
                'date': str(r.date),
                'dtype': r.dtype,
                'minutes_late': r.minutes_late,
                'days': r.days,
                'amount': r.amount,
                'state': r.state,
                'note': r.note or False,
            } for r in rows],
            'total': sum(confirmed.mapped('amount')),
            'total_days': sum(confirmed.mapped('days')),
        }
