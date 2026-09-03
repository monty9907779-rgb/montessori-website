# -*- coding: utf-8 -*-
"""صفحة توزيع الأدوار للمديرة + مدخل ولي الأمر بحساب جوجل (/my-child)
+ نقطة الدخول الموحّدة SSO (/portal-login → جوجل → /portal-home حسب الدور)."""
import json
import re

import werkzeug.exceptions
import werkzeug.urls
from markupsafe import escape as e

from odoo import http, fields
from odoo.http import request


WEBSITE = 'https://montessori-ksa.com'


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
            [('parent_user_id', '=', u.id), ('active', '=', True)], limit=1)
        # لو المديرة اعتمدت الطلب قبل ما ولي الأمر يسجل دخول بجوجل،
        # نربطه دلوقتي حسب إيميله (مطابقة بالضبط — u.login قيمة موثوقة)
        if not student:
            req = request.env['nursery.link.request'].sudo().search(
                [('parent_email', '=', (u.login or '').strip().lower()),
                 ('state', '=', 'linked'),
                 ('matched_student_id', '!=', False)], limit=1)
            if req and req.matched_student_id.active:
                req.matched_student_id.parent_user_id = u.id
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
        student = Stu.search([('parent_user_id', '=', u.id), ('active', '=', True)], limit=1)
        if not student:
            req = request.env['nursery.link.request'].sudo().search(
                [('parent_email', '=', (u.login or '').strip().lower()),
                 ('state', '=', 'linked'), ('matched_student_id', '!=', False)], limit=1)
            if req and req.matched_student_id.active:
                req.matched_student_id.parent_user_id = u.id
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
        Cls = request.env['nursery.class'].sudo()
        Emp = request.env['hr.employee'].sudo()
        Stu = request.env['nursery.student'].sudo()
        classes = Cls.search([], order='name')
        teachers = Emp.search([('active', '=', True)], order='name')
        students = Stu.search([('active', '=', True)], order='name')
        return {
            'ok': True, 'manager': mgr.name,
            'classes': [{
                'id': c.id, 'name': c.name,
                'teacher_id': c.teacher_id.id or False,
                'teacher_name': c.teacher_id.name or '',
                'capacity': c.capacity,
                'student_count': c.student_count,
                'student_ids': c.student_ids.ids,
            } for c in classes],
            'teachers': [{'id': t.id, 'name': t.name} for t in teachers],
            'students': [{'id': s.id, 'name': s.name,
                          'class_id': s.class_id.id or False} for s in students],
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
            'nursery': company.name or 'حضانة مونتيسوري',
        }}

    # ==================== الطلاب + الدفعات ====================
    _AR_MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

    def _num(self, v):
        try:
            return max(0.0, float(v))
        except (TypeError, ValueError):
            return 0.0

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
        last = s.payment_ids.sorted(lambda p: (p.date or fields.Date.today()), reverse=True)[:1]
        return {
            'id': s.id, 'name': s.name,
            'class_id': s.class_id.id or False,
            'class_name': s.class_id.name or '',
            'guardian_name': s.guardian_name or '',
            'guardian_phone': s.guardian_phone or '',
            'fees': s.fees or 0.0,
            'total_paid': s.total_paid or 0.0,
            'paid': bool(s.paid),
            'paid_at': s.paid_at.strftime('%Y-%m-%d') if s.paid_at else '',
            'paid_until': s.paid_until.strftime('%Y-%m-%d') if s.paid_until else '',
            'joining_date': s.joining_date.strftime('%Y-%m-%d') if s.joining_date else '',
            'linked': bool(s.parent_user_id),
            'last_amount': (last.amount if last else 0.0),
            'last_date': (last.date.strftime('%Y-%m-%d') if (last and last.date) else ''),
            'payments_count': len(s.payment_ids),
            'status': status, 'days': days,
        }

    @http.route('/api/manager/students', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_students(self, mt=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        Stu = request.env['nursery.student'].sudo()
        Cls = request.env['nursery.class'].sudo()
        students = Stu.search([('active', '=', True)], order='name')
        classes = Cls.search([], order='name')
        return {
            'ok': True, 'manager': mgr.name,
            'students': [self._student_row(s) for s in students],
            'classes': [{'id': c.id, 'name': c.name} for c in classes],
        }

    @http.route('/api/manager/student/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_save(self, mt=None, id=None, name=None, class_id=None,
                                 guardian_name=None, guardian_phone=None,
                                 fees=None, joining_date=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        name = (name or '').strip().replace('<', '').replace('>', '')
        if not name:
            return {'ok': False, 'error': 'اكتب اسم الطالب'}
        vals = {
            'name': name,
            'guardian_name': (guardian_name or '').strip().replace('<', '').replace('>', ''),
            'guardian_phone': (guardian_phone or '').strip(),
            'fees': self._num(fees),
        }
        try:
            vals['class_id'] = int(class_id) if class_id else False
        except (TypeError, ValueError):
            vals['class_id'] = False
        vals['joining_date'] = (joining_date or '').strip() or False
        Stu = request.env['nursery.student'].sudo()
        if id:
            s = Stu.browse(int(id))
            if not s.exists():
                return {'ok': False, 'error': 'طالب غير موجود'}
            s.write(vals)
            sid = s.id
        else:
            sid = Stu.create(vals).id
        return {'ok': True, 'id': sid}

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
        except (TypeError, ValueError):
            return {'ok': False, 'error': 'طالب غير موجود'}
        return {'ok': True}

    @http.route('/api/manager/student/pay', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_student_pay(self, mt=None, student_id=None, amount=None,
                                date=None, paid_until=None, method=None,
                                period=None, note=None, **kw):
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
        pay_date = (date or '').strip() or fields.Date.today().strftime('%Y-%m-%d')
        if self._closed_month_of(pay_date):
            return {'ok': False, 'error': 'هذا التاريخ داخل شهر محاسبي مقفول — لا يمكن التسجيل فيه'}
        pu = (paid_until or '').strip() or False
        meth = method if method in ('cash', 'transfer', 'card', 'other') else 'cash'
        per = (period or '').strip()
        if not per and pu:
            try:
                d = fields.Date.from_string(pu)
                per = '%s %s' % (self._AR_MONTHS[d.month - 1], d.year)
            except Exception:
                per = ''
        request.env['nursery.fee.payment'].sudo().create({
            'student_id': s.id, 'date': pay_date, 'amount': amt,
            'method': meth, 'period': per,
            'note': (note or '').strip().replace('<', '').replace('>', ''),
        })
        vals = {'paid': True, 'paid_at': pay_date, 'payment_method': meth}
        if pu:
            vals['paid_until'] = pu
        s.write(vals)
        return {'ok': True, 'row': self._student_row(s)}

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
        pays = s.payment_ids.sorted(lambda p: (p.date or fields.Date.today()), reverse=True)
        return {'ok': True, 'name': s.name, 'total_paid': s.total_paid or 0.0,
                'payments': [{
                    'id': p.id,
                    'date': p.date.strftime('%Y-%m-%d') if p.date else '',
                    'amount': p.amount or 0.0,
                    'method': MLBL.get(p.method, p.method or ''),
                    'period': p.period or '', 'note': p.note or '',
                } for p in pays]}

    @http.route('/api/manager/payment/delete', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_manager_payment_delete(self, mt=None, id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        try:
            p = request.env['nursery.fee.payment'].sudo().browse(int(id))
            sid = p.student_id.id
            if p.exists():
                if p.date and self._closed_month_of(p.date.strftime('%Y-%m-%d')):
                    return {'ok': False,
                            'error': 'هذه الدفعة داخل شهر محاسبي مقفول — لا يمكن حذفها'}
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

    def _month_totals(self, month):
        inc_students = sum(month.fee_ids.mapped('paid'))
        inc_other = sum(e.amount for e in month.entry_ids if e.etype == 'income')
        expenses = sum(e.amount for e in month.entry_ids if e.etype == 'expense')
        salaries = sum(e.amount for e in month.entry_ids if e.etype == 'salary')
        net = inc_students + inc_other - expenses - salaries
        return {
            'income_students': inc_students, 'income_other': inc_other,
            'expenses': expenses, 'salaries': salaries, 'net': net,
            'closing': (month.opening_balance or 0.0) + net,
            'due_total': sum(month.fee_ids.mapped('fees')),
            'unpaid_count': len(month.fee_ids.filtered(lambda f: (f.paid or 0) <= 0)),
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
        Months = request.env['nursery.month'].sudo()
        months = Months.search([], order='ym desc')
        out = []
        for m in months:
            t = self._month_totals(m)
            out.append({'ym': m.ym, 'label': self._month_label(m.ym),
                        'state': m.state, 'opening': m.opening_balance or 0.0,
                        'net': t['net'], 'closing': t['closing']})
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
        in_month = set(m.fee_ids.mapped('student_id').ids)
        avail = request.env['nursery.student'].sudo().search(
            [('active', '=', True), ('id', 'not in', list(in_month))], order='name')
        MLBL = dict(request.env['nursery.month.fee']._fields['method'].selection or [])
        return {
            'ok': True, 'ym': m.ym, 'label': self._month_label(m.ym),
            'state': m.state, 'opening': m.opening_balance or 0.0,
            'totals': self._month_totals(m),
            'fees': [{
                'id': f.id, 'student_id': f.student_id.id or False,
                'name': f.name, 'fees': f.fees or 0.0, 'paid': f.paid or 0.0,
                'paid_date': f.paid_date.strftime('%Y-%m-%d') if f.paid_date else '',
                'method': f.method or 'cash', 'note': f.note or '',
            } for f in m.fee_ids.sorted('name')],
            'entries': [{
                'id': e.id, 'etype': e.etype, 'name': e.name,
                'amount': e.amount or 0.0,
                'date': e.date.strftime('%Y-%m-%d') if e.date else '',
                'note': e.note or '',
            } for e in m.entry_ids],
            'available_students': [{'id': s.id, 'name': s.name,
                                    'fees': s.fees or 0.0} for s in avail],
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
        prev = Months.search([('ym', '<', ym)], order='ym desc', limit=1)
        if prev:
            open_bal = self._month_totals(prev)['closing']
        else:
            open_bal = self._num(opening) if opening not in (None, '') else 0.0
        month = Months.create({'ym': ym, 'opening_balance': open_bal})
        # ترحيل أسماء الشهر السابق (أو كل الطلاب النشطين لأول شهر)
        Fee = request.env['nursery.month.fee'].sudo()
        if prev:
            for f in prev.fee_ids:
                if f.student_id and not f.student_id.active:
                    continue  # طالب مؤرشف لا يترحّل
                Fee.create({'month_id': month.id,
                            'student_id': f.student_id.id or False,
                            'name': f.name, 'fees': f.fees or 0.0})
        else:
            for s in request.env['nursery.student'].sudo().search(
                    [('active', '=', True)], order='name'):
                Fee.create({'month_id': month.id, 'student_id': s.id,
                            'name': s.name, 'fees': s.fees or 0.0})
        return {'ok': True, 'ym': ym, 'carried': len(month.fee_ids),
                'opening': open_bal}

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
        m.write({'state': 'closed', 'closed_at': fields.Datetime.now()})
        return {'ok': True, 'closing': self._month_totals(m)['closing']}

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
        m.write({'state': 'open', 'closed_at': False})
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
        f = request.env['nursery.month.fee'].sudo().create({
            'month_id': m.id, 'student_id': s.id, 'name': s.name,
            'fees': s.fees or 0.0})
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
        if amt > 0:
            # سند دفع حقيقي — يظهر لولي الأمر وفي الداشبورد
            pvals = {'date': pd, 'amount': amt, 'method': meth, 'period': period}
            if f.payment_id:
                f.payment_id.write(pvals)
            elif f.student_id:
                pvals['student_id'] = f.student_id.id
                vals['payment_id'] = Pay.create(pvals).id
            if f.student_id:
                svals = {'paid': True, 'paid_at': pd, 'payment_method': meth}
                last_day = fields.Date.from_string(self._month_last_day(m.ym))
                if not f.student_id.paid_until or f.student_id.paid_until < last_day:
                    svals['paid_until'] = last_day
                f.student_id.write(svals)
        else:
            if f.payment_id:
                f.payment_id.unlink()
            vals['payment_id'] = False
        f.write(vals)
        return {'ok': True, 'totals': self._month_totals(m)}

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
        if etype not in ('income', 'expense', 'salary'):
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
        # مزامنة مع سجل المصروفات (الداشبورد): مصروف موجب / دخل سالب
        if etype in ('expense', 'income'):
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

    def _role_of(self, user):
        if user.has_group('base.group_system'):
            return ('أونر / أدمن', 't-owner')
        if user.has_group('nursery.group_nursery_manager'):
            return ('مديرة', 't-mgr')
        if user.has_group('nursery.group_nursery_teacher'):
            return ('مدرسة', 't-teach')
        students = request.env['nursery.student'].sudo().search_count(
            [('parent_user_id', '=', user.id)])
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
                [('parent_user_id', '=', u.id)])
            linked_txt = (' — مربوط بـ: ' + '، '.join(linked.mapped('name'))) if linked else ''
            opts = ''.join('<option value="%d">%s</option>' % (s.id, e(s.name))
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
                [('parent_user_id', '=', u.id)])
            out.append({
                'id': u.id, 'name': u.name, 'login': u.login,
                'role': label, 'cls': cls, 'is_owner': u.has_group('base.group_system'),
                'linked': '، '.join(linked.mapped('name')) if linked else '',
            })
        return {'ok': True, 'manager': mgr.name, 'users': out,
                'students': [{'id': s.id, 'name': s.name} for s in students]}

    @http.route('/api/roles/assign', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def api_roles_assign(self, mt=None, user_id=None, role=None, student_id=None, **kw):
        mgr = _manager_by_token(mt)
        if not mgr:
            return {'ok': False, 'error': 'unauthorized'}
        env = request.env
        try:
            user = env['res.users'].sudo().browse(int(user_id))
            assert user.exists()
        except Exception:
            return {'ok': False, 'error': 'مستخدم غير موجود'}
        if user.has_group('base.group_system'):
            return {'ok': False, 'error': 'مينفعش تعديل حساب الأونر'}
        ref = env.ref
        g_internal = ref('base.group_user')
        g_portal = ref('base.group_portal')
        g_teacher = ref('nursery.group_nursery_teacher')
        if role == 'teacher':
            user.write({'groups_id': [(3, g_portal.id), (4, g_internal.id), (4, g_teacher.id)]})
            self._ensure_employee(user)
            return {'ok': True, 'msg': '%s بقت مدرسة ✓' % user.name}
        if role == 'worker':
            user.write({'groups_id': [(3, g_portal.id), (4, g_internal.id), (3, g_teacher.id)]})
            self._ensure_employee(user)
            return {'ok': True, 'msg': '%s بقت عاملة ✓' % user.name}
        if role == 'parent':
            try:
                sid = int(student_id)
            except (TypeError, ValueError):
                return {'ok': False, 'error': 'اختاري الطفل الأول'}
            student = env['nursery.student'].sudo().browse(sid)
            if not student.exists():
                return {'ok': False, 'error': 'طفل غير موجود'}
            user.write({'groups_id': [(3, g_internal.id), (3, g_teacher.id), (4, g_portal.id)]})
            student.write({'parent_user_id': user.id})
            if not student.guardian_name:
                student.write({'guardian_name': user.name})
            return {'ok': True, 'msg': '%s بقى ولي أمر %s ✓' % (user.name, student.name)}
        return {'ok': False, 'error': 'دور غير صحيح'}

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
        # ماينفعش المديرة تعدل أدوار الأدمن/الأونر
        if user.has_group('base.group_system'):
            return request.redirect('/nursery-roles?done=' +
                                    'مينفعش تعديل حساب الأونر')

        ref = env.ref
        g_internal = ref('base.group_user')
        g_portal = ref('base.group_portal')
        g_teacher = ref('nursery.group_nursery_teacher')

        msg = 'تم'
        if role == 'teacher':
            user.write({'groups_id': [(3, g_portal.id), (4, g_internal.id),
                                      (4, g_teacher.id)]})
            self._ensure_employee(user)
            msg = '%s بقت مدرسة ✓' % user.name
        elif role == 'worker':
            user.write({'groups_id': [(3, g_portal.id), (4, g_internal.id),
                                      (3, g_teacher.id)]})
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
                user.write({'groups_id': [(3, g_internal.id),
                                          (3, g_teacher.id), (4, g_portal.id)]})
                student.write({'parent_user_id': user.id})
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
        students = env['nursery.student'].sudo().search(
            [('parent_user_id', '=', env.user.id), ('active', '=', True)])
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
