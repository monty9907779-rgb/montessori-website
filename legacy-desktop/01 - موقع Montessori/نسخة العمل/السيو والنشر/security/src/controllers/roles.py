# -*- coding: utf-8 -*-
"""صفحة توزيع الأدوار للمديرة + مدخل ولي الأمر بحساب جوجل (/my-child)
+ نقطة الدخول الموحّدة SSO (/portal-login → جوجل → /portal-home حسب الدور)."""
import json
import re

from datetime import datetime, time as dt_time, timedelta

from dateutil.relativedelta import relativedelta

import werkzeug.exceptions
import werkzeug.urls
from markupsafe import escape as e

from odoo import http, fields
from odoo.http import request

from ..models.nursery import (BOOKS_FEE_DEFAULT, DAY_BASIS, STUDENT_LEVELS,
                              advance_due, coverage_for, days_for_amount)


WEBSITE = 'https://montessori-ksa.com'
STUDENT_LEVEL_KEYS = {key for key, _label in STUDENT_LEVELS}
STUDENT_LEVEL_LABELS = dict(STUDENT_LEVELS)
_AI_CHATWOOT_CACHE = {'at': None, 'data': None}


def _parent_student_domain(user_id):
    """Legacy one-to-one field plus the new multi-child relation."""
    return [('active', '=', True), '|',
            ('parent_user_id', '=', user_id),
            ('parent_user_ids', 'in', [user_id])]


def _parent_students(env, user):
    return env['nursery.student'].sudo().search(
        _parent_student_domain(user.id), order='name')


def _stats_allowed(env, user):
    """هل يُسمح لهذا المستخدم برؤية/دخول لوحات الإحصائيات؟
    قائمة بيضاء بالبريد في ir.config_parameter — فاضية = كل أونر."""
    allowed = (env['ir.config_parameter'].sudo()
               .get_param('nursery.stats_sso_emails') or '')
    allowed = [x.strip() for x in allowed.lower().replace(',', ' ').split()
               if x.strip()]
    if not user or not user.has_group('base.group_system'):
        return False
    if not allowed:
        return True
    return (user.email or user.login or '').strip().lower() in allowed


# ============ صلاحيات الأدوار (يتحكّم فيها الأونر من صفحة /permissions/) ============
# الافتراضي: كل شيء مسموح = نفس السلوك الحالي بالضبط. الأونر يقفل ما يشاء.
PERM_DEFAULTS = {
    'teacher': {'salary': True, 'deductions': True, 'classes': True, 'chat': True,
                'evals': True, 'phones': True},
    'worker':  {'salary': True, 'deductions': True},
    'manager': {'dashboard': True, 'students': True, 'classes': True, 'books': True,
                'salaries': True, 'accounts': True, 'albums': True, 'cameras': True,
                'roles': True, 'manage': True, 'ai': True},
    'parent':  {'payments': True, 'evals': True, 'photos': True},
}
# مفاتيح صفحات المديرة = نفس مفاتيح بنود القائمة العلوية (adminNav) — للإخفاء من القائمة
MANAGER_PAGES = ['dashboard', 'students', 'classes', 'books', 'salaries',
                 'accounts', 'albums', 'cameras', 'roles', 'manage', 'ai']
PERM_CATALOG = [
    {'role': 'teacher', 'label': 'المدرّسة — أقسام صفحتها', 'caps': [
        {'key': 'salary',     'label': 'راتبي'},
        {'key': 'deductions', 'label': 'الخصومات'},
        {'key': 'classes',    'label': 'فصولي (قائمة الطلاب)'},
        {'key': 'chat',       'label': 'شات أولياء الأمور'},
        {'key': 'evals',      'label': 'تقييم الطلاب (يومي / أسبوعي)'},
        {'key': 'phones',     'label': 'تشوف تليفونات أولياء الأمور'},
    ]},
    {'role': 'worker', 'label': 'العاملة — أقسام صفحتها', 'caps': [
        {'key': 'salary',     'label': 'راتبي'},
        {'key': 'deductions', 'label': 'الخصومات'},
    ]},
    {'role': 'manager', 'label': 'المديرة — الصفحات اللي تشوفها', 'caps': [
        {'key': 'dashboard', 'label': 'الرئيسية / الداشبورد المالي'},
        {'key': 'ai',        'label': 'ذكاء الحضانة'},
        {'key': 'students',  'label': 'الطلاب'},
        {'key': 'classes',   'label': 'الفصول'},
        {'key': 'books',     'label': 'الكتب'},
        {'key': 'salaries',  'label': 'المرتبات'},
        {'key': 'accounts',  'label': 'الحسابات الشهرية'},
        {'key': 'albums',    'label': 'الألبومات'},
        {'key': 'cameras',   'label': 'الكاميرات'},
        {'key': 'roles',     'label': 'توزيع الأدوار'},
        {'key': 'manage',    'label': 'طلبات أولياء الأمور'},
    ]},
    {'role': 'parent', 'label': 'ولي الأمر', 'caps': [
        {'key': 'payments', 'label': 'يشوف سجل المدفوعات'},
        {'key': 'evals',    'label': 'يشوف تقييمات المعلمة'},
        {'key': 'photos',   'label': 'يشوف ألبومات الصور'},
    ]},
]


def role_perms(env):
    """الصلاحيات الفعّالة = الافتراضي + ما حفظه الأونر. دفاعي — لا يرمي أبداً."""
    saved = {}
    raw = env['ir.config_parameter'].sudo().get_param('nursery.role_perms')
    if raw:
        try:
            saved = json.loads(raw)
        except Exception:
            saved = {}
    out = {}
    for role, caps in PERM_DEFAULTS.items():
        out[role] = dict(caps)
        for k, v in (saved.get(role) or {}).items():
            if k in out[role]:
                out[role][k] = bool(v)
    return out


def perm_allowed(env, role, cap):
    """True = مسموح. غير المعروف = مسموح (آمن للأمام)."""
    return role_perms(env).get(role, {}).get(cap, True)


def _mgr_page_blocked(mgr, cap):
    """True لو المديرة (غير الأونر) مقفولة عن صفحة الإدارة دي. الأونر يتخطّى دايماً."""
    return (not mgr.has_group('base.group_system')
            and not perm_allowed(request.env, 'manager', cap))

PAGE_BLOCKED_MSG = 'هذه الصفحة متوقّفة من إدارة الصلاحيات'


def _is_manager():
    u = request.env.user
    return (u.has_group('nursery.group_nursery_manager')
            or u.has_group('base.group_system'))


_TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')


def _manager_by_token(mt):
    """يتحقق من توكن المديرة الصادر عند الدخول."""
    if not mt or not _TOKEN_RE.match(mt):
        return None
    u = request.env['res.users'].sudo().search(
        [('nursery_api_token', '=', mt)], limit=1)
    if not u:
        return None
    if not (u.has_group('nursery.group_nursery_manager')
            or u.has_group('base.group_system')):
        return None
    return u


ROLES_PAGE_TOP = """<!DOCTYPE html>
<html lang="ar" dir="rtl"><head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>توزيع الأدوار</title>
<style>
 *{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,"Segoe UI",Tahoma,sans-serif;}
 body{background:#f0f7f2;min-height:100vh;padding:16px;}
 .top{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap;}
 .top a{background:#14532d;color:#fff;text-decoration:none;padding:9px 16px;border-radius:10px;font-size:13px;font-weight:700;}
 h1{font-size:19px;color:#14532d;margin-bottom:4px;}
 .sub{color:#6b7280;font-size:13px;margin-bottom:16px;}
 .card{background:#fff;border-radius:14px;padding:14px;margin-bottom:12px;box-shadow:0 1px 5px rgba(0,0,0,.07);}
 .u{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:10px 0;border-bottom:1px dashed #e5e7eb;}
 .u:last-child{border:none;}
 .u .info{flex:1;min-width:180px;}
 .u .info b{font-size:15px;}
 .u .info small{color:#9ca3af;display:block;}
 .tag{padding:2px 10px;border-radius:9px;font-size:11px;font-weight:700;}
 .t-owner{background:#111827;color:#fbbf24;} .t-mgr{background:#ede9fe;color:#6d28d9;}
 .t-teach{background:#dcfce7;color:#15803d;} .t-work{background:#fef3c7;color:#b45309;}
 .t-parent{background:#dbeafe;color:#1d4ed8;} .t-none{background:#fee2e2;color:#b91c1c;}
 form{display:inline;}
 button,select{border:1px solid #d1d5db;border-radius:9px;padding:7px 12px;font-size:13px;background:#fff;cursor:pointer;}
 button.go{background:#14532d;color:#fff;border:none;font-weight:700;}
 .msg{background:#dcfce7;color:#15803d;border-radius:10px;padding:10px 14px;margin-bottom:12px;font-size:14px;font-weight:700;}
</style></head><body>
<div class="top"><a href="/nursery-dashboard">◀ الداشبورد</a><a href="/odoo">النظام</a></div>
<h1>👥 توزيع الأدوار</h1>
<div class="sub">أي حد يسجل دخول جديد (بجوجل أو غيره) هيظهر هنا "بدون دور" — اختاري دوره واضغطي تعيين</div>
"""


