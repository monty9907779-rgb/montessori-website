# -*- coding: utf-8 -*-
import json
import math
import re
from datetime import datetime, timedelta

import pytz
import werkzeug.exceptions

from odoo import fields, http
from odoo.http import request

NURSERY_TZ = 'Asia/Riyadh'
DEFAULT_LAT = 21.5795281
DEFAULT_LNG = 39.194829
DEFAULT_RADIUS_M = 400


def _geo_params(env):
    icp = env['ir.config_parameter'].sudo()
    try:
        return (float(icp.get_param('nursery.geo_lat', DEFAULT_LAT)),
                float(icp.get_param('nursery.geo_lng', DEFAULT_LNG)),
                float(icp.get_param('nursery.geo_radius', DEFAULT_RADIUS_M)))
    except (TypeError, ValueError):
        return DEFAULT_LAT, DEFAULT_LNG, DEFAULT_RADIUS_M


def _distance_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _geofence_error(env, latitude, longitude):
    """يرجّع رسالة خطأ لو ولي الأمر بعيد عن الحضانة، وإلا None."""
    try:
        lat, lng = float(latitude), float(longitude)
    except (TypeError, ValueError):
        return 'يجب السماح بالوصول إلى موقعك لتسجيل حضور طفلك'
    lat0, lng0, radius = _geo_params(env)
    dist = _distance_m(lat, lng, lat0, lng0)
    if dist > radius:
        return ('أنت بعيد عن الحضانة بمسافة %d متر — يجب أن تكون داخل الحضانة '
                'لتسجيل حضور أو خروج طفلك' % int(dist))
    return None


_TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')


def _student_by_token(token):
    if not token or not _TOKEN_RE.match(token):
        return None
    student = request.env['nursery.student'].sudo().search(
        [('portal_token', '=', token), ('active', '=', True)], limit=1)
    return student or None


_DRIVE_ID_RE = re.compile(r'^[A-Za-z0-9_-]+$')


def _safe_drive_id(v):
    """يرفض أي قيمة فيها حروف غريبة (علامات اقتباس... إلخ) قبل ما تتحط في HTML."""
    return v if v and _DRIVE_ID_RE.match(v) else False


def _local_now():
    return fields.Datetime.now()


def _local_today():
    """تاريخ اليوم بتوقيت جدة — عشان تسجيل الحضور بعد نص الليل بتوقيت
    UTC (يعني قبل 3 الفجر بتوقيت جدة) ميتسجلش على تاريخ اليوم اللي فات."""
    return datetime.now(pytz.timezone(NURSERY_TZ)).date()


def _fmt_dt(dt):
    if not dt:
        return False
    tz = pytz.timezone(NURSERY_TZ)
    return pytz.utc.localize(dt).astimezone(tz).strftime('%H:%M')


PARENT_PAGE = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no"/>
<meta name="apple-mobile-web-app-capable" content="yes"/>
<meta name="referrer" content="no-referrer"/>
<meta name="theme-color" content="#7c3aed"/>
<link rel="manifest" href="/parent/__TOKEN__/manifest.webmanifest"/>
<link rel="apple-touch-icon" href="/nursery/static/description/icon.png"/>
<title>حضانة مونتيسوري | ولي الأمر</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, "Segoe UI", Tahoma, sans-serif; }
  body { background: linear-gradient(180deg,#f5f3ff 0%,#fdf4ff 100%); min-height: 100vh; }
  header { background: linear-gradient(135deg,#7c3aed,#a855f7); color: #fff; padding: 18px 16px 46px; text-align: center;
           border-radius: 0 0 28px 28px; }
  header img { width: 54px; height: 54px; border-radius: 14px; background: #fff; padding: 4px; }
  header h1 { font-size: 18px; margin-top: 6px; }
  header .child { font-size: 22px; font-weight: 800; margin-top: 4px; }
  main { max-width: 480px; margin: -28px auto 0; padding: 0 14px 40px; }
  .card { background: #fff; border-radius: 18px; padding: 16px; margin-bottom: 12px;
          box-shadow: 0 2px 10px rgba(124,58,237,.08); }
  .card h3 { color: #7c3aed; font-size: 15px; margin-bottom: 10px; }
  .row { display: flex; justify-content: space-between; font-size: 14px; margin: 5px 0; }
  .row .l { color: #6b7280; }
  .btns { display: flex; gap: 10px; }
  .btns button { flex: 1; padding: 16px 8px; border: 0; border-radius: 14px; font-size: 16px; font-weight: 800; color: #fff; }
  #arrive { background: #16a34a; } #depart { background: #f59e0b; }
  .btns button:disabled { background: #d1d5db; color: #6b7280; }
  #att-msg { text-align: center; font-size: 13px; color: #374151; margin-top: 8px; min-height: 18px; }
  .badge { padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 700; }
  .b-green { background: #dcfce7; color: #15803d; } .b-red { background: #fee2e2; color: #b91c1c; }
  .b-amber { background: #fef3c7; color: #b45309; } .b-violet { background: #ede9fe; color: #6d28d9; }
  .tabs { display: grid; grid-template-columns: repeat(4,1fr); gap: 8px; margin-bottom: 12px; }
  .tabs button { background: #fff; border: 0; border-radius: 14px; padding: 12px 4px; font-size: 12px; font-weight: 700;
                 color: #6d28d9; box-shadow: 0 1px 6px rgba(124,58,237,.08); }
  .tabs button span { display: block; font-size: 22px; margin-bottom: 3px; }
  .tabs button.on { background: #7c3aed; color: #fff; }
  #thread { display: flex; flex-direction: column; gap: 8px; }
  .bubble { max-width: 82%; padding: 10px 12px; border-radius: 14px; font-size: 14px; white-space: pre-line; }
  .bubble.me { background: #ede9fe; align-self: flex-start; }
  .bubble.them { background: #f0fdf4; align-self: flex-end; }
  .bubble small { display: block; color: #9ca3af; font-size: 11px; margin-top: 4px; }
  .sendrow { display: flex; gap: 8px; margin-top: 10px; }
  .sendrow input { flex: 1; border: 1px solid #ddd6fe; border-radius: 12px; padding: 12px; font-size: 15px; }
  .sendrow button { background: #7c3aed; color: #fff; border: 0; border-radius: 12px; padding: 0 16px; font-size: 18px; }
  .albums { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .album { background: #fff; border-radius: 14px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,.08); cursor: pointer; }
  .album img { width: 100%; height: 110px; object-fit: cover; display: block; background: #ede9fe; }
  .album div { padding: 8px; font-size: 13px; font-weight: 700; color: #4c1d95; text-align: center; }
  .photos { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; }
  .photos a img { width: 100%; height: 100px; object-fit: cover; border-radius: 10px; display: block; background: #ede9fe; }
  .empty { text-align: center; color: #9ca3af; padding: 26px 8px; font-size: 14px; }
  .hol { display: flex; justify-content: space-between; align-items: center; padding: 10px 4px; border-bottom: 1px dashed #ede9fe; font-size: 14px; }
  footer { text-align: center; color: #a78bfa; font-size: 12px; padding: 14px; }
</style>
</head>
<body>
<header>
  <img src="/nursery/static/description/icon.png"/>
  <h1>حضانة مونتيسوري 🌸</h1>
  <div class="child">__CHILD__</div>
</header>
<main>
  <div class="card" id="countdown" style="display:none; text-align:center;">
    <h3 id="cd-title">⏳ باقي على تجديد الرسوم</h3>
    <div id="cd-timer" style="font-size:26px; font-weight:800; color:#7c3aed; letter-spacing:1px;"></div>
    <div id="cd-sub" style="font-size:13px; color:#6b7280; margin-top:4px;"></div>
  </div>

  <div class="card">
    <h3>✋ حضور وخروج اليوم</h3>
    <div class="btns">
      <button id="arrive">🟢 وصل ابني</button>
      <button id="depart">🏠 استلمت ابني</button>
    </div>
    <div id="att-msg"></div>
  </div>

  <div class="tabs">
    <button data-t="info"><span>👧</span>البيانات</button>
    <button data-t="pay"><span>💳</span>الرسوم</button>
    <button data-t="chat"><span>💬</span>الشات</button>
    <button data-t="photos"><span>📷</span>الصور</button>
  </div>
  <div id="content"></div>
</main>
<footer>Montessori Nursery • Jeddah 🇸🇦</footer>
<script>
const TOKEN = '__TOKEN__';
let S = null;
const C = document.getElementById('content');

async function rpc(path, params) {
  const r = await fetch('/parent/' + TOKEN + path, {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: params || {}})
  });
  const d = await r.json();
  if (d.error) throw new Error((d.error.data && d.error.data.message) || d.error.message);
  return d.result;
}
function esc(s) { const d = document.createElement('div'); d.textContent = s == null ? '' : String(s); return d.innerHTML; }

function attRender() {
  const a = S.today;
  const btnA = document.getElementById('arrive'), btnD = document.getElementById('depart');
  const msg = document.getElementById('att-msg');
  btnA.disabled = !!a.arrival;
  btnD.disabled = !a.arrival || !!a.departure;
  if (!a.arrival) msg.textContent = 'لم يتم تسجيل حضور اليوم بعد';
  else if (!a.departure) msg.textContent = '✅ حضر الساعة ' + a.arrival;
  else msg.textContent = '✅ حضر ' + a.arrival + ' — 🏠 خرج ' + a.departure;
}

document.getElementById('arrive').onclick = async () => {
  try { S.today = await rpc('/checkin'); attRender(); } catch(e) { alert(e.message); }
};
document.getElementById('depart').onclick = async () => {
  try { S.today = await rpc('/checkout'); attRender(); } catch(e) { alert(e.message); }
};

function tab(t) {
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.t === t));
  if (t === 'info') return info();
  if (t === 'pay') return pay();
  if (t === 'chat') return chat();
  if (t === 'photos') return photos();
}
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => tab(b.dataset.t));

function info() {
  const i = S.child;
  let h = '<div class="card"><h3>👧 بيانات ' + esc(i.name) + '</h3>' +
    (i.class_name ? '<div class="row"><span class="l">الفصل</span><b>' + esc(i.class_name) + '</b></div>' : '') +
    (i.teacher ? '<div class="row"><span class="l">المعلمة</span><b>' + esc(i.teacher) + '</b></div>' : '') +
    (i.joining_date ? '<div class="row"><span class="l">تاريخ الالتحاق</span><span>' + esc(i.joining_date) + '</span></div>' : '') +
    '</div>';
  h += '<div class="card"><h3>📅 إجازات الحضانة</h3>';
  if (!S.holidays.length) h += '<div class="empty">لا توجد إجازات معلنة قريبة</div>';
  S.holidays.forEach(x => {
    h += '<div class="hol"><b>' + esc(x.name) + '</b><span class="badge b-violet">' + esc(x.from) +
         (x.to !== x.from ? ' → ' + esc(x.to) : '') + '</span></div>';
  });
  h += '<div class="hol"><span>الويك إند</span><span class="badge b-violet">الجمعة والسبت</span></div></div>';
  h += '<div class="card"><h3>🕗 مواعيد الحضانة</h3><div class="row"><span class="l">من الأحد للخميس</span><b>8:00 ص – 2:00 م</b></div></div>';
  C.innerHTML = h;
}

function pay() {
  const p = S.payment;
  let h = '<div class="card"><h3>💳 حالة الرسوم</h3>' +
    '<div class="row"><span class="l">الرسوم الشهرية</span><b>' + p.fees + ' ر.س</b></div>' +
    '<div class="row"><span class="l">الحالة</span>' + (p.paid ? '<span class="badge b-green">مدفوع ✓</span>' : '<span class="badge b-red">مستحق الدفع</span>') + '</div>' +
    (p.paid_until ? '<div class="row"><span class="l">مدفوع حتى</span><b>' + esc(p.paid_until) + '</b></div>' : '') +
    (p.next_due ? '<div class="row"><span class="l">ميعاد الدفعة الجاية</span><span class="badge b-amber">' + esc(p.next_due) + '</span></div>' : '') +
    '</div>';
  h += '<div class="card"><h3>🧾 سجل المدفوعات</h3>';
  if (!p.history.length) h += '<div class="empty">لا توجد مدفوعات مسجلة</div>';
  p.history.forEach(x => {
    h += '<div class="row"><span>' + esc(x.date) + (x.period ? ' — ' + esc(x.period) : '') + '</span><b>' + x.amount + ' ر.س</b></div>';
  });
  h += '</div>';
  C.innerHTML = h;
}

async function chat() {
  C.innerHTML = '<div class="card"><div class="empty">... جاري التحميل</div></div>';
  try {
    const d = await rpc('/messages');
    let h = '<div class="card"><h3>💬 التواصل مع المعلمة</h3><div id="thread">';
    if (!d.messages.length) h += '<div class="empty">ابدأ المحادثة مع معلمة ' + esc(S.child.name) + ' 💜</div>';
    d.messages.forEach(m => {
      h += '<div class="bubble ' + (m.is_parent ? 'me' : 'them') + '">' + esc(m.body) +
        '<small>' + (m.is_parent ? 'أنا' : esc(m.author)) + ' • ' + esc(m.time) + '</small></div>';
    });
    h += '</div><div class="sendrow"><input id="mbody" placeholder="اكتب رسالتك..."/><button id="msend">➤</button></div></div>';
    C.innerHTML = h;
    document.getElementById('msend').onclick = async () => {
      const inp = document.getElementById('mbody');
      if (!inp.value.trim()) return;
      try { await rpc('/messages/post', {body: inp.value.trim()}); inp.value=''; chat(); }
      catch(e) { alert('لم تُرسل — حاول تاني'); }
    };
  } catch(e) { C.innerHTML = '<div class="card empty">خطأ: ' + esc(e.message) + '</div>'; }
}

function thumb(id, w) { return 'https://drive.google.com/thumbnail?id=' + id + '&sz=w' + (w || 400); }

async function photos(albumId) {
  C.innerHTML = '<div class="card"><div class="empty">... جاري التحميل</div></div>';
  try {
    if (!albumId) {
      const d = await rpc('/albums');
      if (!d.albums.length) { C.innerHTML = '<div class="card empty">📷 لا توجد ألبومات بعد — ستظهر صور أول مناسبة هنا!</div>'; return; }
      let h = '<div class="albums">';
      d.albums.forEach(a => {
        h += '<div class="album" onclick="photos(' + a.id + ')">' +
          (a.cover ? '<img loading="lazy" src="' + thumb(a.cover, 400) + '"/>' : '<img/>') +
          '<div>' + esc(a.name) + ' (' + a.count + ')</div></div>';
      });
      C.innerHTML = h + '</div>';
    } else {
      const d = await rpc('/albums/' + albumId);
      let h = '<div class="card"><h3>📷 ' + esc(d.name) + '</h3><div class="photos">';
      d.photos.forEach(p => {
        h += '<a href="https://drive.google.com/file/d/' + p.drive_id + '/view" target="_blank">' +
             '<img loading="lazy" src="' + thumb(p.drive_id, 300) + '"/></a>';
      });
      h += '</div></div><button class="tabs" style="width:100%;border:0;background:#ede9fe;color:#6d28d9;border-radius:12px;padding:12px;font-weight:700" onclick="photos()">◀ كل الألبومات</button>';
      C.innerHTML = h;
    }
  } catch(e) { C.innerHTML = '<div class="card empty">خطأ: ' + esc(e.message) + '</div>'; }
}

function startCountdown() {
  const p = S.payment;
  if (!p.paid_until) return;
  const box = document.getElementById('countdown');
  const timerEl = document.getElementById('cd-timer');
  const titleEl = document.getElementById('cd-title');
  const subEl = document.getElementById('cd-sub');
  box.style.display = '';
  // نهاية اليوم المدفوع حتى نهايته بتوقيت جدة
  const target = new Date(p.paid_until + 'T23:59:59+03:00');
  function tick() {
    const diff = target - new Date();
    if (diff > 0) {
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      titleEl.textContent = '⏳ باقي على تجديد الرسوم';
      timerEl.style.color = d < 3 ? '#d97706' : '#7c3aed';
      timerEl.textContent = d + ' يوم ' + h + ' ساعة ' + m + ' دقيقة ' + s + ' ثانية';
      subEl.textContent = 'الرسوم: ' + p.fees + ' ر.س — مدفوع حتى ' + p.paid_until;
    } else {
      const late = Math.floor(-diff / 86400000);
      titleEl.textContent = '⛔ الرسوم مستحقة';
      timerEl.style.color = '#dc2626';
      timerEl.textContent = 'متأخر ' + late + ' يوم';
      subEl.textContent = 'برجاء التواصل مع الإدارة لتجديد الاشتراك (' + p.fees + ' ر.س)';
    }
  }
  tick();
  setInterval(tick, 1000);
}

(async function init() {
  S = await rpc('/state');
  attRender();
  startCountdown();
  tab('info');
})();
</script>
</body>
</html>"""


class NurseryParentPortal(http.Controller):

    @http.route('/parent/<string:token>', type='http', auth='public', website=False)
    def parent_page(self, token, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        page = (PARENT_PAGE
                .replace('__TOKEN__', token)
                .replace('__CHILD__', student.name.replace('<', '').replace('>', '')))
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store'),
            ('X-Robots-Tag', 'noindex'),
        ])

    @http.route('/parent/<string:token>/manifest.webmanifest', type='http', auth='public')
    def parent_manifest(self, token, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        manifest = {
            'name': 'مونتيسوري | %s' % student.name,
            'short_name': 'مونتيسوري',
            'start_url': '/parent/%s' % token,
            'scope': '/parent/%s' % token,
            'display': 'standalone', 'dir': 'rtl', 'lang': 'ar',
            'background_color': '#f5f3ff', 'theme_color': '#7c3aed',
            'icons': [{'src': '/nursery/static/description/icon.png',
                       'sizes': '512x512', 'type': 'image/png'}],
        }
        return request.make_response(json.dumps(manifest), headers=[
            ('Content-Type', 'application/manifest+json'),
            ('Cache-Control', 'no-store')])

    def _today_payload(self, student):
        env = request.env
        today = _local_today()
        att = env['nursery.attendance'].sudo().search(
            [('student_id', '=', student.id), ('date', '=', today)], limit=1)
        return {
            'arrival': _fmt_dt(att.arrival) if att else False,
            'departure': _fmt_dt(att.departure) if att else False,
        }

    @http.route('/parent/<string:token>/state', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_state(self, token, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        env = request.env
        today = _local_today()
        hols = env['nursery.holiday'].sudo().search(
            [('date_to', '>=', today)], limit=10)
        next_due = False
        if student.paid_until:
            next_due = (student.paid_until + timedelta(days=1)).strftime('%Y-%m-%d')
        pays = env['nursery.fee.payment'].sudo().search(
            [('student_id', '=', student.id)], order='date desc', limit=12)
        return {
            'child': {
                'name': student.name,
                'class_name': student.class_id.name or False,
                'teacher': student.class_id.teacher_id.name or False,
                'joining_date': str(student.joining_date) if student.joining_date else False,
            },
            'today': self._today_payload(student),
            'payment': {
                'fees': student.fees,
                'paid': student.paid,
                'paid_until': str(student.paid_until) if student.paid_until else False,
                'next_due': next_due,
                'history': [{'date': str(p.date), 'amount': p.amount,
                             'period': p.period or False} for p in pays],
            },
            'holidays': [{'name': h.name, 'from': str(h.date_from),
                          'to': str(h.date_to)} for h in hols],
        }

    @http.route('/parent/<string:token>/checkin', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_checkin(self, token, latitude=None, longitude=None, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        env = request.env
        # جيوفنس: لازم ولي الأمر يكون عند الحضانة (نفس حيز المدرسين 400م)
        err = _geofence_error(env, latitude, longitude)
        if err:
            return {'error': err}
        today = _local_today()
        Att = env['nursery.attendance'].sudo()
        att = Att.search([('student_id', '=', student.id), ('date', '=', today)], limit=1)
        if not att:
            att = Att.create({
                'student_id': student.id, 'date': today, 'status': 'present',
                'arrival': _local_now(), 'by_parent': True,
            })
        elif not att.arrival:
            # ما تلغيش حالة سجلتها المعلمة (غائب/مريض) — بس سجّل وقت الوصول
            att.write({'arrival': _local_now(), 'by_parent': True})
        return self._today_payload(student)

    @http.route('/parent/<string:token>/checkout', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_checkout(self, token, latitude=None, longitude=None, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        env = request.env
        err = _geofence_error(env, latitude, longitude)
        if err:
            return {'error': err}
        today = _local_today()
        att = env['nursery.attendance'].sudo().search(
            [('student_id', '=', student.id), ('date', '=', today)], limit=1)
        if att and att.arrival and not att.departure:
            att.write({'departure': _local_now()})
        return self._today_payload(student)

    @http.route('/parent/<string:token>/messages', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_messages(self, token, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        # ولي الأمر يشوف رسائله هو + رسائل المعلمات المعتمدة فقط
        # (الرسائل المعلقة بانتظار موافقة المديرة لا تظهر له)
        msgs = request.env['nursery.message'].sudo().search(
            ['&', ('student_id', '=', student.id),
             '|', ('is_parent', '=', True), ('state', '=', 'approved')],
            order='create_date desc', limit=200)
        msgs = msgs.sorted('create_date')
        return {'messages': [{
            'body': m.body,
            'is_parent': m.is_parent,
            'author': 'المعلمة' if not m.is_parent else 'ولي الأمر',
            'time': _fmt_dt(m.create_date) or '',
        } for m in msgs]}

    @http.route('/parent/<string:token>/messages/post', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_messages_post(self, token, body=None, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        body = (body or '').strip()
        if not body:
            return {'ok': False}
        request.env['nursery.message'].sudo().create({
            'student_id': student.id,
            'author_id': request.env.ref('base.public_user').id,
            'is_parent': True,
            'body': body[:2000],
        })
        return {'ok': True}

    @http.route('/parent/<string:token>/evals', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_evals(self, token, **kw):
        """تقييمات المعلمة (يومي/أسبوعي) لصفحة ولي الأمر."""
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        from .staff_api import EVAL_CRITERIA
        labels = {t: dict(c) for t, c in EVAL_CRITERIA.items()}
        evs = request.env['nursery.evaluation'].sudo().search(
            [('student_id', '=', student.id)], limit=20)
        out = []
        for e in evs:
            try:
                sc = json.loads(e.scores or '{}')
            except ValueError:
                sc = {}
            crit = [{'label': labels.get(e.etype, {}).get(k, k), 'val': v}
                    for k, v in sc.items()
                    if isinstance(v, int) and 1 <= v <= 5]
            if not crit and not (e.note or '').strip():
                continue
            avg = round(sum(c['val'] for c in crit) / len(crit), 1) if crit else 0
            out.append({
                'etype': e.etype,
                'type_label': 'تقييم اليوم' if e.etype == 'daily' else 'تقييم الأسبوع',
                'date': e.date.strftime('%Y-%m-%d'),
                'criteria': crit, 'avg': avg,
                'note': e.note or '',
                'teacher': e.teacher_id.name or '',
            })
        return {'ok': True, 'evals': out}

    @http.route('/parent/<string:token>/albums', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_albums(self, token, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        albums = request.env['nursery.album'].sudo().search(
            [('active', '=', True), ('parent_visible', '=', True)])
        return {'albums': [{
            'id': a.id, 'name': a.name,
            'cover': _safe_drive_id(a.cover_file_id) or
                     (_safe_drive_id(a.photo_ids[:1].drive_id) if a.photo_ids else False),
            'count': a.photo_count,
        } for a in albums]}

    @http.route('/parent/<string:token>/albums/<int:album_id>', type='json', auth='public', cors='https://montessori-ksa.com')
    def parent_album_photos(self, token, album_id, **kw):
        student = _student_by_token(token)
        if not student:
            raise werkzeug.exceptions.NotFound()
        album = request.env['nursery.album'].sudo().search(
            [('id', '=', album_id), ('active', '=', True),
             ('parent_visible', '=', True)], limit=1)
        if not album:
            return {'name': '', 'photos': []}
        return {'name': album.name, 'photos': [
            {'drive_id': _safe_drive_id(p.drive_id), 'name': p.name or ''}
            for p in album.photo_ids if _safe_drive_id(p.drive_id)]}