class NurserySSO(http.Controller):
    """نقطة الدخول الموحّدة: زرار الموقع التسويقي يوجّه هنا."""

    @http.route('/portal-login', type='http', auth='public', website=False, sitemap=False)
    def portal_login(self, **kw):
        # لو داخل بالفعل → ودّيه لمكانه حسب دوره
        if request.env.user and not request.env.user._is_public():
            return request.redirect('/portal-home')
        # ابنِ رابط دخول جوجل من مزوّد OAuth واطلب الرجوع لـ /portal-home
        provider = request.env['auth.oauth.provider'].sudo().search(
            [('enabled', '=', True), ('name', 'ilike', 'google')], limit=1)
        if not provider:
            return request.redirect('/web/login')
        base = request.httprequest.url_root.rstrip('/')
        state = {'d': request.env.cr.dbname, 'p': provider.id,
                 'r': base + '/portal-home'}
        params = werkzeug.urls.url_encode({
            'response_type': 'token',
            'client_id': provider.client_id,
            'redirect_uri': base + '/auth_oauth/signin',
            'scope': provider.scope,
            'state': json.dumps(state),
            # خلي جوجل يعرض اختيار الحساب دايماً (عشان تقدر تغيّر الإيميل)
            'prompt': 'select_account',
        })
        return request.redirect('%s?%s' % (provider.auth_endpoint, params),
                                local=False)

    @http.route('/portal-home', type='http', auth='user', website=False, sitemap=False)
    def portal_home(self, **kw):
        """بعد الدخول بجوجل — يرجّع المستخدم للموقع (مش أودو) حسب دوره."""
        u = request.env.user
        # الأونر / الأدمن → الداشبورد على الموقع (مش أودو)
        if u.has_group('base.group_system'):
            mt = u._ensure_api_token()
            return request.redirect('%s/dashboard/#mt=%s' % (WEBSITE, mt), local=False)
        # مديرة الحضانة → صفحة مراجعة أولياء الأمور على الموقع (بتوكن)
        if u.has_group('nursery.group_nursery_manager'):
            mt = u._ensure_api_token()
            return request.redirect('%s/manage/#mt=%s' % (WEBSITE, mt), local=False)
        # مدرسة / عاملة → صفحة الموظف على الموقع (بتوكن)
        if u._is_internal():
            st = u._ensure_api_token()
            return request.redirect('%s/staff/#st=%s' % (WEBSITE, st), local=False)
        # ولي أمر (بورتال) → صفحة الطفل على الموقع
        student = request.env['nursery.student'].sudo().search(
            _parent_student_domain(u.id), limit=1)
        # لو المديرة اعتمدت الطلب قبل ما ولي الأمر يسجل دخول بجوجل،
        # نربطه دلوقتي حسب إيميله (مطابقة بالضبط — u.login قيمة موثوقة)
        if not student:
            req = request.env['nursery.link.request'].sudo().search(
                [('parent_email', '=', (u.login or '').strip().lower()),
                 ('state', '=', 'linked'),
                 ('matched_student_id', '!=', False)], limit=1)
            if req and req.matched_student_id.active:
                req.matched_student_id._link_parent_user(u)
                student = req.matched_student_id
        if student and student.portal_token:
            return request.redirect(
                '%s/me/#t=%s' % (WEBSITE, student.portal_token), local=False)
        # ولي أمر لسه ماتربطش بطفل → صفحة انتظار على الموقع
        return request.redirect(
            '%s/me/#pending=%s' % (WEBSITE, u.login), local=False)

    @http.route('/site/photos', type='http', auth='public', website=False,
                methods=['GET'], csrf=False, sitemap=False)
    def site_photos(self, limit=12, **kw):
        """صور مختارة للمعرض على الموقع التسويقي — Drive IDs فقط."""
        import re as _re
        try:
            limit = max(1, min(24, int(limit)))
        except (TypeError, ValueError):
            limit = 12
        safe = _re.compile(r'^[A-Za-z0-9_-]+$')
        albums = request.env['nursery.album'].sudo().search(
            [('active', '=', True), ('site_visible', '=', True)])
        ids = []
        # ناخد صور بالتناوب من كل ألبوم عشان تكون متنوعة
        pools = [list(a.photo_ids) for a in albums]
        i = 0
        while len(ids) < limit and any(p[i:] for p in pools):
            for p in pools:
                if i < len(p) and len(ids) < limit:
                    did = p[i].drive_id
                    if did and safe.match(did):
                        ids.append(did)
            i += 1
        body = json.dumps({'photos': ids})
        return request.make_response(body, headers=[
            ('Content-Type', 'application/json'),
            ('Access-Control-Allow-Origin', WEBSITE),
            ('Cache-Control', 'public, max-age=600'),
        ])

    # ============ APIs للموقع (CORS) ============

    def _role_redirect(self, u):
        """يبني رابط التوجيه للموقع حسب دور المستخدم (نفس منطق portal_home)."""
        u = u.sudo()
        if u.has_group('base.group_system'):
            return '%s/dashboard/#mt=%s' % (WEBSITE, u._ensure_api_token())
        if u.has_group('nursery.group_nursery_manager'):
            return '%s/manage/#mt=%s' % (WEBSITE, u._ensure_api_token())
        if u._is_internal():
            return '%s/staff/#st=%s' % (WEBSITE, u._ensure_api_token())
        Stu = request.env['nursery.student'].sudo()
        student = Stu.search(_parent_student_domain(u.id), limit=1)
        if not student:
            req = request.env['nursery.link.request'].sudo().search(
                [('parent_email', '=', (u.login or '').strip().lower()),
                 ('state', '=', 'linked'), ('matched_student_id', '!=', False)], limit=1)
            if req and req.matched_student_id.active:
                req.matched_student_id._link_parent_user(u)
                student = req.matched_student_id
        if student and student.portal_token:
            return '%s/me/#t=%s' % (WEBSITE, student.portal_token)
        return '%s/me/#pending=%s' % (WEBSITE, u.login)

    @http.route('/api/login', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_login(self, email=None, password=None, **kw):
        """دخول بالبريد وكلمة المرور من الموقع (بدون واجهة أودو) → توكن + توجيه حسب الدور."""
        login = (email or '').strip().lower()
        if not login or not password:
            return {'ok': False, 'error': 'يرجى إدخال البريد الإلكتروني وكلمة المرور'}
        uid = None
        try:
            request.session.authenticate(
                request.db, {'type': 'password', 'login': login, 'password': password})
            uid = request.session.uid
        except Exception:
            uid = None
        if not uid:
            return {'ok': False, 'error': 'بيانات الدخول غير صحيحة'}
        user = request.env['res.users'].sudo().browse(uid)
        return {'ok': True, 'redirect': self._role_redirect(user)}


    @http.route('/api/parent-signup', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_parent_signup(self, parent_name=None, parent_email=None,
                          parent_phone=None, child_name=None, **kw):
        """ولي الأمر يسجّل من الموقع ويقول اسم طفله → يتعمل طلب ربط."""
        email = (parent_email or '').strip().lower()
        child = (child_name or '').strip()
        if not email or '@' not in email or not child or len(child) > 120:
            return {'ok': False, 'error': 'الإيميل واسم الطفل مطلوبين'}
        Req = request.env['nursery.link.request'].sudo()
        # سقف مكافحة السبام: 3 طلبات معلّقة كحد أقصى لكل إيميل
        if Req.search_count([('parent_email', '=', email),
                             ('state', '=', 'pending')]) >= 3:
            return {'ok': True, 'enrolled': False, 'child': child}
        # امنع التكرار: نفس الإيميل + نفس الطفل ولسه pending
        dup = Req.search([('parent_email', '=', email),
                          ('child_name', '=', child),
                          ('state', '=', 'pending')], limit=1)
        req = dup or Req.create_from_site(parent_name, email, parent_phone, child)
        # gclid جاي من الموقع (query string) — ننضّفه لأنه مدخل خارجي.
        g = re.sub(r'[^A-Za-z0-9_-]', '', (kw.get('gclid') or ''))[:255]
        if g and not req.gclid:
            req.sudo().write({'gclid': g})
        return {'ok': True, 'enrolled': req.is_enrolled,
                'child': req.child_name}

    @http.route('/api/parent/notify', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_parent_notify(self, email=None, **kw):
        """ولي الأمر (بانتظار الربط) يبلّغ الإدارة داخل النظام أنه سجّل.
        يعلّم طلبه كـ (بلّغ) فيظهر منبّهاً في صفحة الطلبات عند المديرة."""
        email = (email or '').strip().lower()
        if not email or '@' not in email:
            return {'ok': False, 'error': 'إيميل غير صالح'}
        Req = request.env['nursery.link.request'].sudo()
        reqs = Req.search([('parent_email', '=', email),
                           ('state', '=', 'pending')])
        if not reqs:
            # لا يوجد طلب معلّق بهذا الإيميل — وجّهه للتسجيل أولاً
            return {'ok': False, 'no_request': True,
                    'error': 'لم نجد طلب تسجيل بهذا البريد — سجّل من الصفحة الرئيسية أولاً'}
        reqs.write({'nudged': True, 'nudged_at': fields.Datetime.now()})
        return {'ok': True, 'count': len(reqs)}

    @http.route('/api/manager/pending', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_pending(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'manage'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        # المُبلِّغون أولاً، ثم الأحدث
        reqs = request.env['nursery.link.request'].sudo().search(
            [('state', '=', 'pending')],
            order='nudged desc, nudged_at desc, create_date desc', limit=100)
        students = request.env['nursery.student'].sudo().search(
            [('active', '=', True)], order='name')
        return {
            'ok': True, 'manager': mgr.name,
            'requests': [{
                'id': r.id, 'parent_name': r.parent_name,
                'parent_email': r.parent_email, 'parent_phone': r.parent_phone or '',
                'child_name': r.child_name,
                'enrolled': r.is_enrolled,
                'nudged': bool(r.nudged),
                'matched_id': r.matched_student_id.id or False,
                'matched_name': r.matched_student_id.name or '',
                'matched_phone': r.matched_student_id.guardian_phone or '',
                'phone_match': bool(r.parent_phone and r.matched_student_id.guardian_phone
                                    and r.parent_phone.strip() == r.matched_student_id.guardian_phone.strip()),
            } for r in reqs],
            'students': [{'id': s.id, 'name': s.name} for s in students],
        }

    @http.route('/api/manager/link', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_link(self, mt=None, request_id=None, student_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            req = request.env['nursery.link.request'].sudo().browse(int(request_id))
            assert req.exists()
        except Exception:
            return {'ok': False, 'error': 'طلب غير موجود'}
        if student_id:
            try:
                req.matched_student_id = int(student_id)
            except (TypeError, ValueError):
                return {'ok': False, 'error': 'طفل غير صحيح'}
        try:
            req.action_link()
        except Exception as ex:
            return {'ok': False, 'error': str(ex)}
        return {'ok': True}

    @http.route('/api/manager/reject', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_reject(self, mt=None, request_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            req = request.env['nursery.link.request'].sudo().browse(int(request_id))
            if not req.exists():
                return {'ok': False, 'error': 'طلب غير موجود'}
            req.state = 'rejected'
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'طلب غير موجود'}
        return {'ok': True}

    # ==================== إدارة الفصول ====================
    @http.route('/api/manager/classes', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_classes(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'classes'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        Cls = request.env['nursery.class'].sudo()
        Emp = request.env['hr.employee'].sudo()
        Stu = request.env['nursery.student'].sudo()
        classes = Cls.search([], order='name')
        teachers = Emp.search([('active', '=', True)], order='name')
        students = Stu.search(self._visible_student_domain(), order='name')
        return {
            'ok': True, 'manager': mgr.name,
            'classes': [{
                'id': c.id, 'name': c.name,
                'teacher_id': c.teacher_id.id or False,
                'teacher_name': c.teacher_id.name or '',
                'capacity': c.capacity,
                'student_count': len(students.filtered(lambda s: s.class_id.id == c.id)),
                'student_ids': students.filtered(lambda s: s.class_id.id == c.id).ids,
            } for c in classes],
            'teachers': [{'id': t.id, 'name': t.name} for t in teachers],
            'students': [{'id': s.id, 'name': s.name,
                          'class_id': s.class_id.id or False,
                          'linked': self._student_link_meta(s)['linked']} for s in students],
        }

    @http.route('/api/manager/class/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_class_save(self, mt=None, id=None, name=None,
                               teacher_id=None, capacity=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        name = (name or '').strip().replace('<', '').replace('>', '')
        if not name:
            return {'ok': False, 'error': 'اكتب اسم الفصل'}
        vals = {'name': name}
        try:
            vals['teacher_id'] = int(teacher_id) if teacher_id else False
        except (TypeError, ValueError):
            vals['teacher_id'] = False
        try:
            if capacity:
                vals['capacity'] = max(1, int(capacity))
        except (TypeError, ValueError):
            pass
        Cls = request.env['nursery.class'].sudo()
        if id:
            c = Cls.browse(int(id))
            if not c.exists():
                return {'ok': False, 'error': 'فصل غير موجود'}
            c.write(vals)
            cid = c.id
        else:
            cid = Cls.create(vals).id
        return {'ok': True, 'id': cid}

    @http.route('/api/manager/class/delete', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_class_delete(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            c = request.env['nursery.class'].sudo().browse(int(id))
            if c.exists():
                c.student_ids.write({'class_id': False})
                c.unlink()
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'فصل غير موجود'}
        return {'ok': True}

    @http.route('/api/manager/class/students', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_class_students(self, mt=None, id=None, student_ids=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            c = request.env['nursery.class'].sudo().browse(int(id))
            assert c.exists()
        except Exception:
            return {'ok': False, 'error': 'فصل غير موجود'}
        ids = []
        for x in (student_ids or []):
            try:
                ids.append(int(x))
            except (TypeError, ValueError):
                pass
        Stu = request.env['nursery.student'].sudo()
        newset = Stu.browse(ids).exists()
        (c.student_ids - newset).write({'class_id': False})
        newset.write({'class_id': c.id})
        return {'ok': True, 'count': len(newset)}

    # ==================== الكاميرات + تسجيل الوجه ====================
    def _face_row(self, s):
        """صف طالب لشاشة الكاميرات: حالة تسجيل الوجه."""
        return {
            'id': s.id, 'name': s.name,
            'class_id': s.class_id.id or False,
            'class_name': s.class_id.name or '',
            'photo_count': s.face_photo_count,
            'ready': s.face_ready,
            'enrolled': s.face_enrolled,
        }

    @http.route('/api/today', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_today(self, **kw):
        """تاريخ ووقت السيرفر بتوقيت الرياض (UTC+3، بلا توقيت صيفي) —
        عشان الصفحات ما تعتمدش على ساعة جهاز المستخدم (قد تكون غلط)."""
        import datetime
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=3)
        return {'ok': True, 'date': now.strftime('%Y-%m-%d'),
                'datetime': now.strftime('%Y-%m-%d %H:%M:%S'), 'tz': 'Asia/Riyadh'}

    @http.route('/api/health/sys', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_health_sys(self, key=None, **kw):
        """صحّة نظام n8n-vm (قرص/ذاكرة) — يقرأها الفاحص الأمني على montasercloud
        ليراقب السيرفرين. محميّة بسرّ في ir.config_parameter."""
        want = request.env['ir.config_parameter'].sudo().get_param('nursery.sys_health_key')
        if not want or key != want:
            return {'ok': False}
        import shutil
        t, u, fr = shutil.disk_usage('/')
        out = {'ok': True, 'disk_pct': round(u * 100.0 / t),
               'disk_free_gb': round(fr / 1e9, 1), 'disk_total_gb': round(t / 1e9)}
        try:
            with open('/proc/meminfo') as fh:
                mi = {}
                for ln in fh:
                    p = ln.split(':')
                    if len(p) == 2:
                        mi[p[0]] = int(p[1].split()[0])
            out['mem_pct'] = round((mi['MemTotal'] - mi.get('MemAvailable', mi['MemFree']))
                                   * 100.0 / mi['MemTotal'])
        except Exception:
            out['mem_pct'] = 0
        return out

    @http.route('/api/manager/cctv', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_cctv(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'cameras'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        Cls = request.env['nursery.class'].sudo()
        Stu = request.env['nursery.student'].sudo()
        classes = Cls.search([], order='name')
        students = Stu.search([('active', '=', True)], order='class_id, name')
        return {
            'ok': True, 'manager': mgr.name,
            'classes': [{
                'id': c.id, 'name': c.name,
                'teacher_name': c.teacher_id.name or '',
                'student_count': c.student_count,
                'camera_channel': c.camera_channel or 0,
            } for c in classes],
            'students': [self._face_row(s) for s in students],
        }

    @http.route('/api/manager/class/camera', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_class_camera(self, mt=None, id=None, channel=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            c = request.env['nursery.class'].sudo().browse(int(id))
            assert c.exists()
        except Exception:
            return {'ok': False, 'error': 'فصل غير موجود'}
        try:
            ch = int(channel or 0)
            if ch < 0 or ch > 64:
                return {'ok': False, 'error': 'رقم قناة غير صالح'}
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'رقم قناة غير صالح'}
        c.write({'camera_channel': ch})
        return {'ok': True, 'id': c.id, 'channel': ch}

    @http.route('/api/manager/student/faces', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_faces(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            s = request.env['nursery.student'].sudo().browse(int(id))
            assert s.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        photos = []
        for p in s.face_photo_ids:
            thumb = p.image_256 or p.image
            photos.append({
                'id': p.id,
                'thumb': ('data:image/jpeg;base64,%s'
                          % (thumb.decode() if isinstance(thumb, bytes) else thumb)) if thumb else '',
                'quality': p.quality or '',
                'embedded': p.embedded,
            })
        return {'ok': True, 'student': s.name,
                'ready': s.face_ready, 'enrolled': s.face_enrolled,
                'photos': photos}

    @http.route('/api/manager/student/face/add', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_face_add(self, mt=None, id=None, image=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            s = request.env['nursery.student'].sudo().browse(int(id))
            assert s.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        if not image:
            return {'ok': False, 'error': 'لا توجد صورة'}
        # نقبل data-URI أو base64 خام؛ نجرّد الترويسة
        data = image.split(',', 1)[1] if ',' in image[:64] else image
        # تحقّق حقيقي قبل الحفظ: فُكّ الترميز، احسب الحجم المُفكوك، وتأكّد أنها صورة فعلاً
        import base64 as _b64, binascii as _bx
        try:
            raw = _b64.b64decode(data, validate=True)
        except (_bx.Error, ValueError):
            return {'ok': False, 'error': 'صورة غير صالحة'}
        if len(raw) > 6 * 1024 * 1024:               # 6MB مفكوكة (≈8MB base64)
            return {'ok': False, 'error': 'الصورة كبيرة جداً'}
        # فحص البصمة السحرية: JPEG / PNG / GIF / WEBP فقط
        is_img = (raw[:3] == b'\xff\xd8\xff' or raw[:8] == b'\x89PNG\r\n\x1a\n'
                  or raw[:6] in (b'GIF87a', b'GIF89a')
                  or (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'))
        if not is_img:
            return {'ok': False, 'error': 'الملف ليس صورة صالحة'}
        # الحفظ داخل savepoint: لو فشل معالجة الصورة (fields.Image) تُلغى الإضافة بالكامل
        try:
            with request.env.cr.savepoint():
                p = request.env['nursery.face.photo'].sudo().create({
                    'student_id': s.id, 'image': data,
                })
                p.flush_recordset()   # يُجبر معالجة الصورة الآن داخل الـsavepoint
        except Exception:
            return {'ok': False, 'error': 'صورة غير صالحة'}
        return {'ok': True, 'photo_id': p.id,
                'photo_count': s.face_photo_count, 'ready': s.face_ready}

    @http.route('/api/manager/student/face/del', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_face_del(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            p = request.env['nursery.face.photo'].sudo().browse(int(id))
            assert p.exists()
        except Exception:
            return {'ok': False, 'error': 'صورة غير موجودة'}
        s = p.student_id
        p.unlink()
        s.write({'face_enrolled': False})
        return {'ok': True, 'photo_count': s.face_photo_count, 'ready': s.face_ready}

    # ==================== المرتبات + الباي سليب ====================
    def _cur_term(self):
        return request.env['ir.config_parameter'].sudo().get_param(
            'nursery.cur_term', 'term_2026')

    @http.route('/api/manager/salaries', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_salaries(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not mgr.has_group('base.group_system') and not perm_allowed(request.env, 'manager', 'salaries'):
            return {'ok': False, 'error': 'المرتبات متوقّفة من إدارة الصلاحيات'}
        term = self._cur_term()
        Emp = request.env['hr.employee'].sudo()
        Sal = request.env['nursery.salary'].sudo()
        Ded = request.env['nursery.deduction'].sudo()
        rows = []
        for emp in Emp.search([('active', '=', True)], order='name'):
            sal = (Sal.search([('employee_id', '=', emp.id), ('term', '=', term)], limit=1)
                   or Sal.search([('teacher', '=', emp.name), ('term', '=', term)], limit=1))
            ded_total = sum(Ded.search([('employee_id', '=', emp.id),
                                        ('state', '=', 'confirmed')]).mapped('amount'))
            expected = sal.expected if sal else 0.0
            actual = sal.actual if sal else 0.0
            rows.append({
                'employee_id': emp.id, 'name': emp.name,
                'job': emp.job_title or '',
                'salary_id': sal.id or False,
                'expected': expected, 'actual': actual,
                'paid_date': sal.paid_date.strftime('%Y-%m-%d') if (sal and sal.paid_date) else '',
                'deductions_total': ded_total,
                'net': (actual or expected) - ded_total,
                'exempt': emp.attendance_exempt,
            })
        return {'ok': True, 'manager': mgr.name, 'term': term,
                'term_label': dict(Sal._fields['term'].selection).get(term, term),
                'rows': rows}

    @http.route('/api/manager/salary/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_salary_save(self, mt=None, employee_id=None,
                                expected=None, actual=None, paid_date=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not mgr.has_group('base.group_system') and not perm_allowed(request.env, 'manager', 'salaries'):
            return {'ok': False, 'error': 'المرتبات متوقّفة من إدارة الصلاحيات'}
        try:
            emp = request.env['hr.employee'].sudo().browse(int(employee_id))
            assert emp.exists()
        except Exception:
            return {'ok': False, 'error': 'موظف غير موجود'}
        term = self._cur_term()
        Sal = request.env['nursery.salary'].sudo()
        sal = (Sal.search([('employee_id', '=', emp.id), ('term', '=', term)], limit=1)
               or Sal.search([('teacher', '=', emp.name), ('term', '=', term)], limit=1))

        def num(v):
            try:
                return max(0.0, float(v))
            except (TypeError, ValueError):
                return 0.0
        vals = {'expected': num(expected), 'actual': num(actual),
                'employee_id': emp.id, 'teacher': emp.name, 'term': term}
        vals['paid_date'] = (paid_date or '').strip() or False
        if sal:
            sal.write(vals)
        else:
            Sal.create(vals)
        return {'ok': True}

    @http.route('/api/manager/payslip', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_payslip(self, mt=None, employee_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not mgr.has_group('base.group_system') and not perm_allowed(request.env, 'manager', 'salaries'):
            return {'ok': False, 'error': 'المرتبات متوقّفة من إدارة الصلاحيات'}
        try:
            emp = request.env['hr.employee'].sudo().browse(int(employee_id))
            assert emp.exists()
        except Exception:
            return {'ok': False, 'error': 'موظف غير موجود'}
        term = self._cur_term()
        Sal = request.env['nursery.salary'].sudo()
        sal = (Sal.search([('employee_id', '=', emp.id), ('term', '=', term)], limit=1)
               or Sal.search([('teacher', '=', emp.name), ('term', '=', term)], limit=1))
        Ded = request.env['nursery.deduction'].sudo()
        deds = Ded.search([('employee_id', '=', emp.id), ('state', '=', 'confirmed')], order='date')
        LBL = {'late': 'تأخير', 'absence': 'غياب', 'absence_auth': 'غياب بإذن'}
        ded_rows = [{
            'date': d.date.strftime('%Y-%m-%d') if d.date else '',
            'label': LBL.get(d.dtype, d.dtype), 'days': d.days, 'amount': d.amount,
        } for d in deds]
        ded_total = sum(deds.mapped('amount'))
        expected = sal.expected if sal else 0.0
        actual = sal.actual if sal else 0.0
        gross = actual or expected
        company = request.env['res.company'].sudo().search([], limit=1)
        return {'ok': True, 'payslip': {
            'name': emp.name, 'job': emp.job_title or '',
            'term_label': dict(Sal._fields['term'].selection).get(term, term),
            'expected': expected, 'actual': actual, 'gross': gross,
            'deductions': ded_rows, 'deductions_total': ded_total,
            'net': gross - ded_total,
            'nursery': company.name or 'روضة كوكب الطفل الحر',
        }}

    # ==================== الطلاب + الدفعات ====================
    _AR_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

    def _num(self, v):
        try:
            return max(0.0, float(v))
        except (TypeError, ValueError):
            return 0.0


    def _month_student_domain(self, ym, exclude_ids=None):
        """طلاب الشهر الفعليون فقط؛ الحجز المستقبلي لا يدخل قبل تاريخ بدايته."""
        last_day = self._month_last_day(ym)
        domain = [
            ('active', '=', True),
            '|', ('joining_date', '=', False), ('joining_date', '<=', last_day),
        ]
        if exclude_ids:
            domain += [('id', 'not in', list(exclude_ids))]
        return domain

    def _visible_student_domain(self):
        """طلاب التشغيل الحاليين فقط؛ حجوزات السنة الجديدة تظهر من سبتمبر."""
        start = request.env['ir.config_parameter'].sudo().get_param(
            'nursery.term_2027_start', '2026-09-01')
        domain = [('active', '=', True)]
        if fields.Date.today().strftime('%Y-%m-%d') < start:
            domain.append(('term', '!=', 'term_2027'))
        return domain

    def _cleanup_future_month_fees(self):
        """إزالة أسطر الحجز غير المدفوعة من الشهور المفتوحة القديمة."""
        Month = request.env['nursery.month'].sudo()
        for month in Month.search([('state', '=', 'open')]):
            last_day = self._month_last_day(month.ym)
            future = month.fee_ids.filtered(
                lambda f: f.student_id and f.student_id.joining_date
                and f.student_id.joining_date > fields.Date.from_string(last_day)
                and (f.paid or 0.0) <= 0.0)
            if future:
                future.unlink()

    def _student_link_meta(self, s):
        """حالة ربط ولي الأمر من سجل الطالب + آخر طلب ربط مطابق.

        طلبات سبتمبر تحفظ بريد ولي الأمر في nursery.link.request، بينما باقي
        الصفحات تقرأ من سجل الطالب. هذا الموحّد يمنع ظهور الطالب «غير مرتبط»
        في صفحة، و«مرتبط» في صفحة أخرى بعد اعتماد/حفظ الربط.
        """
        req = request.env['nursery.link.request'].sudo().search([
            ('matched_student_id', '=', s.id),
            ('state', 'in', ('pending', 'linked')),
        ], order='write_date desc, create_date desc', limit=1)
        linked = bool(s.parent_user_id or s.parent_user_ids or
                      (req and req.state == 'linked'))
        parent_user = s.parent_user_id or s.parent_user_ids[:1]
        parent_email = ''
        if req:
            parent_email = req.parent_email or ''
        elif parent_user:
            parent_email = parent_user.email or parent_user.login or ''
        return {
            'linked': linked,
            'link_state': 'linked' if linked else ((req.state if req else '') or 'none'),
            'link_request_id': req.id if req else False,
            'parent_name': (req.parent_name if req else '') or s.guardian_name or '',
            'parent_email': parent_email,
            'parent_phone': (req.parent_phone if req else '') or s.guardian_phone or '',
        }

    def _sync_parent_link(self, student, parent_name=None, parent_email=None,
                          parent_phone=None):
        """احفظ/حدّث طلب ربط ولي الأمر ثم اربطه فوراً لو حسابه موجود."""
        email = (parent_email or '').strip().lower()
        if not email:
            return self._student_link_meta(student)
        Req = request.env['nursery.link.request'].sudo()
        req = Req.search([
            ('parent_email', '=', email),
            ('matched_student_id', '=', student.id),
            ('state', 'in', ('pending', 'linked')),
        ], order='write_date desc, create_date desc', limit=1)
        if not req:
            req = Req.search([
                ('parent_email', '=', email),
                ('child_name', '=', student.name),
                ('state', 'in', ('pending', 'linked')),
            ], order='write_date desc, create_date desc', limit=1)
        if not req:
            req = Req.create_from_site(parent_name or student.guardian_name,
                                       email, parent_phone or student.guardian_phone,
                                       student.name)
        vals = {'matched_student_id': student.id, 'child_name': student.name}
        clean_name = (parent_name or '').strip().replace('<', '').replace('>', '')[:120]
        clean_phone = (parent_phone or '').strip()[:40]
        if clean_name:
            vals['parent_name'] = clean_name
        if clean_phone:
            vals['parent_phone'] = clean_phone
        req.write(vals)
        user = request.env['res.users'].sudo().search([
            '&', ('active', '=', True), '|',
            ('login', '=ilike', email), ('email', '=ilike', email),
        ], limit=1)
        if user:
            req.action_link()
            student = request.env['nursery.student'].sudo().browse(student.id)
        return self._student_link_meta(student)

    def _student_row(self, s):
        today = fields.Date.today()
        status, days = 'none', 0
        if s.paid_until:
            days = (s.paid_until - today).days
            if days < 0:
                status = 'overdue'
            elif days <= 3:
                status = 'due_soon'
            else:
                status = 'paid'
        elif s.paid:
            status = 'paid'
        last = s.payment_ids.filtered(
            lambda p: p.payment_type != 'books'
        ).sorted(lambda p: (p.date or fields.Date.today()), reverse=True)[:1]
        link = self._student_link_meta(s)
        books_due = s.books_fees or 0.0
        books_paid = s.books_paid or 0.0
        books_remaining = max(0.0, books_due - books_paid)
        return {
            'id': s.id, 'name': s.name,
            'class_id': s.class_id.id or False,
            'class_name': s.class_id.name or '',
            'level': s.level or '',
            'level_label': STUDENT_LEVEL_LABELS.get(s.level, s.level or ''),
            'guardian_name': s.guardian_name or '',
            'father_name': s.father_name or '',
            'mother_name': s.mother_name or '',
            'guardian_phone': s.guardian_phone or '',
            'fees': s.fees or 0.0,
            'books_due': round(books_due, 2),
            'books_paid': round(books_paid, 2),
            'books_remaining': round(books_remaining, 2),
            'books_status': ('paid' if books_remaining <= 0.01 else
                             ('partial' if books_paid > 0.01 else 'unpaid')),
            'total_paid': s.total_paid or 0.0,
            'paid': bool(s.paid),
            'paid_at': s.paid_at.strftime('%Y-%m-%d') if s.paid_at else '',
            'paid_until': s.paid_until.strftime('%Y-%m-%d') if s.paid_until else '',
            'joining_date': s.joining_date.strftime('%Y-%m-%d') if s.joining_date else '',
            'term': s.term or '',
            'term_label': dict(s._fields['term'].selection).get(s.term, s.term or ''),
            'remark': s.remark or '',
            'linked': link['linked'],
            'link_state': link['link_state'],
            'link_request_id': link['link_request_id'],
            'parent_name': link['parent_name'],
            'parent_email': link['parent_email'],
            'parent_phone': link['parent_phone'],
            'last_amount': (last.amount if last else 0.0),
            'last_date': (last.date.strftime('%Y-%m-%d') if (last and last.date) else ''),
            'last_days': (last.days if last else 0),
            'payments_count': len(s.payment_ids.filtered(
                lambda p: p.payment_type != 'books')),
            'day_basis': DAY_BASIS,
            'status': status, 'days': days,
        }

    @http.route('/api/manager/students', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_students(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'students'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        Stu = request.env['nursery.student'].sudo()
        Cls = request.env['nursery.class'].sudo()
        students = Stu.search(self._visible_student_domain(), order='name')
        classes = Cls.search([], order='name')
        return {
            'ok': True, 'manager': mgr.name,
            'students': [self._student_row(s) for s in students],
            'classes': [{'id': c.id, 'name': c.name} for c in classes],
            'alert_staff': self._alert_staff(),
        }

    def _alert_staff(self):
        """أرقام واتساب المسؤولات عن تذكير أولياء الأمور (نسرين/سمر…) — قابلة للضبط من الموقع."""
        raw = request.env['ir.config_parameter'].sudo().get_param('nursery.alert_staff')
        try:
            lst = json.loads(raw) if raw else []
        except Exception:
            lst = []
        out = []
        for x in lst[:4]:
            if isinstance(x, dict) and (x.get('name') or '').strip():
                out.append({'name': str(x['name'])[:40], 'phone': re.sub(r'\D', '', str(x.get('phone') or ''))[:15]})
        return out or [{'name': 'نسرين', 'phone': ''}, {'name': 'سمر', 'phone': ''}]

    @http.route('/api/manager/crm_sso', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_crm_sso(self, mt=None, **kw):
        """دخول تلقائي للـCRM (Chatwoot) بدون كلمة سر: نُصدِر رابط دخول لحظياً عبر Platform API
        بناءً على توكن المدير الحالي. الربط مدير→مستخدم CRM من إعدادات محفوظة."""
        import requests
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        ICP = request.env['ir.config_parameter'].sudo()
        token = (ICP.get_param('nursery.crm_platform_token') or '').strip()
        base = (ICP.get_param('nursery.crm_url') or 'https://crm.montessori-ksa.com').rstrip('/')
        if not token:
            return {'ok': False, 'error': 'الدخول التلقائي لم يُفعَّل بعد'}
        # تحديد مستخدم الـCRM: خريطة بريد→معرّف، ثم الأونر، ثم الافتراضي
        try:
            umap = json.loads(ICP.get_param('nursery.crm_user_map') or '{}')
        except Exception:
            umap = {}
        email = (mgr.email or mgr.login or '').strip().lower()
        cw_uid = umap.get(email)
        if not cw_uid and mgr.has_group('base.group_system'):
            cw_uid = ICP.get_param('nursery.crm_owner_uid')
        if not cw_uid:
            cw_uid = ICP.get_param('nursery.crm_default_uid')
        if not cw_uid:
            return {'ok': False, 'error': 'لا يوجد حساب مراسلة مربوط بك'}
        try:
            r = requests.get('%s/platform/api/v1/users/%s/login' % (base, cw_uid),
                             headers={'api_access_token': token}, timeout=15)
            url = (r.json() or {}).get('url')
            if not url:
                return {'ok': False, 'error': 'تعذّر توليد رابط الدخول'}
            return {'ok': True, 'url': url}
        except Exception:
            return {'ok': False, 'error': 'تعذّر الاتصال بنظام الرسائل'}

    @http.route('/api/manager/notifications', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_notifications(self, mt=None, **kw):
        """عدّاد التنبيهات الموحّد للجرس 🔔 — كل ما يجب أن يعرفه المدير/الأونر فور الدخول."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        env = request.env
        today = fields.Date.today()
        students = env['nursery.student'].sudo().search(self._visible_student_domain())
        overdue, due_today, due_soon, no_join, no_phone = [], [], [], [], []
        for s in students:
            if s.paid_until:
                d = (s.paid_until - today).days
                if d < 0:
                    overdue.append(s.name)
                elif d == 0:
                    due_today.append(s.name)
                elif d <= 3:
                    due_soon.append(s.name)
            if not s.joining_date:
                no_join.append(s.name)
            if not s.guardian_phone:
                no_phone.append(s.name)
        try:
            pending_links = env['nursery.link.request'].sudo().search_count([('state', '=', 'pending')])
        except Exception:
            pending_links = 0
        try:
            pending_msgs = env['nursery.message'].sudo().search_count([('state', '=', 'pending')])
        except Exception:
            pending_msgs = 0
        to_buy = 0
        try:
            from .books import _effective_levels
            eff, _src = _effective_levels(env, students)
            for b in env['nursery.book'].sudo().search([('active', '=', True)]):
                issued = set(mv.student_id.id for mv in b.move_ids
                             if mv.move_type == 'out' and mv.student_id)
                missing = sum(1 for s in students
                              if eff.get(s.id) == b.level and s.id not in issued)
                to_buy += max(0, missing - int(b.stock_qty))
        except Exception:
            to_buy = 0
        # مواعيد الزيارات القادمة. when_dt مخزّن UTC، والمقارنة بتوقيت الرياض
        # عشان «النهاردة» تبقى النهاردة عند المستخدم مش عند الخادم.
        visits_today, visits_soon = [], []
        try:
            import pytz as _pytz
            _tz = _pytz.timezone('Asia/Riyadh')
            _now_local = fields.Datetime.now().replace(tzinfo=_pytz.UTC).astimezone(_tz)
            _today_local = _now_local.date()
            _V = env['nursery.visit'].sudo().search(
                [('state', '=', 'scheduled')], order='when_dt asc', limit=200)
            for _v in _V:
                if not _v.when_dt:
                    continue
                _d = _v.when_dt.replace(tzinfo=_pytz.UTC).astimezone(_tz)
                _delta = (_d.date() - _today_local).days
                _label = '%s — %s' % (_v.lead_name or 'بدون اسم', _d.strftime('%H:%M'))
                if _delta == 0 and _d >= _now_local:
                    visits_today.append(_label)
                elif 1 <= _delta <= 3:
                    visits_soon.append('%s (%s)' % (_label, _d.strftime('%d/%m')))
        except Exception:
            visits_today, visits_soon = [], []

        items = []

        def add(key, label, count, url, names=None, tone='info'):
            if count:
                items.append({'key': key, 'label': label, 'count': count,
                              'url': url, 'names': (names or [])[:8], 'tone': tone})

        try:
            from .funnel import new_leads_cached
            _lc, _ln = new_leads_cached()
            add('new_leads', 'عملاء محتملون جدد على واتساب', _lc,
                '/funnel/', _ln, 'warn')
        except Exception:
            pass
        add('visits_today', 'زيارات النهاردة', len(visits_today),
            '/visits/', visits_today, 'warn')
        add('visits_soon', 'زيارات خلال ٣ أيام', len(visits_soon),
            '/visits/', visits_soon, 'info')
        add('overdue', 'متأخرون في السداد', len(overdue), '/students/', overdue, 'danger')
        add('due_today', 'مستحق اليوم', len(due_today), '/students/', due_today, 'warn')
        add('due_soon', 'اقترب موعدهم (خلال ٣ أيام)', len(due_soon), '/students/', due_soon, 'info')
        add('links', 'طلبات أولياء أمور بانتظار الربط', pending_links, '/manage/', None, 'warn')
        add('msgs', 'رسائل معلمات بانتظار الموافقة', pending_msgs, 'https://odoo.montessori-ksa.com', None, 'warn')
        add('books', 'نسخ كتب مطلوب شراؤها', to_buy, '/books/', None, 'info')
        add('nojoin', 'طلاب بدون تاريخ التحاق', len(no_join), '/students/', no_join, 'warn')
        add('nophone', 'طلاب بدون رقم ولي أمر', len(no_phone), '/students/', no_phone, 'info')
        return {'ok': True, 'items': items,
                'total': sum(i['count'] for i in items)}

    def _ai_chatwoot_stats(self):
        """إحصاءات واتساب الحية من Chatwoot، مع كاش قصير لتفادي إبطاء الصفحة."""
        cached_at = _AI_CHATWOOT_CACHE.get('at')
        if (cached_at and _AI_CHATWOOT_CACHE.get('data')
                and (datetime.utcnow() - cached_at).total_seconds() < 180):
            return dict(_AI_CHATWOOT_CACHE['data'])

        ICP = request.env['ir.config_parameter'].sudo()
        token = (ICP.get_param('nursery.chatwoot_token') or '').strip()
        empty = {
            'available': False, 'source': 'Chatwoot / WhatsApp',
            'sent_today': 0, 'received_today': 0,
            'new_conversations_today': 0, 'open_conversations': 0,
            'waiting_reply': 0, 'unread_conversations': 0,
        }
        if not token:
            _AI_CHATWOOT_CACHE.update({'at': datetime.utcnow(), 'data': empty})
            return dict(empty)

        try:
            import pytz as _pytz
            import requests

            base = (ICP.get_param('nursery.crm_url') or
                    'https://crm.montessori-ksa.com').rstrip('/')
            account_id = int(ICP.get_param('nursery.crm_account_id') or 1)
            inbox_id = int(ICP.get_param('nursery.crm_whatsapp_inbox_id') or 1)
            headers = {'api_access_token': token, 'Accept': 'application/json'}
            tz = _pytz.timezone('Asia/Riyadh')
            now_local = datetime.utcnow().replace(tzinfo=_pytz.UTC).astimezone(tz)
            start_local = tz.localize(datetime.combine(now_local.date(), dt_time.min))

            start_ts = int(start_local.timestamp())
            until_ts = int(now_local.timestamp())

            def report(metric):
                response = requests.get(
                    '%s/api/v2/accounts/%s/reports' % (base, account_id),
                    params={
                        'metric': metric, 'type': 'inbox', 'id': inbox_id,
                        'since': start_ts,
                        'until': until_ts,
                    }, headers=headers, timeout=15)
                response.raise_for_status()
                rows = response.json() or []
                return int(round(sum(float(row.get('value') or 0)
                                     for row in rows if isinstance(row, dict)
                                     and start_ts <= int(row.get('timestamp') or 0)
                                     <= until_ts)))

            waiting = unread = processed = total_open = 0
            page = 1
            while page <= 40:
                response = requests.get(
                    '%s/api/v1/accounts/%s/conversations' % (base, account_id),
                    params={'status': 'open', 'inbox_id': inbox_id, 'page': page},
                    headers=headers, timeout=15)
                response.raise_for_status()
                payload = response.json() or {}
                data = payload.get('data') or {}
                rows = data.get('payload') or []
                if page == 1:
                    total_open = int((data.get('meta') or {}).get('all_count') or
                                     len(rows))
                for conv in rows:
                    last = conv.get('last_non_activity_message') or {}
                    if last.get('message_type') in (0, 'incoming'):
                        waiting += 1
                    if int(conv.get('unread_count') or 0) > 0:
                        unread += 1
                processed += len(rows)
                if not rows or len(rows) < 25 or processed >= total_open:
                    break
                page += 1

            result = {
                'available': True, 'source': 'Chatwoot / WhatsApp',
                'sent_today': report('outgoing_messages_count'),
                'received_today': report('incoming_messages_count'),
                'new_conversations_today': report('conversations_count'),
                'open_conversations': total_open,
                'waiting_reply': waiting,
                'unread_conversations': unread,
                'updated_at': now_local.strftime('%Y-%m-%d %H:%M'),
            }
        except Exception:
            result = empty
        _AI_CHATWOOT_CACHE.update({'at': datetime.utcnow(), 'data': result})
        return dict(result)

    def _ai_context_data(self):
        """لقطة أرقام محدودة يقرأها المساعد؛ لا تشمل هواتف أو بريد أولياء الأمور."""
        import pytz as _pytz

        env = request.env
        today = fields.Date.today()
        students = env['nursery.student'].sudo().search(
            self._visible_student_domain(), order='name')
        student_ids = students.ids

        overdue = students.filtered(lambda s: s.paid_until and s.paid_until < today)
        no_current_payment = students.filtered(
            lambda s: not s.paid_until and not s.paid)
        paid_current = students.filtered(lambda s: s.paid)
        needs_payment_ids = set(overdue.ids) | set(no_current_payment.ids)
        due_soon = students.filtered(
            lambda s: s.paid_until and 0 <= (s.paid_until - today).days <= 3)
        due_today = students.filtered(lambda s: s.paid_until == today)
        debtors = students.filtered(lambda s: (s.receivable or 0.0) > 0.01)
        overdue_rows = sorted(({
            'name': s.name,
            'days_late': (today - s.paid_until).days if s.paid_until else 0,
            'receivable': round(max(0.0, s.receivable or 0.0), 2),
        } for s in overdue), key=lambda row: row['days_late'], reverse=True)
        due_soon_rows = sorted(({
            'name': s.name,
            'days_left': (s.paid_until - today).days,
        } for s in due_soon), key=lambda row: row['days_left'])

        linked_ids = set(students.filtered(
            lambda s: s.parent_user_id or s.parent_user_ids).ids)
        if student_ids:
            linked_requests = env['nursery.link.request'].sudo().search([
                ('matched_student_id', 'in', student_ids), ('state', '=', 'linked')])
            linked_ids.update(linked_requests.mapped('matched_student_id').ids)

        Attendance = env['nursery.attendance'].sudo()
        attendance = Attendance.search([
            ('date', '=', today), ('student_id', 'in', student_ids)]) \
            if student_ids else Attendance.browse()
        attendance_counts = {
            key: len(attendance.filtered(lambda row, k=key: row.status == k))
            for key in ('present', 'absent', 'late', 'sick', 'leave')
        }
        absent_names = attendance.filtered(
            lambda row: row.status == 'absent').mapped('student_id.name')[:12]

        new_year = env['nursery.student'].sudo().search([
            ('active', '=', True), ('term', '=', 'term_2027')], order='name')
        new_linked_ids = set(new_year.filtered(
            lambda s: s.parent_user_id or s.parent_user_ids).ids)
        if new_year.ids:
            new_linked_requests = env['nursery.link.request'].sudo().search([
                ('matched_student_id', 'in', new_year.ids), ('state', '=', 'linked')])
            new_linked_ids.update(new_linked_requests.mapped('matched_student_id').ids)

        tz = _pytz.timezone('Asia/Riyadh')
        start_local = tz.localize(datetime.combine(today, dt_time.min))
        tomorrow_local = start_local + timedelta(days=1)
        soon_local = start_local + timedelta(days=4)
        start_utc = start_local.astimezone(_pytz.UTC).replace(tzinfo=None)
        tomorrow_utc = tomorrow_local.astimezone(_pytz.UTC).replace(tzinfo=None)
        soon_utc = soon_local.astimezone(_pytz.UTC).replace(tzinfo=None)
        Visit = env['nursery.visit'].sudo()
        visits_today = Visit.search_count([
            ('state', '=', 'scheduled'), ('when_dt', '>=', start_utc),
            ('when_dt', '<', tomorrow_utc)])
        visits_soon = Visit.search_count([
            ('state', '=', 'scheduled'), ('when_dt', '>=', tomorrow_utc),
            ('when_dt', '<', soon_utc)])

        ym = today.strftime('%Y-%m')
        month = env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)
        monthly = {
            'ym': ym, 'open': False, 'income_students': 0.0,
            'income_other': 0.0, 'expenses': 0.0, 'salaries': 0.0,
            'net': 0.0, 'unpaid_count': 0,
        }
        if month:
            monthly.update(self._month_totals(month))
            monthly['open'] = True

        whatsapp = self._ai_chatwoot_stats()
        priorities = []
        if whatsapp.get('waiting_reply'):
            priorities.append({'label': 'محادثات واتساب تنتظر الرد',
                               'count': whatsapp['waiting_reply'], 'url': '/funnel/'})
        if needs_payment_ids:
            priorities.append({'label': 'طلاب يحتاجون متابعة سداد',
                               'count': len(needs_payment_ids), 'url': '/receivables/'})
        if visits_today:
            priorities.append({'label': 'زيارات مجدولة اليوم',
                               'count': visits_today, 'url': '/visits/'})
        if attendance_counts['absent']:
            priorities.append({'label': 'طلاب غائبون اليوم',
                               'count': attendance_counts['absent'], 'url': '/classes/'})
        missing_grade = len(new_year.filtered(lambda s: not s.level))
        if missing_grade:
            priorities.append({'label': 'طلبات سنة جديدة بدون جريد',
                               'count': missing_grade, 'url': '/enrollments/'})

        ICP = env['ir.config_parameter'].sudo()
        return {
            'generated_at': datetime.utcnow().replace(
                tzinfo=_pytz.UTC).astimezone(tz).strftime('%Y-%m-%d %H:%M'),
            'assistant': {
                'provider': 'Msty Go',
                'configured': bool((ICP.get_param('nursery.msty_gateway_key') or '').strip()),
            },
            'whatsapp': whatsapp,
            'students': {
                'total': len(students), 'linked_parents': len(linked_ids),
                'unlinked_parents': len(students) - len(linked_ids),
                'paid_current': len(paid_current),
                'without_phone': len(students.filtered(lambda s: not s.guardian_phone)),
            },
            'payments': {
                'needs_payment': len(needs_payment_ids),
                'never_or_not_current': len(no_current_payment),
                'overdue': len(overdue), 'due_soon': len(due_soon),
                'due_today': len(due_today),
                'debtors': len(debtors),
                'receivable_total': round(sum(debtors.mapped('receivable')), 2),
                'overdue_students': overdue_rows[:15],
                'due_soon_students': due_soon_rows[:15],
            },
            'attendance_today': dict(attendance_counts, marked=len(attendance),
                                     absent_names=absent_names),
            'new_year': {
                'total': len(new_year),
                'ready': len(new_year.filtered(lambda s: s.joining_date and s.level)),
                'without_grade': missing_grade,
                'without_joining_date': len(new_year.filtered(lambda s: not s.joining_date)),
                'linked_parents': len(new_linked_ids),
                'unlinked_parents': len(new_year) - len(new_linked_ids),
            },
            'visits': {'today': visits_today, 'next_three_days': visits_soon},
            'monthly_finance': monthly,
            'internal_messages': {
                'pending_approval': env['nursery.message'].sudo().search_count([
                    ('state', '=', 'pending')]),
            },
            'priorities': priorities,
        }

    def _ai_gateway_context(self, data):
        """نسخة مختصرة للبوابة الخارجية بلا أسماء طلاب أو بيانات تعريفية."""
        context = dict(data)
        payments = dict(context.get('payments') or {})
        payments.pop('overdue_students', None)
        payments.pop('due_soon_students', None)
        context['payments'] = payments
        attendance = dict(context.get('attendance_today') or {})
        attendance.pop('absent_names', None)
        context['attendance_today'] = attendance
        return context

    def _ai_direct_answer(self, prompt, data):
        """الأسئلة الرقمية تُجاب من المصدر مباشرة؛ الصياغة والتحليل فقط لـMsty Go."""
        q = (prompt or '').strip().lower()
        q = q.translate(str.maketrans('أإآىة', 'ااايه'))

        def number(value):
            return '{:,}'.format(int(round(float(value or 0))))

        def money(value):
            return '%s ر.س' % number(value)

        if any(word in q for word in (
                'اكتب', 'صيغ', 'جهز رسال', 'اقترح رسال', 'حلل',
                'خطة', 'لخص', 'اقترح', 'رتب اولوي')):
            return None
        wa = data['whatsapp']
        pay = data['payments']
        st = data['students']
        ny = data['new_year']
        att = data['attendance_today']
        fin = data['monthly_finance']
        today_q = 'اليوم' in q or 'نهارده' in q

        if 'تقرير' in q and any(word in q for word in ('يومي', 'مختصر', 'ادار')):
            wa_line = ('واتساب: %s رسالة صادرة، %s رسالة واردة، و%s محادثة تنتظر الرد.' %
                       (number(wa['sent_today']), number(wa['received_today']),
                        number(wa['waiting_reply']))) if wa.get('available') else (
                            'واتساب: تعذّر تحديث أرقام Chatwoot حالياً.')
            return ('تقرير يومي مختصر للإدارة:\n'
                    '- %s\n'
                    '- السداد: %s طالباً يحتاج متابعة، و%s مستحق السداد اليوم.\n'
                    '- الحضور: تم تسجيل حضور %s طالباً، والغياب %s.\n'
                    '- طلبات السنة الجديدة: %s طلباً، منها %s بدون جريد.\n'
                    '- الزيارات المجدولة اليوم: %s.\n'
                    '- الرسائل الداخلية المعلقة للموافقة: %s.' %
                    (wa_line, number(pay['needs_payment']), number(pay['due_today']),
                     number(att['present']), number(att['absent']), number(ny['total']),
                     number(ny['without_grade']), number(data['visits']['today']),
                     number(data['internal_messages']['pending_approval'])))

        if ('مستني' in q or 'ينتظر' in q or 'بانتظار' in q) and 'رد' in q:
            if not wa.get('available'):
                return 'تعذّر قراءة Chatwoot الآن، لذلك لن أعرض رقماً غير مؤكّد.'
            return ('هناك %s محادثة واتساب آخر رسالة فيها من العميل وتنتظر رد الفريق، '
                    'من أصل %s محادثة مفتوحة.' %
                    (number(wa['waiting_reply']), number(wa['open_conversations'])))
        if 'غير مقرو' in q and ('محادث' in q or 'واتس' in q):
            if not wa.get('available'):
                return 'تعذّر قراءة Chatwoot الآن، لذلك لن أعرض رقماً غير مؤكّد.'
            return 'هناك %s محادثة عليها رسائل غير مقروءة.' % number(wa['unread_conversations'])
        if 'مفتوح' in q and ('محادث' in q or 'واتس' in q):
            if not wa.get('available'):
                return 'تعذّر قراءة Chatwoot الآن، لذلك لن أعرض رقماً غير مؤكّد.'
            return 'هناك %s محادثة واتساب مفتوحة حالياً.' % number(wa['open_conversations'])
        if 'محادث' in q and any(word in q for word in ('جديد', 'بدات', 'بدا')):
            if not wa.get('available'):
                return 'تعذّر قراءة تقرير واتساب من Chatwoot الآن. جرّبي التحديث بعد قليل.'
            return 'بدأت %s محادثة جديدة اليوم.' % number(wa['new_conversations_today'])
        if 'اخر تحديث' in q and ('بيانات' in q or 'واتس' in q or 'محادث' in q):
            if not wa.get('available'):
                return 'تعذّر قراءة وقت تحديث بيانات واتساب الآن.'
            return 'آخر تحديث لبيانات واتساب كان %s بتوقيت الرياض.' % (wa.get('updated_at') or 'غير معروف')
        if ('واتس' in q or 'رسال' in q) and any(
                word in q for word in ('اتبعت', 'اترسل', 'مرسل', 'ارسلنا', 'خرجت')):
            if not wa.get('available'):
                return 'تعذّر قراءة تقرير واتساب من Chatwoot الآن. جرّبي التحديث بعد قليل.'
            return ('تم إرسال %s رسالة واتساب اليوم، واستقبال %s رسالة، وبدأت %s محادثة جديدة.' %
                    (number(wa['sent_today']), number(wa['received_today']),
                     number(wa['new_conversations_today'])))
        if ('واتس' in q or 'رسال' in q) and any(
                word in q for word in ('استقبل', 'وصل', 'وارد')):
            if not wa.get('available'):
                return 'تعذّر قراءة تقرير واتساب من Chatwoot الآن. جرّبي التحديث بعد قليل.'
            return 'وصلت %s رسالة واتساب اليوم.' % number(wa['received_today'])
        if ('دفع' in q or 'سدد' in q or 'مدفوع' in q) and 'طالب' in q and not any(
                word in q for word in ('مدفعش', 'ما دفع', 'لم يدفع', 'مادفعش',
                                       'غير مدفوع', 'غير مسدد', 'لم يسدد')):
            return 'تم سداد الرسوم الحالية لـ%s طالباً.' % number(st['paid_current'])
        if any(word in q for word in (
                'مدفعش', 'ما دفع', 'لم يدفع', 'مادفعش', 'غير مدفوع',
                'غير مسدد', 'لم يسدد', 'ما سددش')):
            return ('هناك %s طالب يحتاج متابعة سداد الآن: %s متأخرون عن الموعد، '
                    'و%s بلا تغطية دفع حالية.' %
                    (number(pay['needs_payment']), number(pay['overdue']),
                     number(pay['never_or_not_current'])))
        if 'طالب' in q and today_q and any(
                word in q for word in ('مستحق', 'سداد', 'دفع')):
            return 'استحق السداد اليوم لـ%s طالباً.' % number(pay['due_today'])
        if any(word in q for word in ('اجمالي', 'مجموع')) and any(
                word in q for word in ('مستحق', 'مديون', 'متاخر', 'رصيد')):
            return 'إجمالي المبالغ المستحقة حالياً هو %s.' % money(pay['receivable_total'])
        if 'مديون' in q and not any(word in q for word in ('مين', 'اسم')):
            return 'عدد الطلاب الذين عليهم رصيد مستحق هو %s.' % number(pay['debtors'])
        if 'متاخر' in q and any(word in q for word in ('مين', 'اسم', 'طالب')):
            rows = pay['overdue_students']
            if not rows:
                return 'لا يوجد طلاب متأخرون عن موعد السداد الآن.'
            lines = ['%s: %s يوم' % (row['name'], number(row['days_late']))
                     for row in rows[:10]]
            return ('المتأخرون عن موعد السداد (%s):\n- %s' %
                    (number(pay['overdue']), '\n- '.join(lines)))
        if any(word in q for word in ('قرب موعد', 'خلال 3', 'خلال ٣', 'مستحق قريب')):
            rows = pay['due_soon_students']
            if not rows:
                return 'لا توجد مواعيد سداد خلال الأيام الثلاثة القادمة.'
            return 'مواعيد السداد القريبة:\n- ' + '\n- '.join(
                '%s: خلال %s يوم' % (row['name'], number(row['days_left']))
                for row in rows[:10])
        if ('بدون رقم' in q or 'من غير رقم' in q or 'بدون تليفون' in q or
                'من غير تليفون' in q) and 'طالب' in q:
            return 'هناك %s طالباً بدون رقم ولي أمر مسجل.' % number(st['without_phone'])
        is_new_year = ('طلب' in q or 'تسجيل' in q) and ('سنه' in q or 'جديد' in q)
        if is_new_year and ('غير مرتبط' in q or 'مش مرتبط' in q):
            return 'هناك %s طلب سنة جديدة غير مرتبط بولي الأمر.' % number(ny['unlinked_parents'])
        if is_new_year and 'مرتبط' in q:
            return 'هناك %s طلب سنة جديدة مرتبط بولي الأمر.' % number(ny['linked_parents'])
        if is_new_year and ('موعد' in q or 'التحاق' in q) and any(
                word in q for word in ('غير', 'بدون', 'من غير')):
            return 'هناك %s طلب سنة جديدة بدون موعد التحاق.' % number(ny['without_joining_date'])
        if is_new_year and 'جاهز' in q:
            return 'عدد طلبات السنة الجديدة الجاهزة هو %s.' % number(ny['ready'])
        if is_new_year:
            return ('طلبات السنة الجديدة: %s إجمالاً، %s مكتملة بموعد التحاق وجريد، '
                    'و%s بلا جريد، و%s غير مرتبطة بولي الأمر.' %
                    (number(ny['total']), number(ny['ready']),
                     number(ny['without_grade']), number(ny['unlinked_parents'])))
        if 'مرتبط' in q and ('ولي' in q or 'الامر' in q):
            if 'غير مرتبط' in q or 'مش مرتبط' in q:
                return 'هناك %s طالباً غير مرتبط بولي الأمر.' % number(st['unlinked_parents'])
            return ('%s طالباً مرتبطون بحساب ولي الأمر، و%s غير مرتبطين، من إجمالي %s.' %
                    (number(st['linked_parents']), number(st['unlinked_parents']),
                    number(st['total'])))
        if 'جريد' in q or 'مرحله' in q:
            return ('هناك %s طلب سنة جديدة بلا جريد، و%s طلباً مكتمل الجريد وموعد الالتحاق.' %
                    (number(ny['without_grade']), number(ny['ready'])))
        if 'زيار' in q:
            if any(word in q for word in ('ثلاث', '3', '٣', 'القادم', 'الجاي')):
                return 'هناك %s زيارة مجدولة خلال الأيام الثلاثة القادمة.' % number(data['visits']['next_three_days'])
            return 'هناك %s زيارة مجدولة اليوم.' % number(data['visits']['today'])
        if any(word in q for word in ('غايب', 'غياب')):
            names = (' الأسماء: %s.' % '، '.join(att['absent_names'])) \
                if att['absent_names'] and any(word in q for word in ('مين', 'اسم')) else ''
            return 'هناك %s طالباً غائباً اليوم.%s' % (number(att['absent']), names)
        if any(word in q for word in ('اتاخر', 'تاخير')) and (today_q or 'حضور' in q):
            return 'هناك %s طالباً متأخراً اليوم.' % number(att['late'])
        if 'مريض' in q and (today_q or 'حضور' in q):
            return 'هناك %s طالباً مسجلاً كمريض اليوم.' % number(att['sick'])
        if 'اجازه' in q and (today_q or 'حضور' in q):
            return 'هناك %s طالباً في إجازة اليوم.' % number(att['leave'])
        if ('اتسجل' in q or 'مسجل' in q) and 'حضور' in q:
            return 'تم تسجيل حضور %s طالباً اليوم.' % number(att['marked'])
        if ('حضر' in q or 'حاضر' in q) and today_q:
            return 'حضر اليوم %s طالباً.' % number(att['present'])
        if 'حضور' in q:
            names = (' الأسماء: %s.' % '، '.join(att['absent_names'])) \
                if att['absent_names'] and any(word in q for word in ('مين', 'اسم')) else ''
            return ('حضور اليوم: %s حاضر، %s غائب، %s متأخر، وتم تسجيل %s طالب.%s' %
                    (number(att['present']), number(att['absent']), number(att['late']),
                     number(att['marked']), names))
        if ('دخل الطلب' in q or 'دخل الطلاب' in q) and 'شهر' in q:
            if not fin['open']:
                return 'لم يُفتح كشف الشهر الحالي بعد، لذلك لا يوجد دخل مؤكّد.'
            return 'دخل الطلبة هذا الشهر هو %s.' % money(fin['income_students'])
        if ('دخل اخر' in q or 'دخل اضاف' in q) and 'شهر' in q:
            if not fin['open']:
                return 'لم يُفتح كشف الشهر الحالي بعد، لذلك لا يوجد دخل مؤكّد.'
            return 'الدخل الآخر هذا الشهر هو %s.' % money(fin['income_other'])
        if ('مرتبات' in q or 'رواتب' in q) and ('مصاريف' in q or 'مصروف' in q):
            if not fin['open']:
                return 'لم يُفتح كشف الشهر الحالي بعد، لذلك لا توجد أرقام مالية مؤكّدة.'
            return 'المرتبات %s، والمصاريف الأخرى %s هذا الشهر.' % (
                money(fin['salaries']), money(fin['expenses']))
        if ('مرتبات' in q or 'رواتب' in q) and ('مصاريف' not in q and 'مصروف' not in q):
            if not fin['open']:
                return 'لم يُفتح كشف الشهر الحالي بعد، لذلك لا توجد أرقام رواتب مؤكّدة.'
            return 'إجمالي المرتبات هذا الشهر هو %s.' % money(fin['salaries'])
        if 'صاف' in q:
            if not fin['open']:
                return 'لم يُفتح كشف الشهر الحالي بعد، لذلك لا يوجد صافي مالي مؤكّد.'
            return 'صافي الشهر الحالي هو %s.' % money(fin['net'])
        if any(word in q for word in ('دخل', 'مصاريف', 'مصروف', 'مالي')):
            if not fin['open']:
                return 'لم يُفتح كشف الشهر الحالي بعد، لذلك لا يوجد ملخص مالي مؤكّد.'
            income = fin['income_students'] + fin['income_other']
            costs = fin['expenses'] + fin['salaries']
            return ('ملخص الشهر: دخل %s، مصروفات ورواتب %s، والصافي %s.' %
                    (money(income), money(costs), money(fin['net'])))
        if any(word in q for word in ('اهم', 'اولوي', 'اتابع', 'اعمل ايه')):
            priorities = data['priorities']
            if not priorities:
                return 'لا توجد عناصر عاجلة ظاهرة في بيانات النظام الآن.'
            return 'أهم المتابعات الآن:\n- ' + '\n- '.join(
                '%s: %s' % (row['label'], number(row['count']))
                for row in priorities[:6])
        if ('موافق' in q or 'مستني' in q) and ('رسال' in q or 'معلم' in q or 'داخلي' in q):
            return ('هناك %s رسالة داخلية من المعلمات بانتظار الموافقة.' %
                    number(data['internal_messages']['pending_approval']))
        if 'كام طالب' in q or 'كم طالب' in q or 'عدد الطلاب' in q:
            return 'عدد الطلاب الحاليين في النظام هو %s.' % number(st['total'])
        return None

    @http.route('/api/manager/ai/context', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_ai_context(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'ai'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        return {'ok': True, 'context': self._ai_context_data(), 'suggestions': [
            'كام رسالة واتساب اتبعتت النهارده؟',
            'كام رسالة واتساب وصلتنا النهارده؟',
            'كام محادثة جديدة بدأت النهارده؟',
            'كام محادثة مستنية الرد؟',
            'كام محادثة واتساب مفتوحة؟',
            'كام محادثة عليها رسائل غير مقروءة؟',
            'إمتى آخر تحديث لبيانات واتساب؟',
            'كام طالب عندنا حالياً؟',
            'كام طالب دفع الرسوم الحالية؟',
            'كام طالب مرتبط بولي الأمر؟',
            'كام طالب غير مرتبط بولي الأمر؟',
            'كام طالب من غير رقم ولي الأمر؟',
            'كام طالب مدفعش؟',
            'كام طالب مستحق السداد النهارده؟',
            'كام طالب مديون؟',
            'إجمالي المبالغ المستحقة كام؟',
            'مين عليه متأخرات؟',
            'مين قرب موعد سداده؟',
            'كام طلب سنة جديدة؟',
            'كام طلب سنة جديدة جاهز؟',
            'كام طلب لسه من غير جريد؟',
            'كام طلب سنة جديدة من غير موعد التحاق؟',
            'كام طلب سنة جديدة مرتبط بولي الأمر؟',
            'كام طلب سنة جديدة غير مرتبط بولي الأمر؟',
            'كام طالب حضر النهارده؟',
            'كام زيارة عندنا النهارده؟',
            'كام طالب غايب النهارده؟',
            'كام طالب اتأخر النهارده؟',
            'كام طالب مريض النهارده؟',
            'كام طالب في إجازة النهارده؟',
            'كام طالب اتسجل حضوره النهارده؟',
            'كام زيارة خلال الثلاث أيام الجاية؟',
            'إيه ملخص دخل ومصاريف الشهر؟',
            'دخل الطلبة الشهر ده كام؟',
            'المرتبات والمصاريف الشهر ده كام؟',
            'الصافي المالي للشهر كام؟',
            'كام رسالة داخلية مستنية الموافقة؟',
            'إيه أهم حاجات أتابعها دلوقتي؟',
            'اعمل لي خطة متابعة لليوم من الأرقام الحالية.',
            'اكتب رسائل تذكير قصيرة للمتأخرين في السداد.',
            'اكتب رسالة متابعة لولي أمر لم يرد على واتساب.',
            'لخص حالة الروضة في نقاط قصيرة.',
            'اقترح ترتيب أولويات الفريق اليوم.',
            'جهز تقرير يومي مختصر للإدارة.',
        ]}

    @http.route('/api/manager/ai/ask', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_ai_ask(self, mt=None, prompt=None, history=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'ai'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        prompt = str(prompt or '').strip()
        if not prompt:
            return {'ok': False, 'error': 'اكتبي سؤالك أولاً'}
        if len(prompt) > 1200:
            return {'ok': False, 'error': 'السؤال طويل جداً؛ اختصريه قليلاً'}

        data = self._ai_context_data()
        direct = self._ai_direct_answer(prompt, data)
        if direct:
            return {'ok': True, 'answer': direct, 'source': 'live-data',
                    'provider': 'بيانات النظام'}

        ICP = request.env['ir.config_parameter'].sudo()
        gateway_key = (ICP.get_param('nursery.msty_gateway_key') or '').strip()
        if not gateway_key:
            return {'ok': False,
                    'error': 'Msty Go غير مربوط بالخادم بعد؛ الأسئلة الرقمية ما زالت تعمل.'}
        gateway_url = (ICP.get_param('nursery.msty_gateway_url') or
                       'https://ai.montessori-ksa.com/v1/chat/completions').strip()
        model = (ICP.get_param('nursery.msty_gateway_model') or 'auto').strip()
        safe_history = []
        for item in (history or [])[-8:]:
            if not isinstance(item, dict) or item.get('role') not in ('user', 'assistant'):
                continue
            content = str(item.get('content') or '').strip()[:1600]
            if content:
                safe_history.append({'role': item['role'], 'content': content})

        gateway_data = self._ai_gateway_context(data)
        system = (
            'أنت ذكاء إدارة روضة كوكب الطفل الحر. أجب بالعربية الواضحة وباختصار. '
            'اعتمد حصراً على لقطة البيانات المرفقة في أي أرقام، ولا تخمّن أو تخترع أسماء. '
            'ميّز بين واتساب الحي من Chatwoot ورسائل التطبيق الداخلية. '
            'لا تعرض هواتف أو بريد أو مفاتيح أو معلومات ليست موجودة في اللقطة. '
            'عند طلب صياغة رسالة قدّم نصاً عملياً جاهزاً، من دون ادعاء أنه أُرسل.\n'
            'لقطة البيانات الحالية:\n' + json.dumps(gateway_data, ensure_ascii=False))
        messages = [{'role': 'system', 'content': system}] + safe_history + [
            {'role': 'user', 'content': prompt}]
        try:
            import requests
            response = requests.post(
                gateway_url,
                headers={'Authorization': 'Bearer %s' % gateway_key,
                         'Content-Type': 'application/json'},
                json={'model': model, 'messages': messages, 'temperature': 0.2,
                      # Reasoning models can spend a small token budget before
                      # producing message.content, which otherwise arrives null.
                      'max_tokens': 1600,
                      'reasoning': {'effort': 'low'},
                      'stream': False},
                timeout=60)
            response.raise_for_status()
            payload = response.json() or {}
            message = ((payload.get('choices') or [{}])[0].get('message') or {})
            answer = message.get('content') or ''
            if isinstance(answer, list):
                answer = ''.join(
                    str(part.get('text') or part.get('content') or '')
                    if isinstance(part, dict) else str(part)
                    for part in answer)
            answer = str(answer).strip()
            if not answer:
                raise ValueError('empty answer')
            return {'ok': True, 'answer': answer, 'source': 'msty-go',
                    'provider': 'Msty Go', 'model': payload.get('model') or model}
        except Exception:
            return {'ok': False,
                    'error': 'تعذّر الوصول إلى Msty Go الآن. جرّبي السؤال مرة أخرى بعد قليل.'}

    @http.route('/api/manager/alert_staff/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_alert_staff_save(self, mt=None, staff=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        clean = []
        for x in (staff or [])[:4]:
            if not isinstance(x, dict):
                continue
            name = str(x.get('name') or '').strip().replace('<', '').replace('>', '')[:40]
            phone = re.sub(r'\D', '', str(x.get('phone') or ''))[:15]
            if name:
                clean.append({'name': name, 'phone': phone})
        request.env['ir.config_parameter'].sudo().set_param(
            'nursery.alert_staff', json.dumps(clean, ensure_ascii=False))
        return {'ok': True, 'alert_staff': self._alert_staff()}


    @http.route('/api/manager/enrollments', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_enrollments(self, mt=None, **kw):
        """طلبات السنة الجديدة من نفس سجل الطلاب، بدون إنشاء سجل مكرر."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        self._cleanup_future_month_fees()
        students = request.env['nursery.student'].sudo().search(
            [('active', '=', True), ('term', '=', 'term_2027')], order='joining_date, name')
        rows = [self._student_row(s) for s in students]
        requests = request.env['nursery.link.request'].sudo().search(
            [('matched_student_id', 'in', students.ids)], order='create_date desc')
        latest = {}
        for req in requests:
            latest.setdefault(req.matched_student_id.id, req)
        for row in rows:
            req = latest.get(row['id'])
            if req:
                row['parent_email'] = req.parent_email or row.get('parent_email', '')
                row['parent_name'] = req.parent_name or row['guardian_name']
                row['link_state'] = 'linked' if row.get('linked') else (req.state or 'none')
                row['link_request_id'] = req.id
            row['reservation_status'] = 'ready' if row['joining_date'] else 'needs_date'
            row['reservation_label'] = (
                'جاهز للترحيل التلقائي' if row['joining_date']
                else 'يحتاج تحديد تاريخ البداية')
        return {'ok': True, 'manager': mgr.name, 'students': rows,
                'target_term': 'term_2027', 'target_start': '2026-09-01'}

    @http.route('/api/manager/enrollment/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_enrollment_save(self, mt=None, id=None, name=None,
                                    parent_name=None, parent_email=None,
                                    parent_phone=None, fees=None,
                                    joining_date=None, remark=None, level=None,
                                    father_name=None, mother_name=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        name = (name or '').strip().replace('<', '').replace('>', '')
        email = (parent_email or '').strip().lower()
        if not name:
            return {'ok': False, 'error': 'اكتبي اسم الطالب'}
        if email and '@' not in email:
            return {'ok': False, 'error': 'إيميل ولي الأمر غير صالح'}
        start = (joining_date or '').strip() or '2026-09-01'
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', start):
            return {'ok': False, 'error': 'تاريخ بداية غير صالح'}
        if level and level not in STUDENT_LEVEL_KEYS:
            return {'ok': False, 'error': 'مرحلة غير صحيحة'}
        vals = {
            'name': name[:120], 'term': 'term_2027', 'joining_date': start,
            'level': level or False,
            'guardian_name': (parent_name or '').strip().replace('<', '').replace('>', '')[:120],
            'father_name': (father_name or '').strip().replace('<', '').replace('>', '')[:120],
            'mother_name': (mother_name or '').strip().replace('<', '').replace('>', '')[:120],
            'guardian_phone': (parent_phone or '').strip()[:40],
            'fees': self._num(fees),
            'remark': (remark or '').strip().replace('<', '').replace('>', ''),
        }
        Stu = request.env['nursery.student'].sudo()
        if id:
            s = Stu.browse(int(id))
            if not s.exists():
                return {'ok': False, 'error': 'طلب غير موجود'}
            s.write(vals)
        else:
            s = Stu.create(vals)
        link = self._sync_parent_link(s, vals['guardian_name'], email,
                                      vals['guardian_phone']) if email else self._student_link_meta(s)
        return {'ok': True, 'id': s.id, 'link_state': link['link_state'],
                'request_id': link['link_request_id']}

    @http.route('/api/manager/student/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_save(self, mt=None, id=None, name=None, class_id=None,
                                 guardian_name=None, guardian_phone=None,
                                 fees=None, joining_date=None, paid_until=None,
                                 term=None, remark=None, level=None,
                                 parent_email=None, father_name=None,
                                 mother_name=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        name = (name or '').strip().replace('<', '').replace('>', '')
        email = (parent_email or '').strip().lower()
        if not name:
            return {'ok': False, 'error': 'اكتب اسم الطالب'}
        if email and '@' not in email:
            return {'ok': False, 'error': 'إيميل ولي الأمر غير صالح'}
        vals = {
            'name': name,
            'guardian_name': (guardian_name or '').strip().replace('<', '').replace('>', ''),
            'father_name': (father_name or '').strip().replace('<', '').replace('>', '')[:120],
            'mother_name': (mother_name or '').strip().replace('<', '').replace('>', '')[:120],
            'guardian_phone': (guardian_phone or '').strip(),
            'fees': self._num(fees),
        }
        if level not in (None, '') and level not in STUDENT_LEVEL_KEYS:
            return {'ok': False, 'error': 'مرحلة غير صحيحة'}
        if level is not None:
            vals['level'] = level or False
        try:
            vals['class_id'] = int(class_id) if class_id else False
        except (TypeError, ValueError):
            vals['class_id'] = False
        vals['joining_date'] = (joining_date or '').strip() or False
        if term in ('term_2026', 'summer_2026', 'term_2027'):
            vals['term'] = term
            if term == 'term_2027' and not vals['joining_date']:
                vals['joining_date'] = '2026-09-01'
        if remark is not None:
            vals['remark'] = (remark or '').strip().replace('<', '').replace('>', '')
        Stu = request.env['nursery.student'].sudo()
        if id:
            s = Stu.browse(int(id))
            if not s.exists():
                return {'ok': False, 'error': 'طالب غير موجود'}
            old_joining = s.joining_date
            s.write(vals)
            pu = (paid_until or '').strip()
            if pu:
                # تصحيح يدوي صريح للاستحقاق من نافذة التعديل — له الأولوية على أي حساب تلقائي
                try:
                    s.paid_until = fields.Date.from_string(pu)
                except Exception:
                    pass
            elif s.joining_date and s.paid_until and s.joining_date != old_joining:
                # لو اتغيّر تاريخ الالتحاق والطالب له استحقاق قائم: أعد محاذاة الاستحقاق
                # على «نفس يوم الالتحاق شهرياً» بنفس عدد الدورات المدفوعة تقريباً —
                # حتى لا يبقى استحقاق قديم محسوب من يوم الدفع (حالة حمزة 14/8 بدل 7/8).
                k = int(round((s.paid_until - s.joining_date).days / 30.0))
                if k < 1:
                    k = 1
                s.paid_until = s.joining_date + relativedelta(months=k)
        else:
            s = Stu.create(vals)
        link = self._sync_parent_link(s, vals['guardian_name'], email,
                                      vals['guardian_phone']) if email else self._student_link_meta(s)
        return {'ok': True, 'id': s.id, 'link_state': link['link_state'],
                'request_id': link['link_request_id']}

    @http.route('/api/manager/student/delete', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_delete(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            s = request.env['nursery.student'].sudo().browse(int(id))
            if s.exists():
                s.active = False
                # حذف حقيقي: شيل الطالب من الشهور المحاسبية المفتوحة أيضاً
                # (الشهور المُقفَلة تحتفظ به كسِجلّ تاريخي؛ والأسطر المدفوعة
                #  تبقى لأنها إيراد فعلي حصل في ذلك الشهر).
                request.env['nursery.month.fee'].sudo().search([
                    ('student_id', '=', s.id),
                    ('month_id.state', '!=', 'closed'),
                    ('paid', '=', 0.0),
                ]).unlink()
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'طالب غير موجود'}
        return {'ok': True}

    def _ensure_month_fee_row(self, month, student):
        """سطر الطالب في كشف الشهر — يرجّعه أو ينشئه. مصدر واحد لإنشاء السطر
        يستخدمه «إضافة طالب للشهر» ومسار الدفع، فالرسوم المتناسبة والرصيد
        المُرحّل يُحسبان بنفس الطريقة في الحالتين."""
        Fee = request.env['nursery.month.fee'].sudo()
        f = Fee.search([('month_id', '=', month.id),
                        ('student_id', '=', student.id)], limit=1)
        if f:
            return f
        full = student.fees or 0.0
        # _coverage_due (نفس دالة محرك فتح الشهر) مش _prorated_fee: الأخيرة
        # بترجع الرسوم كاملة لأي شهر ≠ شهر الالتحاق حتى لو أسبق منه — فطالب
        # التحاقه 1/9 كان بياخد سطر أغسطس بمستحق كامل (اتصلحت 2026-08-11).
        due = request.env['nursery.month'].sudo()._coverage_due(
            student, full, month.ym)
        priors = Fee.search([('student_id', '=', student.id)]).filtered(
            lambda r: r.month_id.ym < month.ym)
        carry = 0.0
        if priors:
            pf = max(priors, key=lambda r: r.month_id.ym)
            carry = (pf.carry_in or 0.0) + (pf.paid or 0.0) - (pf.fees or 0.0)
        return Fee.create({
            'month_id': month.id, 'student_id': student.id, 'name': student.name,
            'full_fee': full, 'fees': due, 'carry_in': carry})

    def _post_payment_to_month(self, student, payment, pay_date, amount, method, anchor):
        """تسجيل الدفعة في كشف الشهر المفتوح كمان — عشان «الحسابات» و«الطلاب»
        يتطابقوا. من غيرها الدفعة المسجّلة من صفحة الطلاب تفضل ظاهرة «لم يدفع»
        في الحسابات. يرجّع اسم الشهر لو اتسجّلت، وإلا None.

        لو الطالب مش مضاف للشهر، بننشئ له السطر بدل ما نسيب الدفعة «عائمة»
        بلا سطر — الدفعة العائمة كانت بتختفي من إيراد الرئيسية لأن كشف الشهر
        بيحجب حساب الدفعات بالكامل."""
        Month = request.env['nursery.month'].sudo()
        m = Month.search([('ym', '=', (pay_date or '')[:7])], limit=1)
        if not m or m.state != 'open':
            return None
        f = self._ensure_month_fee_row(m, student)
        vals = {'paid': (f.paid or 0.0) + amount,
                'paid_date': pay_date,
                'method': method}
        if not f.until_before:
            vals['until_before'] = anchor
        if not f.payment_id:
            vals['payment_id'] = payment.id
        f.write(vals)
        return m.ym

    @http.route('/api/manager/student/pay', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_pay(self, mt=None, student_id=None, amount=None,
                                date=None, paid_until=None, method=None,
                                period=None, note=None, payment_type='tuition',
                                **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            s = request.env['nursery.student'].sudo().browse(int(student_id))
            assert s.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        amt = self._num(amount)
        if amt <= 0:
            return {'ok': False, 'error': 'اكتب مبلغاً صحيحاً'}
        if payment_type == 'books':
            books_due = BOOKS_FEE_DEFAULT
            books_paid = s.books_paid or 0.0
            books_remaining = max(0.0, books_due - books_paid)
            if books_remaining <= 0.01:
                return {'ok': False, 'error': 'رسوم الكتب مدفوعة بالكامل'}
            if amt > books_remaining + 0.01:
                return {'ok': False,
                        'error': 'المتبقي من رسوم الكتب: %.2f ريال' % books_remaining}
            pay_date = (date or '').strip() or fields.Date.today().strftime('%Y-%m-%d')
            if self._closed_month_of(pay_date):
                return {'ok': False, 'error': 'هذا التاريخ داخل شهر محاسبي مقفول — لا يمكن التسجيل فيه'}
            meth = method if method in ('cash', 'transfer', 'card', 'other') else 'cash'
            request.env['nursery.fee.payment'].sudo().create({
                'student_id': s.id, 'date': pay_date, 'amount': amt,
                'method': meth, 'payment_type': 'books',
                'period': 'رسوم الكتب',
                'note': (note or '').strip().replace('<', '').replace('>', ''),
            })
            return {'ok': True, 'row': self._student_row(s)}
        pay_date = (date or '').strip() or fields.Date.today().strftime('%Y-%m-%d')
        if self._closed_month_of(pay_date):
            return {'ok': False, 'error': 'هذا التاريخ داخل شهر محاسبي مقفول — لا يمكن التسجيل فيه'}
        meth = method if method in ('cash', 'transfer', 'card', 'other') else 'cash'
        # تغطية الدفعة = شهور كاملة تقويمية + أيام الباقي بقاسم 30.
        # (٤ سبتمبر + ٣ شهور = ٤ ديسمبر؛ وشهر + ١٠٠ ر.س من ألف = شهر و٣ أيام.)
        # محسوبة من الاستحقاق السابق وليس من يوم الدفع — فالجدول لا ينزاح
        # بالتأخير، لكنه يمتدّ لو دُفع أكثر من شهر، ويتقدّم جزئياً لو دُفع أقل.
        anchor = s.paid_until or s.joining_date or fields.Date.from_string(pay_date)
        months, extra = coverage_for(amt, s.fees)
        new_until = advance_due(anchor, amt, s.fees)
        days = (new_until - anchor).days
        per = (period or '').strip()
        if not per:
            try:
                per = '%s %s' % (self._AR_MONTHS[new_until.month - 1], new_until.year)
            except Exception:
                per = ''
        pay_rec = request.env['nursery.fee.payment'].sudo().create({
            'student_id': s.id, 'date': pay_date, 'amount': amt,
            'method': meth, 'payment_type': 'tuition', 'period': per,
            'note': (note or '').strip().replace('<', '').replace('>', ''),
            'days': days, 'until_before': anchor, 'until_after': new_until,
        })
        s.write({'paid': True, 'paid_at': pay_date, 'payment_method': meth,
                 'paid_until': new_until})
        # نفس الدفعة تُسجَّل في كشف الشهر — وإلا ظهرت «لم يدفع» في الحسابات
        posted = self._post_payment_to_month(s, pay_rec, pay_date, amt, meth, anchor)
        return {'ok': True, 'days': days, 'months': months, 'extra_days': extra,
                'paid_until': new_until.strftime('%Y-%m-%d'),
                'posted_month': posted,
                'row': self._student_row(s)}

    @http.route('/api/manager/student/payments', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_payments(self, mt=None, student_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            s = request.env['nursery.student'].sudo().browse(int(student_id))
            assert s.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        MLBL = {'cash': 'نقداً', 'transfer': 'تحويل', 'card': 'شبكة', 'other': 'أخرى'}
        payment_type = (kw.get('payment_type') or 'tuition').strip()
        pays = s.payment_ids.filtered(
            lambda p: not payment_type or p.payment_type == payment_type
        ).sorted(lambda p: (p.date or fields.Date.today()), reverse=True)
        total = sum(p.amount for p in pays)
        return {'ok': True, 'name': s.name, 'total_paid': total,
                'payments': [{
                    'id': p.id,
                    'date': p.date.strftime('%Y-%m-%d') if p.date else '',
                    'amount': p.amount or 0.0,
                    'payment_type': p.payment_type or 'tuition',
                    'method': MLBL.get(p.method, p.method or ''),
                    'period': p.period or '', 'note': p.note or '',
                    'days': p.days or 0,
                    'until_after': (p.until_after.strftime('%Y-%m-%d')
                                    if p.until_after else ''),
                } for p in pays]}

    @http.route('/api/manager/payment/delete', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_payment_delete(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            p = request.env['nursery.fee.payment'].sudo().browse(int(id))
            if not p.exists():
                return {'ok': False, 'error': 'دفعة غير موجودة'}
            sid = p.student_id.id
            month = request.env['nursery.month'].sudo().search([
                ('ym', '=', p.date.strftime('%Y-%m') if p.date else ''),
            ], limit=1)
            if month and month.state == 'closed':
                closed_by = month.closed_by.name if month.closed_by else 'غير محدد'
                return {'ok': False,
                        'error': 'هذه الدفعة داخل شهر محاسبي مقفول — أغلقه %s' % closed_by,
                        'month_state': 'closed', 'closed_at': (
                            month.closed_at.strftime('%Y-%m-%d %H:%M:%S')
                            if month.closed_at else ''),
                        'closed_by': closed_by}
            p.unlink()
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'دفعة غير موجودة'}
        s = request.env['nursery.student'].sudo().browse(sid)
        return {'ok': True, 'row': self._student_row(s) if s.exists() else None}

    # ==================== النظام المحاسبي الشهري ====================
    _YM_RE = None  # يُبنى عند أول استخدام

    def _ym_ok(self, ym):
        import re as _re
        return bool(ym and _re.match(r'^\d{4}-(0[1-9]|1[0-2])$', ym))

    def _month_label(self, ym):
        try:
            y, m = ym.split('-')
            return '%s %s' % (self._AR_MONTHS[int(m) - 1], y)
        except Exception:
            return ym

    def _month_last_day(self, ym):
        from calendar import monthrange
        y, m = int(ym[:4]), int(ym[5:7])
        return '%s-%02d' % (ym, monthrange(y, m)[1])

    def _prorated_fee(self, full_fee, joining_date, ym):
        """يفوّض لمنطق الفوترة الموحّد في النموذج (مصدر واحد للحقيقة)."""
        return request.env['nursery.month'].sudo()._prorated_fee(full_fee, joining_date, ym)

    def _expense_cash_movement(self, month):
        """Return the signed cash movement for expense entries.

        The positive Nesrin line is the opening-balance source and is kept in
        the ledger for audit, but it must not be counted again in closing cash.
        Negative workbook rows are outflows. Older manually-entered positive
        expense rows are treated as outflows for compatibility.
        """
        opening = 0.0
        movement = 0.0
        for entry in month.entry_ids:
            if entry.etype != 'expense':
                continue
            amount = float(entry.amount or 0.0)
            if amount > 0 and 'نسرين' in (entry.name or ''):
                opening += amount
                continue
            movement += amount if amount < 0 else -amount
        return opening, movement

    def _month_totals(self, month):
        inc_students = sum(month.fee_ids.mapped('paid'))          # المُحصَّل نقداً
        cash_collected = sum((f.paid or 0.0) for f in month.fee_ids if f.method == 'cash')
        bank_transfer = sum((f.paid or 0.0) for f in month.fee_ids if f.method == 'transfer')
        students = request.env['nursery.student'].sudo().search(
            self._visible_student_domain(), order='name')
        Payment = request.env['nursery.fee.payment'].sudo()
        month_books = Payment.search([
            ('payment_type', '=', 'books'),
            ('date', '>=', '%s-01' % month.ym),
            ('date', '<=', self._month_last_day(month.ym)),
        ])
        books_collected = sum(month_books.mapped('amount'))
        books_paid_total = sum(students.mapped('books_paid'))
        books_due_total = BOOKS_FEE_DEFAULT * len(students)
        books_remaining_total = sum(
            max(0.0, BOOKS_FEE_DEFAULT - (s.books_paid or 0.0))
            for s in students)
        inc_other = sum(e.amount for e in month.entry_ids if e.etype == 'income')
        reservations = sum(e.amount for e in month.entry_ids if e.etype == 'reservation')
        expenses = sum(e.amount for e in month.entry_ids if e.etype == 'expense')
        salaries = sum(e.amount for e in month.entry_ids if e.etype == 'salary')
        opening_from_entries, expenses_paid_out = self._expense_cash_movement(month)
        opening_balance = float(month.opening_balance or 0.0)
        # صافي التشغيل: بلا الحجوزات المقدّمة (لأنها عربون خدمة لاحقة، ليست دخل الشهر)
        net = inc_students + books_collected + inc_other - expenses - salaries
        cash_closing = opening_balance + cash_collected + inc_other + reservations + expenses_paid_out
        accrued = sum(month.fee_ids.mapped('fees'))              # المستحق المُكتسَب
        carry_fwd = sum((f.carry_in or 0.0) + (f.paid or 0.0) - (f.fees or 0.0)
                        for f in month.fee_ids)                   # يُرحّل للشهر التالي
        excel = {}
        try:
            raw_excel = request.env['ir.config_parameter'].sudo().get_param(
                'nursery.excel_month_%s' % month.ym, '')
            excel = json.loads(raw_excel) if raw_excel else {}
        except Exception:
            excel = {}
        excel_active = isinstance(excel, dict) and excel.get('ym') == month.ym
        if excel_active:
            # Excel is authoritative for the imported month. Its Net cell is
            # a reporting figure; cash_closing is the amount that rolls forward.
            inc_students = float(excel.get('collected', inc_students) or 0.0)
            books_due_total = float(excel.get('books', books_due_total) or 0.0)
            # The workbook supplies the books billed total, while the actual
            # book receipts remain the payment records on each student.
            books_paid_total = float(excel.get('books_paid_total', 0.0) or 0.0)
            books_remaining_total = float(excel.get('books_remaining_total', 0.0) or 0.0)
            books_unpaid_count = int(excel.get('books_unpaid_count', 0) or 0)
            cash_collected = float(excel.get('randa_cash', cash_collected) or 0.0)
            bank_transfer = float(excel.get('bank_transfer', bank_transfer) or 0.0)
            expenses = float(excel.get('expenses', expenses) or 0.0)
            salaries = float(excel.get('salaries', salaries) or 0.0)
            opening_balance = float(excel.get('opening_balance', opening_balance) or 0.0)
            opening_from_entries = float(excel.get('opening_balance', opening_from_entries) or 0.0)
            expenses_paid_out = float(excel.get('expenses_paid_out', expenses_paid_out) or 0.0)
            cash_closing = float(
                excel.get('cash_closing', opening_balance + cash_collected
                          + expenses_paid_out) or 0.0)
            net = float(excel.get('net', net) or 0.0)
            accrued = 0.0
            carry_fwd = 0.0
            due_minus_collected = float(excel.get('remaining_total', 0.0) or 0.0)
        else:
            due_minus_collected = accrued - inc_students
        cash_after_salaries = cash_closing - salaries
        return {
            'income_students': inc_students, 'income_other': inc_other,
            'income_books': books_collected,
            'books_due_total': books_due_total,
            'books_paid_total': books_paid_total,
            'books_remaining_total': books_remaining_total,
            'books_unpaid_count': (books_unpaid_count if excel_active else len(students.filtered(
                lambda s: (s.books_remaining or 0.0) > 0.01))),
            'reservations': reservations,
            'expenses': expenses, 'expenses_paid_out': expenses_paid_out,
            'opening_from_entries': opening_from_entries,
            'salaries': salaries, 'net': net,
            'cash_closing': cash_closing,
            'cash_after_salaries': cash_after_salaries,
            'closing': cash_closing,
            'due_total': accrued, 'accrued': accrued, 'collected': inc_students,
            'cash_collected': cash_collected,
            'bank_transfer': bank_transfer,
            'due_minus_collected': due_minus_collected,
            'carry_forward': carry_fwd,
            'unpaid_count': len(month.fee_ids.filtered(
                lambda f: ((f.carry_in or 0) + (f.paid or 0) - (f.fees or 0)) < -0.01)),
            # نفس قاعدة «متأخرو السداد» في الرئيسية بالحرف: التغطية انتهت قبل
            # اليوم. رقمان مختلفان بقصد — «عليه رصيد» محاسبي، و«متأخر» تغطية —
            # ومكتوبان بنفس التعريف في الصفحتين عشان ميبانوش تضارب.
            'overdue_count': len(month.fee_ids.filtered(
                lambda f: f.student_id.paid_until
                and f.student_id.paid_until < fields.Date.today())),
        }

    def _closed_month_of(self, date_str):
        """True لو التاريخ يقع داخل شهر محاسبي مقفول."""
        if not date_str:
            return False
        ym = str(date_str)[:7]
        m = request.env['nursery.month'].sudo().search(
            [('ym', '=', ym), ('state', '=', 'closed')], limit=1)
        return bool(m)

    @http.route('/api/manager/months', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_months(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'accounts'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        Months = request.env['nursery.month'].sudo()
        months = Months.search([], order='ym desc')
        out = []
        for m in months:
            t = self._month_totals(m)
            out.append({'ym': m.ym, 'label': self._month_label(m.ym),
                        'state': m.state, 'opening': m.opening_balance or 0.0,
                        'net': t['net'], 'closing': t['closing'],
                        'closed_at': (m.closed_at.strftime('%Y-%m-%d %H:%M:%S')
                                      if m.closed_at else ''),
                        'closed_by': m.closed_by.name if m.closed_by else ''})
        # اقتراح الشهر التالي للفتح
        today = fields.Date.today()
        cur = today.strftime('%Y-%m')
        suggest = cur
        if months and months[0].ym >= cur:
            y, mm = int(months[0].ym[:4]), int(months[0].ym[5:7])
            mm += 1
            if mm > 12:
                y, mm = y + 1, 1
            suggest = '%d-%02d' % (y, mm)
        return {'ok': True, 'months': out, 'suggest': suggest,
                'suggest_label': self._month_label(suggest)}

    @http.route('/api/manager/month/get', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_get(self, mt=None, ym=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not self._ym_ok(ym):
            return {'ok': False, 'error': 'شهر غير صالح'}
        m = request.env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)
        if not m:
            return {'ok': False, 'error': 'الشهر غير مفتوح'}
        excel_summary = {}
        try:
            raw_excel = request.env['ir.config_parameter'].sudo().get_param(
                'nursery.excel_month_%s' % ym, '')
            excel_summary = json.loads(raw_excel) if raw_excel else {}
        except Exception:
            excel_summary = {}
        if not isinstance(excel_summary, dict) or excel_summary.get('ym') != ym:
            excel_summary = {}
        in_month = set(m.fee_ids.mapped('student_id').ids)
        avail = request.env['nursery.student'].sudo().search(
            self._month_student_domain(ym, in_month), order='name')
        # إصلاح دائم: أي طالب نشط غير موجود في الشهر المفتوح يُضاف تلقائياً برسوم متناسبة
        # ورصيد مُرحّل من آخر شهر سابق — فلا يضيع دخل طالب التحق بعد فتح الكشف.
        if m.state == 'open' and avail:
            Fee = request.env['nursery.month.fee'].sudo()
            for s in avail:
                full = s.fees or 0.0
                # نفس تصحيح _ensure_month_fee_row: بالأيام غير المغطاة،
                # وصفر لشهر أسبق من الالتحاق (اتصلحت 2026-08-11)
                due = request.env['nursery.month'].sudo()._coverage_due(
                    s, full, ym)
                priors = Fee.search([('student_id', '=', s.id)]).filtered(
                    lambda r: r.month_id.ym < ym)
                carry = 0.0
                if priors:
                    pf = max(priors, key=lambda r: r.month_id.ym)
                    carry = (pf.carry_in or 0.0) + (pf.paid or 0.0) - (pf.fees or 0.0)
                Fee.create({'month_id': m.id, 'student_id': s.id, 'name': s.name,
                            'full_fee': full, 'fees': due, 'carry_in': carry})
            in_month = set(m.fee_ids.mapped('student_id').ids)
            avail = request.env['nursery.student'].sudo().search(
                self._month_student_domain(ym, in_month), order='name')
        MLBL = dict(request.env['nursery.month.fee']._fields['method'].selection or [])
        return {
            'ok': True, 'ym': m.ym, 'label': self._month_label(m.ym),
            'state': m.state, 'opening': m.opening_balance or 0.0,
            'closed_at': (m.closed_at.strftime('%Y-%m-%d %H:%M:%S')
                          if m.closed_at else ''),
            'closed_by': m.closed_by.name if m.closed_by else '',
            'totals': self._month_totals(m),
            'excel_summary': excel_summary,
            'books': [{
                'student_id': s.id,
                'name': s.name,
                'due': round((s.books_fees if excel_summary else BOOKS_FEE_DEFAULT) or 0.0, 2),
                'paid': round(s.books_paid or 0.0, 2),
                'remaining': round(
                    max(0.0, ((s.books_fees if excel_summary else BOOKS_FEE_DEFAULT) or 0.0)
                        - (s.books_paid or 0.0)), 2),
                'status': ('paid' if (((s.books_fees if excel_summary else BOOKS_FEE_DEFAULT) or 0.0)
                                      - (s.books_paid or 0.0)) <= 0.01 else
                           ('partial' if (s.books_paid or 0.0) > 0.01 else 'unpaid')),
            } for s in request.env['nursery.student'].sudo().search(
                self._visible_student_domain(), order='name')],
            'fees': [{
                'id': f.id, 'student_id': f.student_id.id or False,
                'name': f.name, 'fees': f.fees or 0.0, 'paid': f.paid or 0.0,
                'student_serial': (f.student_id.serial
                                   if f.student_id and f.student_id.serial not in (False, None, 0)
                                   else None),
                'full_fee': f.full_fee or 0.0, 'carry_in': f.carry_in or 0.0,
                'carry_out': (f.carry_in or 0.0) + (f.paid or 0.0) - (f.fees or 0.0),
                'remaining': round((f.excel_remaining or 0.0)
                                   if excel_summary else max(
                                       0.0, (f.fees or 0.0) +
                                       (f.carry_in or 0.0) - (f.paid or 0.0)), 2),
                'prorated': bool(f.full_fee and abs((f.fees or 0.0) - (f.full_fee or 0.0)) > 0.01),
                'paid_date': f.paid_date.strftime('%Y-%m-%d') if f.paid_date else '',
                'method': f.method or 'cash', 'note': f.note or '',
                'days_paid': f.days_paid or 0,
                'monthly': ((f.student_id.fees if f.student_id else 0.0)
                            or f.full_fee or f.fees or 0.0),
                'joining_date': (f.student_id.joining_date.strftime('%Y-%m-%d')
                                 if (f.student_id and f.student_id.joining_date) else ''),
                'paid_until': (f.student_id.paid_until.strftime('%Y-%m-%d')
                               if (f.student_id and f.student_id.paid_until) else ''),
                'until_before': (f.until_before.strftime('%Y-%m-%d')
                                 if f.until_before else ''),
                'guardian_name': (f.student_id.guardian_name if f.student_id else '') or '',
                'guardian_phone': (f.student_id.guardian_phone if f.student_id else '') or '',
                'parent_email': (self._student_link_meta(f.student_id)['parent_email']
                                 if f.student_id else ''),
                'linked': (self._student_link_meta(f.student_id)['linked']
                           if f.student_id else False),
                'link_state': (self._student_link_meta(f.student_id)['link_state']
                               if f.student_id else 'none'),
            } for f in m.fee_ids.sorted('name')],
            'day_basis': DAY_BASIS,
            'entries': [{
                'id': e.id, 'etype': e.etype, 'name': e.name,
                'amount': e.amount or 0.0,
                'date': e.date.strftime('%Y-%m-%d') if e.date else '',
                'note': e.note or '',
            } for e in m.entry_ids],
            'available_students': [{'id': s.id, 'name': s.name,
                                    'fees': s.fees or 0.0,
                                    'linked': self._student_link_meta(s)['linked'],
                                    'parent_email': self._student_link_meta(s)['parent_email']}
                                   for s in avail],
        }

    @http.route('/api/manager/month/open', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_open(self, mt=None, ym=None, opening=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not self._ym_ok(ym):
            return {'ok': False, 'error': 'اكتبي شهراً صحيحاً (مثال 2026-08)'}
        Months = request.env['nursery.month'].sudo()
        if Months.search([('ym', '=', ym)], limit=1):
            return {'ok': False, 'error': 'هذا الشهر مفتوح بالفعل'}
        # محرّك الفوترة الموحّد (نفس اللي يستخدمه الكرون التلقائي)
        month = Months._open_month(ym)
        # لأول شهر بلا سابق: يسمح بتحديد رصيد افتتاحي يدوي
        if opening not in (None, '') and not Months.search(
                [('ym', '<', ym)], order='ym desc', limit=1):
            try:
                month.opening_balance = self._num(opening)
            except Exception:
                pass
        return {'ok': True, 'ym': ym, 'carried': len(month.fee_ids),
                'opening': month.opening_balance or 0.0}

    @http.route('/api/manager/receivables', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_receivables(self, mt=None, **kw):
        """كشف الذمم المدينة (A/R): المفوتر − المُحصَّل لكل طالب عبر كل الشهور."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        students = request.env['nursery.student'].sudo().search(
            self._visible_student_domain(), order='name')
        rows = []
        for s in students:
            link = self._student_link_meta(s)
            books_paid = round(s.books_paid or 0.0, 2)
            books_remaining = round(
                max(0.0, BOOKS_FEE_DEFAULT - books_paid), 2)
            tuition_collected = round(
                sum(p.amount for p in s.payment_ids
                    if p.payment_type != 'books'), 2)
            rows.append({
                'id': s.id, 'name': s.name,
                'monthly_fee': round(s.fees or 0.0, 2),
                'billed': round(s.total_billed, 2),
                'collected': round(s.total_collected, 2),
                'receivable': round(s.receivable, 2),
                'books_due': round(BOOKS_FEE_DEFAULT, 2),
                'books_paid': books_paid,
                'books_remaining': books_remaining,
                'books_status': ('paid' if books_remaining <= 0.01 else
                                 ('partial' if books_paid > 0.01 else 'unpaid')),
                'guardian': link['parent_name'] or s.guardian_name or '',
                'phone': link['parent_phone'] or s.guardian_phone or '',
                'parent_email': link['parent_email'],
                'linked': link['linked'],
                'link_state': link['link_state'],
                'paid_until': (s.paid_until.strftime('%Y-%m-%d')
                               if s.paid_until else ''),
                'days_covered': days_for_amount(tuition_collected, s.fees),
            })
        rows.sort(key=lambda r: r['receivable'], reverse=True)
        # الشهر المتفق عليه = 30 يوماً (نفس قاسم كل التابات)
        tb = sum(r['billed'] for r in rows)
        tc = sum(r['collected'] for r in rows)
        return {
            'ok': True, 'manager': mgr.name, 'students': rows,
            'day_basis': DAY_BASIS,
            'totals': {
                'billed': round(tb, 2), 'collected': round(tc, 2),
                'receivable': round(tb - tc, 2),
                'books_billed': round(sum(r['books_due'] for r in rows), 2),
                'books_collected': round(sum(r['books_paid'] for r in rows), 2),
                'books_remaining': round(
                    sum(r['books_remaining'] for r in rows), 2),
                'debtors': len([r for r in rows if r['receivable'] > 0.01]),
                'prepaid': len([r for r in rows if r['receivable'] < -0.01]),
            },
        }

    @http.route('/api/manager/month/close', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_close(self, mt=None, ym=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        m = request.env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)
        if not m:
            return {'ok': False, 'error': 'الشهر غير موجود'}
        if m.state == 'closed':
            return {'ok': False, 'error': 'الشهر مقفول بالفعل'}
        m.write({'state': 'closed', 'closed_at': fields.Datetime.now(),
                 'closed_by': mgr.id})
        return {'ok': True, 'closing': self._month_totals(m)['closing'],
                'closed_by': mgr.name}

    @http.route('/api/manager/month/reopen', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_reopen(self, mt=None, ym=None, **kw):
        """فتح شهر مقفول — للأونر فقط (صمّام أمان)."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not mgr.has_group('base.group_system'):
            return {'ok': False, 'error': 'إعادة فتح الشهر صلاحية الأونر فقط'}
        m = request.env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)
        if not m:
            return {'ok': False, 'error': 'الشهر غير موجود'}
        m.write({'state': 'open', 'closed_at': False, 'closed_by': False})
        return {'ok': True}

    def _open_month_or_err(self, ym):
        m = request.env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)
        if not m:
            return None, {'ok': False, 'error': 'الشهر غير موجود'}
        if m.state == 'closed':
            return None, {'ok': False, 'error': 'الشهر مقفول — لا يمكن التعديل'}
        return m, None

    @http.route('/api/manager/month/opening', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_opening(self, mt=None, ym=None, value=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        m, err = self._open_month_or_err(ym)
        if err:
            return err
        try:
            m.opening_balance = float(value)
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'قيمة غير صالحة'}
        return {'ok': True, 'totals': self._month_totals(m)}

    @http.route('/api/manager/month/fee/add', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_fee_add(self, mt=None, ym=None, student_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        m, err = self._open_month_or_err(ym)
        if err:
            return err
        try:
            s = request.env['nursery.student'].sudo().browse(int(student_id))
            assert s.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        if s.id in m.fee_ids.mapped('student_id').ids:
            return {'ok': False, 'error': 'الطالب موجود في الشهر بالفعل'}
        f = self._ensure_month_fee_row(m, s)
        return {'ok': True, 'id': f.id}

    @http.route('/api/manager/month/fee/del', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_fee_del(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        f = request.env['nursery.month.fee'].sudo().browse(int(id or 0))
        if not f.exists():
            return {'ok': False, 'error': 'سطر غير موجود'}
        if f.month_id.state == 'closed':
            return {'ok': False, 'error': 'الشهر مقفول — لا يمكن التعديل'}
        if (f.paid or 0) > 0:
            return {'ok': False, 'error': 'الطالب دفع هذا الشهر — صفّري الدفعة أولاً'}
        f.unlink()
        return {'ok': True}

    @http.route('/api/manager/month/fee/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_fee_save(self, mt=None, id=None, fees=None,
                                   paid=None, paid_date=None, method=None,
                                   note=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        f = request.env['nursery.month.fee'].sudo().browse(int(id or 0))
        if not f.exists():
            return {'ok': False, 'error': 'سطر غير موجود'}
        m = f.month_id
        if m.state == 'closed':
            return {'ok': False, 'error': 'الشهر مقفول — لا يمكن التعديل'}
        amt = self._num(paid)
        vals = {'paid': amt,
                'note': (note or '').strip().replace('<', '').replace('>', '')[:200]}
        if fees not in (None, ''):
            vals['fees'] = self._num(fees)
        meth = method if method in ('cash', 'transfer', 'card', 'other') else 'cash'
        vals['method'] = meth
        pd = (paid_date or '').strip() or fields.Date.today().strftime('%Y-%m-%d')
        vals['paid_date'] = pd if amt > 0 else False
        Pay = request.env['nursery.fee.payment'].sudo()
        period = self._month_label(m.ym)
        st = f.student_id
        # الرسوم المتفق عليها (شهر = 30 يوماً) — أساس تحويل المبلغ إلى أيام.
        # رسوم الطالب هي المصدر، لأن full_fee على سطر الشهر غير موثوق (فيه
        # سطور بصفر أو بقيمة قديمة) — ولازم يطابق /student/pay وإعادة الحساب.
        monthly = (st.fees if st else 0.0) or f.full_fee or f.fees or 0.0
        months, extra = coverage_for(amt, monthly)
        # نقطة البداية = الاستحقاق قبل احتساب هذا السطر. تُخزَّن أول مرة فقط
        # حتى لا يتزحزح التاريخ مرّتين عند إعادة الحفظ أو تعديل المبلغ.
        anchor = f.until_before or (st.paid_until if st else False) \
            or (st.joining_date if st else False) or fields.Date.from_string(pd)
        vals['until_before'] = anchor if amt > 0 else False
        days = 0
        if amt > 0:
            # سند دفع حقيقي — يظهر لولي الأمر وفي الداشبورد
            new_until = advance_due(anchor, amt, monthly)
            days = (new_until - anchor).days
            pvals = {'date': pd, 'amount': amt, 'method': meth, 'period': period,
                     'days': days, 'until_before': anchor, 'until_after': new_until}
            if f.payment_id:
                f.payment_id.write(pvals)
            elif st:
                pvals['student_id'] = st.id
                vals['payment_id'] = Pay.create(pvals).id
            if st:
                st.write({'paid': True, 'paid_at': pd, 'payment_method': meth,
                          'paid_until': new_until})
        else:
            # إلغاء الدفعة — نرجّع الاستحقاق لما كان عليه قبل هذا السطر
            if f.payment_id:
                f.payment_id.unlink()
            vals['payment_id'] = False
            if st and f.until_before:
                st.write({'paid_until': f.until_before})
        vals['days_paid'] = days
        f.write(vals)
        return {'ok': True, 'days': days, 'months': months, 'extra_days': extra,
                'totals': self._month_totals(m)}

    @http.route('/api/manager/month/entry/add', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_entry_add(self, mt=None, ym=None, etype=None,
                                    name=None, amount=None, date=None,
                                    note=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        m, err = self._open_month_or_err(ym)
        if err:
            return err
        if etype not in ('income', 'expense', 'salary', 'reservation'):
            return {'ok': False, 'error': 'نوع غير معروف'}
        name = (name or '').strip().replace('<', '').replace('>', '')[:120]
        if not name:
            return {'ok': False, 'error': 'اكتبي البيان'}
        amt = self._num(amount)
        if amt <= 0:
            return {'ok': False, 'error': 'اكتبي مبلغاً صحيحاً'}
        d = (date or '').strip() or fields.Date.today().strftime('%Y-%m-%d')
        vals = {'month_id': m.id, 'etype': etype, 'name': name,
                'amount': amt, 'date': d,
                'note': (note or '').strip().replace('<', '').replace('>', '')[:200]}
        # مزامنة مع سجل المصروفات (الداشبورد): مصروف موجب / دخل وحجوزات سالب
        if etype in ('expense', 'income', 'reservation'):
            exp = request.env['nursery.expense'].sudo().create({
                'date': d, 'value': amt if etype == 'expense' else -amt,
                'note': name})
            vals['expense_id'] = exp.id
        e = request.env['nursery.month.entry'].sudo().create(vals)
        return {'ok': True, 'id': e.id, 'totals': self._month_totals(m)}

    @http.route('/api/manager/month/entry/del', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_entry_del(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        e = request.env['nursery.month.entry'].sudo().browse(int(id or 0))
        if not e.exists():
            return {'ok': False, 'error': 'قيد غير موجود'}
        m = e.month_id
        if m.state == 'closed':
            return {'ok': False, 'error': 'الشهر مقفول — لا يمكن التعديل'}
        if e.expense_id:
            e.expense_id.unlink()
        e.unlink()
        return {'ok': True, 'totals': self._month_totals(m)}

    @http.route('/api/manager/month/cashview', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_cashview(self, mt=None, ym=None, **kw):
        """الكاش الحقيقي: يفصل ما يُحصَّل فعلاً هذا الشهر عمّا هو مقدَّم
        لشهور قادمة (فيُرحَّل) وعمّا هو متأخّر (لم يُحصَّل بعد) — بدل الرقم
        الصافي الواحد في /month/get الذي يخلط الاثنين. لا يُعدّل أي بيانات،
        قراءة فقط من نفس حقول nursery.month.fee (fees/paid/carry_in)."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'accounts'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        if not self._ym_ok(ym):
            return {'ok': False, 'error': 'شهر غير صالح'}
        m = request.env['nursery.month'].sudo().search([('ym', '=', ym)], limit=1)
        if not m:
            return {'ok': False, 'error': 'الشهر غير مفتوح'}
        rows = []
        raw_collected = real_cash = advance_total = arrears_total = 0.0
        book_payments = request.env['nursery.fee.payment'].sudo().search([
            ('payment_type', '=', 'books'),
            ('date', '>=', '%s-01' % m.ym),
            ('date', '<=', self._month_last_day(m.ym)),
        ])
        books_collected = sum(book_payments.mapped('amount'))
        for f in m.fee_ids.sorted(key=lambda r: r.name or ''):
            fees = f.fees or 0.0
            paid = f.paid or 0.0
            carry_in = f.carry_in or 0.0
            carry_out = carry_in + paid - fees
            advance = max(0.0, carry_out)   # مدفوع مقدّماً لشهر قادم (يُرحَّل)
            owed = max(0.0, -carry_out)     # متأخّر عليه بعد خصم أي رصيد سابق
            real = paid - advance           # نصيب هذا الشهر فعلاً من المُحصَّل
            raw_collected += paid
            advance_total += advance
            arrears_total += owed
            real_cash += real
            if paid > 0.01 or fees > 0.01 or advance > 0.01 or owed > 0.01:
                rows.append({
                    'student_id': f.student_id.id or False, 'name': f.name,
                    'fees': round(fees, 2), 'paid': round(paid, 2),
                    'real': round(real, 2), 'advance': round(advance, 2),
                    'owed': round(owed, 2),
                })
        today = fields.Date.today()
        overdue = request.env['nursery.student'].sudo().search(
            [('active', '=', True), ('paid_until', '<', today)], order='paid_until')
        overdue_list = [{
            'id': s.id, 'name': s.name,
            'paid_until': s.paid_until.strftime('%Y-%m-%d') if s.paid_until else '',
            'days_late': (today - s.paid_until).days if s.paid_until else 0,
            'fees': s.fees or 0.0,
        } for s in overdue]
        return {
            'ok': True, 'ym': m.ym, 'label': self._month_label(m.ym), 'rows': rows,
            'totals': {
                'raw_collected': round(raw_collected, 2),
                'real_cash': round(real_cash, 2),
                'advance_total': round(advance_total, 2),
                'arrears_total': round(arrears_total, 2),
                'books_collected': round(books_collected, 2),
            },
            'overdue': overdue_list,
            'overdue_total': round(sum(s['fees'] for s in overdue_list), 2),
        }

    @http.route('/api/manager/month/salaries/import', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_month_salaries_import(self, mt=None, ym=None, **kw):
        """يستورد رواتب الموظفين (المستحق من صفحة المرتبات) كقيود رواتب."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        m, err = self._open_month_or_err(ym)
        if err:
            return err
        term = self._cur_term()
        Sal = request.env['nursery.salary'].sudo()
        Entry = request.env['nursery.month.entry'].sudo()
        existing = set(e.name for e in m.entry_ids if e.etype == 'salary')
        added = 0
        for emp in request.env['hr.employee'].sudo().search(
                [('active', '=', True)], order='name'):
            if emp.name in existing:
                continue
            sal = (Sal.search([('employee_id', '=', emp.id), ('term', '=', term)], limit=1)
                   or Sal.search([('teacher', '=', emp.name), ('term', '=', term)], limit=1))
            amount = (sal.actual or sal.expected) if sal else 0.0
            if amount <= 0:
                continue
            Entry.create({'month_id': m.id, 'etype': 'salary',
                          'name': emp.name, 'amount': amount,
                          'date': fields.Date.today().strftime('%Y-%m-%d')})
            added += 1
        return {'ok': True, 'added': added, 'totals': self._month_totals(m)}

    # ==================== الألبومات (تحكم المديرة) ====================
    @http.route('/api/manager/albums', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_albums(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'albums'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        import re as _re
        safe = _re.compile(r'^[A-Za-z0-9_-]+$')
        albums = request.env['nursery.album'].sudo().with_context(
            active_test=False).search([], order='sequence, id desc')
        out = []
        for a in albums:
            cover = a.cover_file_id or (a.photo_ids[:1].drive_id if a.photo_ids else '')
            if cover and not safe.match(cover):
                cover = ''
            out.append({
                'id': a.id, 'name': a.name,
                'count': a.photo_count,
                'cover': cover or False,
                'active': bool(a.active),
                'parent_visible': bool(a.parent_visible),
                'site_visible': bool(a.site_visible),
            })
        return {'ok': True, 'manager': mgr.name, 'albums': out}

    @http.route('/api/manager/album/toggle', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_album_toggle(self, mt=None, id=None, field=None, value=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if field not in ('parent_visible', 'site_visible', 'active'):
            return {'ok': False, 'error': 'حقل غير معروف'}
        try:
            a = request.env['nursery.album'].sudo().with_context(
                active_test=False).browse(int(id))
            assert a.exists()
        except Exception:
            return {'ok': False, 'error': 'ألبوم غير موجود'}
        a.write({field: bool(value)})
        return {'ok': True}

    @http.route('/api/manager/album/rename', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_album_rename(self, mt=None, id=None, name=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        name = (name or '').strip().replace('<', '').replace('>', '')
        if not name:
            return {'ok': False, 'error': 'اكتبي اسم الألبوم'}
        try:
            a = request.env['nursery.album'].sudo().with_context(
                active_test=False).browse(int(id))
            assert a.exists()
        except Exception:
            return {'ok': False, 'error': 'ألبوم غير موجود'}
        a.name = name
        return {'ok': True}

    # ==================== إضافة / تعديل الموظفين (معلّمات) ====================
    @http.route('/api/manager/staff/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_staff_save(self, mt=None, id=None, name=None, job=None,
                               exempt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        name = (name or '').strip().replace('<', '').replace('>', '')
        if not name:
            return {'ok': False, 'error': 'اكتب اسم الموظف'}
        vals = {
            'name': name,
            'job_title': (job or '').strip().replace('<', '').replace('>', ''),
            'attendance_exempt': bool(exempt),
        }
        Emp = request.env['hr.employee'].sudo()
        if id:
            e = Emp.browse(int(id))
            if not e.exists():
                return {'ok': False, 'error': 'موظف غير موجود'}
            e.write(vals)
            eid = e.id
        else:
            eid = Emp.create(vals).id
        return {'ok': True, 'id': eid}

    @http.route('/api/manager/staff/delete', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_staff_delete(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            e = request.env['hr.employee'].sudo().browse(int(id))
            if e.exists():
                e.active = False
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'موظف غير موجود'}
        return {'ok': True}

    @http.route('/register-child', type='http', auth='public', website=False,
                methods=['POST'], csrf=False, sitemap=False)
    def register_child(self, **post):
        """فورم التسجيل من الموقع التسويقي → يعمل طالب جديد للمراجعة."""
        child = (post.get('child_name') or '').strip()
        guardian = (post.get('guardian_name') or '').strip()
        phone = (post.get('phone') or '').strip()
        if not child or not phone:
            return request.make_response(
                json.dumps({'ok': False, 'error': 'الاسم والتليفون مطلوبين'}),
                headers=[('Content-Type', 'application/json')])
        note = 'تسجيل جديد من الموقع'
        if post.get('age'):
            note += ' — السن: %s' % (post.get('age') or '')[:40]
        request.env['nursery.student'].sudo().create({
            'name': child[:120],
            'guardian_name': guardian[:120] or False,
            'guardian_phone': phone[:40],
            'term': 'term_2027',
            'paid': False,
            'remark': note,
        })
        return request.make_response(
            json.dumps({'ok': True}),
            headers=[('Content-Type', 'application/json'),
                     ('Access-Control-Allow-Origin', 'https://montessori-ksa.com')])


class NurseryRoles(http.Controller):

    def _parent_link_candidates(self, user):
        """الأطفال المقترحون من طلبات الربط، ثم من اسم ولي الأمر كاحتياط."""
        env = request.env
        email = (user.email or user.login or '').strip().lower()
        Req = env['nursery.link.request'].sudo()
        requests = Req.search([
            ('parent_email', '=', email),
            ('state', 'in', ('pending', 'linked')),
            ('matched_student_id', '!=', False),
        ], order='create_date desc') if email else Req.browse()
        seen = set()
        candidates = env['nursery.student'].sudo().browse()
        for req in requests:
            student = req.matched_student_id
            if student.active and student.id not in seen:
                candidates |= student
                seen.add(student.id)
        if not candidates and user.name:
            candidates = env['nursery.student'].sudo().search([
                ('active', '=', True), ('guardian_name', '=ilike', user.name.strip()),
            ], order='name')
        return candidates

    def _role_of(self, user):
        if user.has_group('base.group_system'):
            return ('أونر / أدمن', 't-owner')
        if user.has_group('nursery.group_nursery_manager'):
            return ('مديرة', 't-mgr')
        if user.has_group('nursery.group_nursery_teacher'):
            return ('مدرسة', 't-teach')
        students = request.env['nursery.student'].sudo().search_count(
            _parent_student_domain(user.id))
        if students:
            return ('ولي أمر (%d طفل)' % students, 't-parent')
        if user._is_internal():
            return ('عاملة', 't-work')
        return ('بدون دور', 't-none')

    @http.route('/nursery-roles', type='http', auth='user', website=False, csrf=False)
    def roles_page(self, done='', **kw):
        if not _is_manager():
            raise werkzeug.exceptions.Forbidden()
        env = request.env
        users = env['res.users'].sudo().search(
            [('active', '=', True), ('id', 'not in',
              [env.ref('base.user_root').id, env.ref('base.public_user').id])],
            order='create_date desc')
        students = env['nursery.student'].sudo().search(
            [('active', '=', True)], order='name')

        html = [ROLES_PAGE_TOP]
        if done:
            html.append('<div class="msg">✅ %s</div>' % e(done))
        html.append('<div class="card">')
        for u in users:
            label, cls = self._role_of(u)
            linked = env['nursery.student'].sudo().search(
                _parent_student_domain(u.id))
            linked_txt = (' — مربوط بـ: ' + '، '.join(linked.mapped('name'))) if linked else ''
            suggested = self._parent_link_candidates(u)
            suggested_ids = set(suggested.ids)
            opts = ''.join('<option value="%d"%s>%s%s</option>' % (
                s.id, ' selected' if len(suggested) == 1 and s.id in suggested_ids else '',
                e(s.name),
                (' — تطابق البريد' if s.id in suggested_ids else ''))
                           for s in students)
            html.append(
                '<div class="u"><div class="info"><b>%s</b>'
                '<small>%s%s</small></div>'
                '<span class="tag %s">%s</span>'
                '<form method="post" action="/nursery-roles/assign">'
                '<input type="hidden" name="user_id" value="%d"/>'
                '<select name="role">'
                '<option value="teacher">مدرسة</option>'
                '<option value="worker">عاملة</option>'
                '<option value="parent">ولي أمر</option>'
                '</select> '
                '<select name="student_id"><option value="">— الطفل (لولي الأمر) —</option>%s</select> '
                '<button class="go" type="submit">تعيين</button>'
                '</form></div>'
                % (e(u.name), e(u.login), e(linked_txt), cls, e(label), u.id, opts))
        html.append('</div></body></html>')
        return request.make_response(''.join(html), headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-store')])

    # ---------- APIs توزيع الأدوار للموقع (بتوكن المديرة) ----------

    @http.route('/api/roles/users', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_roles_users(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'roles'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        env = request.env
        users = env['res.users'].sudo().search(
            [('active', '=', True), ('id', 'not in',
             [env.ref('base.user_root').id, env.ref('base.public_user').id])],
            order='create_date desc', limit=300)
        students = env['nursery.student'].sudo().search(
            [('active', '=', True)], order='name')
        out = []
        for u in users:
            label, cls = self._role_of(u)
            linked = env['nursery.student'].sudo().search(
                _parent_student_domain(u.id))
            suggested = self._parent_link_candidates(u)
            out.append({
                'id': u.id, 'name': u.name, 'login': u.login,
                'role': label, 'cls': cls, 'is_owner': u.has_group('base.group_system'),
                'link_state': 'linked' if linked else 'unlinked',
                'linked': '، '.join(linked.mapped('name')) if linked else '',
                'suggested_students': [{'id': s.id, 'name': s.name,
                                        'class_name': s.class_id.name or '',
                                        'level': s.level or ''}
                                       for s in suggested],
            })
        return {'ok': True, 'manager': mgr.name,
                'caller_is_owner': mgr.has_group('base.group_system'),
                'caller_id': mgr.id,
                'users': out,
                'students': [{'id': s.id, 'name': s.name} for s in students]}

    @http.route('/api/roles/assign', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_roles_assign(self, mt=None, user_id=None, role=None, student_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if _mgr_page_blocked(mgr, 'roles'):
            return {'ok': False, 'error': PAGE_BLOCKED_MSG}
        env = request.env
        try:
            user = env['res.users'].sudo().browse(int(user_id))
            assert user.exists()
        except Exception:
            return {'ok': False, 'error': 'مستخدم غير موجود'}
        ref = env.ref
        g_internal = ref('base.group_user')
        g_portal = ref('base.group_portal')
        g_teacher = ref('nursery.group_nursery_teacher')
        g_manager = ref('nursery.group_nursery_manager')
        g_system = ref('base.group_system')
        g_erp = ref('base.group_erp_manager')
        caller_is_owner = mgr.has_group('base.group_system')
        # ===== منح / إلغاء الأونر — للأونر فقط. الحارس هنا في الباك-إند نفسه:
        # المديرة ممنوعة حتى لو بعتت role=owner مباشرةً على الـAPI. =====
        if role in ('owner', 'revoke_owner'):
            if not caller_is_owner:
                return {'ok': False, 'error': 'صلاحية الأونر للأونر فقط'}
            if role == 'owner':
                user.write({'groups_id': [(3, g_portal.id), (4, g_internal.id),
                                          (4, g_system.id)]})
                return {'ok': True, 'msg': '%s بقى أونر (صلاحية كاملة) ✓' % user.name}
            # revoke_owner
            if user.id == mgr.id:
                return {'ok': False, 'error': 'مينفعش تلغي الأونر عن نفسك'}
            if not user.has_group('base.group_system'):
                return {'ok': False, 'error': 'الحساب ده مش أونر أصلاً'}
            if env['res.users'].sudo().search_count(
                    [('groups_id', 'in', g_system.id), ('active', '=', True)]) <= 1:
                return {'ok': False, 'error': 'مينفعش تلغي آخر أونر'}
            user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                      (3, g_manager.id), (3, g_teacher.id)],
                        'nursery_api_token': False})
            return {'ok': True, 'msg': 'اتلغى الأونر عن %s ✓' % user.name}
        # أي دور غير الأونر: انزع مجموعة الأونر/المديرة صراحةً + أبطل توكن الـAPI القديم
        # (وإلا يفضل المستخدم المُنزَّل مديراً فعلياً وتوكنه شغّال)
        if user.has_group('base.group_system'):
            if not caller_is_owner:
                return {'ok': False, 'error': 'مينفعش تعديل حساب الأونر'}
            if user.id == mgr.id:
                return {'ok': False, 'error': 'مينفعش تغيّر دور الأونر لنفسك'}
            if env['res.users'].sudo().search_count(
                    [('groups_id', 'in', g_system.id), ('active', '=', True)]) <= 1:
                return {'ok': False, 'error': 'مينفعش تلغي آخر أونر'}
        if role == 'teacher':
            user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                      (3, g_portal.id), (3, g_manager.id),
                                      (4, g_internal.id), (4, g_teacher.id)],
                        'nursery_api_token': False})
            self._ensure_employee(user)
            return {'ok': True, 'msg': '%s بقت مدرسة ✓' % user.name}
        if role == 'worker':
            user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                      (3, g_portal.id), (3, g_manager.id),
                                      (4, g_internal.id), (3, g_teacher.id)],
                        'nursery_api_token': False})
            self._ensure_employee(user)
            return {'ok': True, 'msg': '%s بقت عاملة ✓' % user.name}
        if role == 'parent':
            try:
                sid = int(student_id) if student_id else 0
            except (TypeError, ValueError):
                sid = 0
            if sid:
                student = env['nursery.student'].sudo().browse(sid)
            else:
                suggested = self._parent_link_candidates(user)
                if len(suggested) != 1:
                    return {'ok': False, 'error': 'اختاري الطفل الصحيح من الاقتراحات',
                            'suggested_students': [{'id': s.id, 'name': s.name}
                                                   for s in suggested]}
                student = suggested
            if not student.exists():
                return {'ok': False, 'error': 'طفل غير موجود'}
            user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                      (3, g_internal.id), (3, g_teacher.id),
                                      (3, g_manager.id), (4, g_portal.id)],
                        'nursery_api_token': False})
            student._link_parent_user(user)
            if not student.guardian_name:
                student.write({'guardian_name': user.name})
            return {'ok': True, 'msg': '%s بقى ولي أمر %s ✓' % (user.name, student.name)}
        return {'ok': False, 'error': 'دور غير صحيح'}

    # ============ صلاحيات الأدوار — للأونر فقط ============
    @http.route('/api/perms/get', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_perms_get(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not mgr.has_group('base.group_system'):
            return {'ok': False, 'error': 'صفحة الصلاحيات للأونر فقط'}
        return {'ok': True, 'owner': mgr.name,
                'catalog': PERM_CATALOG, 'perms': role_perms(request.env)}

    @http.route('/api/perms/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_perms_save(self, mt=None, perms=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not mgr.has_group('base.group_system'):
            return {'ok': False, 'error': 'صفحة الصلاحيات للأونر فقط'}
        incoming = perms if isinstance(perms, dict) else {}
        clean = {}
        for role, caps in PERM_DEFAULTS.items():
            clean[role] = {}
            for k, dflt in caps.items():
                v = (incoming.get(role) or {}).get(k)
                clean[role][k] = bool(v) if v is not None else dflt
        request.env['ir.config_parameter'].sudo().set_param(
            'nursery.role_perms', json.dumps(clean))
        return {'ok': True, 'perms': clean}

    @http.route('/api/manager/stats_sso', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_stats_sso(self, mt=None, **kw):
        """رابط دخول لحظي للوحة الإحصائيات (Grafana) — للأونر فقط.
        نوقّع JWT قصير العمر (60 ثانية) بمفتاح RSA خاص، وGrafana تتحقق منه
        بالمفتاح العام (auth.jwt + url_login)."""
        import base64
        import time as _time
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not _stats_allowed(request.env, mgr):
            return {'ok': False, 'error': 'لوحة الإحصائيات مخصّصة لحساب المالك'}
        ICP = request.env['ir.config_parameter'].sudo()
        key_b64 = (ICP.get_param('nursery.stats_sso_key_b64') or '').strip()
        base = (ICP.get_param('nursery.stats_url')
                or 'https://stats.montessori-ksa.com').rstrip('/')
        if not key_b64:
            return {'ok': False, 'error': 'الدخول التلقائي لم يُفعَّل بعد'}
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as _pad

            def _b64u(raw):
                return base64.urlsafe_b64encode(raw).decode().rstrip('=')

            key = serialization.load_pem_private_key(
                base64.b64decode(key_b64), password=None)
            now = int(_time.time())
            email = (mgr.email or mgr.login or '').strip().lower()
            header = {'alg': 'RS256', 'typ': 'JWT', 'kid': 'nursery-sso'}
            payload = {'iss': 'nursery-site', 'aud': 'grafana',
                       'sub': email, 'email': email,
                       'name': mgr.name or '', 'role': 'Admin',
                       'iat': now, 'nbf': now - 5, 'exp': now + 60}
            signing_input = (
                _b64u(json.dumps(header, separators=(',', ':')).encode()) + '.' +
                _b64u(json.dumps(payload, separators=(',', ':')).encode()))
            sig = key.sign(signing_input.encode(), _pad.PKCS1v15(), hashes.SHA256())
            token = signing_input + '.' + _b64u(sig)
            return {'ok': True, 'url': '%s/sso?t=%s' % (base, token)}
        except Exception:
            return {'ok': False, 'error': 'تعذّر إنشاء رابط الدخول'}

    @http.route('/api/manager/beszel_sso', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_beszel_sso(self, mt=None, **kw):
        """رابط دخول لحظي للوحة حالة السيرفر (Beszel/PocketBase) — للمالك فقط.
        PocketBase يوقّع توكن الدخول بـ HS256 ومفتاحه = tokenKey للسجل + سر
        المجموعة، فنصدر التوكن بنفس الطريقة بدل تخزين كلمة سر."""
        import base64
        import hashlib
        import hmac
        import time as _time
        import requests
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        if not _stats_allowed(request.env, mgr):
            return {'ok': False, 'error': 'لوحة حالة السيرفر مخصّصة لحساب المالك'}
        ICP = request.env['ir.config_parameter'].sudo()
        tk = (ICP.get_param('nursery.beszel_token_key') or '').strip()
        sec = (ICP.get_param('nursery.beszel_auth_secret') or '').strip()
        rid = (ICP.get_param('nursery.beszel_user_id') or '').strip()
        cid = (ICP.get_param('nursery.beszel_collection_id') or '').strip()
        base = (ICP.get_param('nursery.beszel_url')
                or 'https://mon.montessori-ksa.com').rstrip('/')
        if not (tk and sec and rid and cid):
            return {'ok': False, 'error': 'الدخول التلقائي لم يُفعَّل بعد'}
        try:
            def _b64u(raw):
                return base64.urlsafe_b64encode(raw).decode().rstrip('=')

            now = int(_time.time())
            header = {'alg': 'HS256', 'typ': 'JWT'}
            payload = {'collectionId': cid, 'exp': now + 604800, 'id': rid,
                       'refreshable': True, 'type': 'auth'}
            signing_input = (
                _b64u(json.dumps(header, separators=(',', ':')).encode()) + '.' +
                _b64u(json.dumps(payload, separators=(',', ':')).encode()))
            sig = hmac.new((tk + sec).encode(), signing_input.encode(),
                           hashlib.sha256).digest()
            token = signing_input + '.' + _b64u(sig)

            rec = {}
            try:
                resp = requests.get(
                    '%s/api/collections/users/records/%s' % (base, rid),
                    headers={'Authorization': token}, timeout=8)
                if resp.ok:
                    rec = resp.json()
            except Exception:
                rec = {}
            if not rec:
                return {'ok': False, 'error': 'تعذّر التحقق من حساب اللوحة'}

            blob = _b64u(json.dumps({'token': token, 'record': rec}).encode())
            return {'ok': True, 'url': '%s/sso#%s' % (base, blob)}
        except Exception:
            return {'ok': False, 'error': 'تعذّر إنشاء رابط الدخول'}

    @http.route('/api/stats/verify', type='http', auth='public',
                methods=['GET'], csrf=False, save_session=False)
    def api_stats_verify(self, **kw):
        """تحقّق من توكن الدخول اللحظي — يناديه nginx عبر auth_request.
        200 + ترويسة X-Sso-User عند النجاح، وإلا 403."""
        import base64
        import time as _time
        uri = request.httprequest.headers.get('X-Original-URI') or ''
        token = ''
        if 't=' in uri:
            token = uri.split('t=', 1)[1].split('&', 1)[0]
        token = werkzeug.urls.url_unquote(token or '')
        if not token or token.count('.') != 2:
            raise werkzeug.exceptions.Forbidden()
        ICP = request.env['ir.config_parameter'].sudo()
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as _pad

            def _unb64(part):
                return base64.urlsafe_b64decode(part + '=' * (-len(part) % 4))

            key_b64 = (ICP.get_param('nursery.stats_sso_key_b64') or '').strip()
            priv = serialization.load_pem_private_key(
                base64.b64decode(key_b64), password=None)
            h_b64, p_b64, s_b64 = token.split('.')
            priv.public_key().verify(_unb64(s_b64),
                                     ('%s.%s' % (h_b64, p_b64)).encode(),
                                     _pad.PKCS1v15(), hashes.SHA256())
            payload = json.loads(_unb64(p_b64))
        except Exception:
            raise werkzeug.exceptions.Forbidden()
        now = int(_time.time())
        if payload.get('iss') != 'nursery-site' or payload.get('aud') != 'grafana':
            raise werkzeug.exceptions.Forbidden()
        if int(payload.get('exp') or 0) < now or int(payload.get('nbf') or now) > now:
            raise werkzeug.exceptions.Forbidden()
        email = (payload.get('email') or '').strip().lower()
        allowed = (ICP.get_param('nursery.stats_sso_emails') or '')
        allowed = [x.strip() for x in allowed.lower().replace(',', ' ').split()
                   if x.strip()]
        if not email or (allowed and email not in allowed):
            raise werkzeug.exceptions.Forbidden()
        return request.make_response('', headers=[('X-Sso-User', email)])

    @http.route('/api/perms/nav', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_perms_nav(self, mt=None, **kw):
        """بنود القائمة العلوية المقفولة عن حامل التوكن (للمديرة). الأونر = لا شيء مخفي."""
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'hidden': []}
        stats_ok = _stats_allowed(request.env, mgr)
        if mgr.has_group('base.group_system'):
            return {'ok': True, 'is_owner': True, 'is_stats': stats_ok,
                    'hidden': []}
        perms = role_perms(request.env).get('manager', {})
        # «الصلاحيات» صفحة للأونر فقط — تُخفى دائماً من قائمة المديرة
        return {'ok': True, 'is_owner': False, 'is_stats': stats_ok,
                'hidden': ['permissions'] + [p for p in MANAGER_PAGES if not perms.get(p, True)]}

    @http.route('/nursery-roles/assign', type='http', auth='user',
                website=False, csrf=False, methods=['POST'])
    def roles_assign(self, user_id=None, role=None, student_id=None, **kw):
        if not _is_manager():
            raise werkzeug.exceptions.Forbidden()
        env = request.env
        try:
            user = env['res.users'].sudo().browse(int(user_id))
            assert user.exists()
        except Exception:
            return request.redirect('/nursery-roles')

        ref = env.ref
        g_internal = ref('base.group_user')
        g_portal = ref('base.group_portal')
        g_teacher = ref('nursery.group_nursery_teacher')
        g_manager = ref('nursery.group_nursery_manager')
        g_system = ref('base.group_system')
        g_erp = ref('base.group_erp_manager')
        caller_is_owner = request.env.user.has_group('base.group_system')

        # الأونر يقدر يخفض أونراً آخر، مع منع المديرة ومنع فقدان آخر أونر.
        if user.has_group('base.group_system'):
            if not caller_is_owner:
                return request.redirect('/nursery-roles?done=' +
                                        'مينفعش تعديل حساب الأونر')
            if user.id == request.env.user.id:
                return request.redirect('/nursery-roles?done=' +
                                        'مينفعش تغيّر دور الأونر لنفسك')
            if env['res.users'].sudo().search_count(
                    [('groups_id', 'in', g_system.id), ('active', '=', True)]) <= 1:
                return request.redirect('/nursery-roles?done=' +
                                        'مينفعش تلغي آخر أونر')

        msg = 'تم'
        if role == 'teacher':
            user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                      (3, g_portal.id), (3, g_manager.id),
                                      (4, g_internal.id), (4, g_teacher.id)],
                        'nursery_api_token': False})
            self._ensure_employee(user)
            msg = '%s بقت مدرسة ✓' % user.name
        elif role == 'worker':
            user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                      (3, g_portal.id), (3, g_manager.id),
                                      (4, g_internal.id), (3, g_teacher.id)],
                        'nursery_api_token': False})
            self._ensure_employee(user)
            msg = '%s بقت عاملة ✓' % user.name
        elif role == 'parent':
            try:
                sid = int(student_id)
            except (TypeError, ValueError):
                return request.redirect('/nursery-roles?done=' +
                                        'اختاري الطفل الأول لولي الأمر')
            student = env['nursery.student'].sudo().browse(sid)
            if student.exists():
                # ولي الأمر = بورتال فقط (مايشوفش النظام الداخلي)
                user.write({'groups_id': [(3, g_system.id), (3, g_erp.id),
                                          (3, g_internal.id), (3, g_teacher.id),
                                          (3, g_manager.id), (4, g_portal.id)],
                            'nursery_api_token': False})
                student._link_parent_user(user)
                if not student.guardian_name:
                    student.write({'guardian_name': user.name})
                msg = '%s بقى ولي أمر %s ✓ — يدخل من /my-child' % (user.name, student.name)
        return request.redirect('/nursery-roles?done=' + msg)

    def _ensure_employee(self, user):
        Emp = request.env['hr.employee'].sudo()
        if not Emp.search([('user_id', '=', user.id)], limit=1):
            Emp.create({'name': user.name, 'user_id': user.id})

    # ---------- مدخل ولي الأمر بحساب جوجل ----------

    @http.route('/my-child', type='http', auth='user', website=False)
    def my_child(self, **kw):
        env = request.env
        students = _parent_students(env, env.user)
        if not students:
            page = ('<html dir="rtl"><body style="font-family:Tahoma;text-align:center;'
                    'padding:60px 20px;background:#f5f3ff;">'
                    '<h2 style="color:#7c3aed;">🌸 أهلاً %s</h2>'
                    '<p style="color:#555;margin-top:12px;">حسابك لم يُربط بطفل بعد — '
                    'يرجى التواصل مع إدارة الحضانة وسيتم ربطك بطفلك خلال دقائق.</p>'
                    '</body></html>' % e(env.user.name))
            return request.make_response(page, headers=[
                ('Content-Type', 'text/html; charset=utf-8')])
        if len(students) == 1:
            return request.redirect('/parent/%s' % students.portal_token)
        links = ''.join(
            '<a style="display:block;background:#fff;border-radius:14px;padding:16px;'
            'margin:10px auto;max-width:400px;text-decoration:none;color:#4c1d95;'
            'font-weight:700;box-shadow:0 1px 6px rgba(0,0,0,.1);" href="/parent/%s">👧 %s</a>'
            % (s.portal_token, e(s.name)) for s in students)
        page = ('<html dir="rtl"><body style="font-family:Tahoma;text-align:center;'
                'padding:40px 16px;background:#f5f3ff;">'
                '<h2 style="color:#7c3aed;">🌸 اختار الطفل</h2>%s</body></html>' % links)
        return request.make_response(page, headers=[
            ('Content-Type', 'text/html; charset=utf-8')])
