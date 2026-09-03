# -*- coding: utf-8 -*-
"""APIs الموظفين للموقع (بتوكن + CORS) — عشان صفحة الموظف تكون على
montessori-ksa.com مش أودو. حضور/انصراف (جيوفنس)، راتب، خصومات،
فصول، وشات (للمدرسين)، وتقييمات الطلاب."""
import json
import re
from datetime import datetime, timedelta

import pytz

from odoo import fields, http
from odoo.http import request

from .app import (_distance_m, _geo_params, _open_attendance, _wa_phone)

WEBSITE = 'https://montessori-ksa.com'
_TOKEN_RE = re.compile(r'^[0-9a-f]{32}$')

# معايير التقييم — نفس المفاتيح تُعرض للمعلمة ولولي الأمر
EVAL_CRITERIA = {
    'daily': [
        ('participation', 'المشاركة والنشاط'),
        ('behavior', 'السلوك مع أصدقائه'),
        ('focus', 'التركيز في العمل'),
        ('eating', 'تناول الطعام'),
        ('mood', 'المزاج العام'),
    ],
    'weekly': [
        ('language', 'اللغة والتواصل'),
        ('motor', 'المهارات الحركية'),
        ('social', 'المهارات الاجتماعية'),
        ('independence', 'الاستقلالية والاعتماد على النفس'),
        ('values', 'القرآن والقيم'),
    ],
}


def _riyadh_today():
    return datetime.now(pytz.timezone('Asia/Riyadh')).date()


def _eval_date(etype):
    """اليومي = تاريخ اليوم؛ الأسبوعي = أحد هذا الأسبوع (بداية الأسبوع)."""
    today = _riyadh_today()
    if etype == 'weekly':
        return today - timedelta(days=(today.weekday() + 1) % 7)
    return today


def _teacher_owns(u, emp, student):
    """هل الطالب في حيّز صلاحية هذا الموظف؟ (يمنع التفويض الأفقي بين المعلمات)
    - المديرة/الأونر: كل الطلاب.
    - المعلمة: طلاب فصولها فقط، أو طالب غير مسنَّد لأي فصل بعد
      (يُبقي التقييم/التواصل عاملاً قبل اكتمال توزيع الفصول — سبب الإزالة الأصلي)."""
    if not (student and student.exists() and student.active):
        return False
    if (u.has_group('nursery.group_nursery_manager')
            or u.has_group('base.group_system')):
        return True
    if not student.class_id:
        return True
    return bool(emp and student.class_id.teacher_id and
                student.class_id.teacher_id.id == emp.id)


def _teacher_can_eval(u, emp, student):
    """التقييم مقصور على طلاب المعلمة (أو غير المسنَّدين) — عبر _teacher_owns."""
    return _teacher_owns(u, emp, student)


def _staff_by_token(st):
    """يتحقق من توكن الموظف الصادر عند الدخول → يرجّع (user, employee)."""
    if not st or not _TOKEN_RE.match(st):
        return None, None
    u = request.env['res.users'].sudo().search(
        [('nursery_api_token', '=', st)], limit=1)
    if not u or not u._is_internal():
        return None, None
    emp = request.env['hr.employee'].sudo().search(
        [('user_id', '=', u.id)], limit=1)
    return u, emp


def _is_teacher_user(u):
    return (u.has_group('nursery.group_nursery_teacher')
            or u.has_group('nursery.group_nursery_manager')
            or u.has_group('base.group_system'))


def _fmt(env, u, dt):
    if not dt:
        return False
    return fields.Datetime.context_timestamp(u, dt).strftime('%H:%M')


class NurseryStaffApi(http.Controller):

    @http.route('/api/staff/state', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_state(self, st=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        env = request.env
        teacher = _is_teacher_user(u)
        base = {'name': u.name, 'is_teacher': teacher,
                'is_manager': u.has_group('nursery.group_nursery_manager')
                or u.has_group('base.group_system')}
        if not emp:
            return dict(base, no_employee=True)
        if emp.attendance_exempt:
            return dict(base, exempt=True)
        open_att = _open_attendance(env, emp)
        if open_att:
            return dict(base, checked_in=True, since=_fmt(env, u, open_att.check_in))
        last = env['hr.attendance'].sudo().search(
            [('employee_id', '=', emp.id)], limit=1, order='check_in desc')
        last_s = _fmt(env, u, last.check_out) if last and last.check_out else False
        if last_s:
            last_s = fields.Datetime.context_timestamp(
                u, last.check_out).strftime('%d/%m %H:%M')
        return dict(base, checked_in=False, last=last_s)

    @http.route('/api/staff/punch', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_punch(self, st=None, latitude=None, longitude=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not emp:
            return {'error': 'لا يوجد ملف موظف مرتبط بحسابك — يرجى التواصل مع الإدارة'}
        if emp.attendance_exempt:
            return {'error': 'أنت معفى من تسجيل الحضور والانصراف'}
        try:
            lat, lng = float(latitude), float(longitude)
        except (TypeError, ValueError):
            return {'error': 'يجب السماح بالوصول إلى موقعك'}
        env = request.env
        lat0, lng0, radius = _geo_params(env)
        dist = _distance_m(lat, lng, lat0, lng0)
        is_admin = u.has_group('base.group_system')
        open_att = _open_attendance(env, emp)
        action = 'out' if open_att else 'in'
        if action == 'in' and dist > radius and not is_admin:
            return {'error': 'أنت بعيد عن الحضانة بمسافة %d متر — يجب أن تكون '
                    'داخل الحضانة لتسجيل الحضور' % int(dist)}
        now = fields.Datetime.now()
        if action == 'in':
            env['hr.attendance'].sudo().create({
                'employee_id': emp.id, 'check_in': now,
                'in_latitude': lat, 'in_longitude': lng})
        else:
            open_att.sudo().write({
                'check_out': now, 'out_latitude': lat, 'out_longitude': lng})
        return {'action': action, 'time': _fmt(env, u, now), 'distance': int(dist)}

    @http.route('/api/staff/salary', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_salary(self, st=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        env = request.env
        if not emp:
            return {'rows': [], 'deductions_total': 0}
        term_labels = dict(
            env['nursery.salary']._fields['term']._description_selection(env))
        rows = env['nursery.salary'].sudo().search(
            [('employee_id', '=', emp.id)], order='id desc')
        if not rows:
            rows = env['nursery.salary'].sudo().search(
                [('teacher', '=', emp.name), ('employee_id', '=', False)], order='id desc')
        ded = env['nursery.deduction'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '=', 'confirmed')])
        return {'rows': [{
            'term': term_labels.get(r.term, r.term or ''), 'expected': r.expected,
            'actual': r.actual, 'paid_date': str(r.paid_date) if r.paid_date else False,
            'notes': r.notes or False} for r in rows],
            'deductions_total': sum(ded.mapped('amount'))}

    @http.route('/api/staff/deductions', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_deductions(self, st=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        env = request.env
        if not emp:
            return {'rows': [], 'total': 0, 'total_days': 0}
        rows = env['nursery.deduction'].sudo().search(
            [('employee_id', '=', emp.id), ('state', '!=', 'cancelled')],
            order='date desc', limit=100)
        confirmed = rows.filtered(lambda r: r.state == 'confirmed')
        return {'rows': [{
            'date': str(r.date), 'dtype': r.dtype, 'minutes_late': r.minutes_late,
            'days': r.days, 'amount': r.amount, 'state': r.state,
            'note': r.note or False} for r in rows],
            'total': sum(confirmed.mapped('amount')),
            'total_days': sum(confirmed.mapped('days'))}

    @http.route('/api/staff/classes', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_classes(self, st=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not _is_teacher_user(u):
            return {'classes': [], 'error': 'غير مصرح'}
        env = request.env
        is_admin = u.has_group('base.group_system') or u.has_group('nursery.group_nursery_manager')
        domain = [] if is_admin else ['|', ('teacher_id', '=', emp.id if emp else 0),
                                      ('teacher_id', '=', False)]
        classes = env['nursery.class'].sudo().search(domain)
        return {'classes': [{
            'name': c.name, 'teacher': c.teacher_id.name or False,
            'students': [{'id': s.id, 'name': s.name} for s in c.student_ids]}
            for c in classes]}

    @http.route('/api/staff/students', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_students(self, st=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not _is_teacher_user(u):
            return {'students': [], 'error': 'غير مصرح'}
        Stu = request.env['nursery.student'].sudo()
        if (u.has_group('nursery.group_nursery_manager')
                or u.has_group('base.group_system')):
            students = Stu.search([('active', '=', True)], order='name')
        else:
            # المعلمة: طلاب فصولها + غير المسنَّدين فقط (لا هواتف بقية الطلاب)
            my_cls = request.env['nursery.class'].sudo().search(
                [('teacher_id', '=', emp.id if emp else 0)])
            students = Stu.search(
                ['&', ('active', '=', True),
                 '|', ('class_id', 'in', my_cls.ids), ('class_id', '=', False)],
                order='name')
        return {'students': [{
            'id': s.id, 'name': s.name, 'guardian': s.guardian_name or False,
            'phone': s.guardian_phone or False, 'wa': _wa_phone(s.guardian_phone)}
            for s in students]}

    @http.route('/api/staff/messages', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_messages(self, st=None, student_id=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not _is_teacher_user(u):
            return {'student': '', 'messages': [], 'error': 'غير مصرح'}
        env = request.env
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            return {'student': '', 'messages': []}
        student = env['nursery.student'].sudo().browse(student_id)
        if not student.exists():
            return {'student': '', 'messages': []}
        if not _teacher_owns(u, emp, student):
            return {'student': '', 'messages': [], 'error': 'هذا الطالب ليس في فصولك'}
        msgs = env['nursery.message'].sudo().search(
            [('student_id', '=', student.id)], order='create_date desc', limit=200)
        msgs = msgs.sorted('create_date')
        state_label = {'pending': '⏳ بانتظار موافقة المديرة',
                       'rejected': '🚫 رفضتها المديرة', 'approved': ''}
        return {'student': student.name, 'messages': [{
            'body': m.body,
            'author': 'ولي الأمر 👨‍👩‍👧' if m.is_parent else m.author_id.name,
            'mine': (not m.is_parent) and m.author_id.id == u.id,
            'status': state_label.get(m.state, ''),
            'time': fields.Datetime.context_timestamp(u, m.create_date).strftime('%d/%m %H:%M')}
            for m in msgs]}

    # ==================== تقييم الطلاب (يومي/أسبوعي) ====================
    @http.route('/api/staff/eval/get', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_eval_get(self, st=None, student_id=None, etype=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not _is_teacher_user(u):
            return {'ok': False, 'error': 'غير مصرح'}
        etype = etype if etype in ('daily', 'weekly') else 'daily'
        try:
            student = request.env['nursery.student'].sudo().browse(int(student_id))
            assert student.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        if not _teacher_can_eval(u, emp, student):
            return {'ok': False, 'error': 'هذا الطالب ليس في فصولك'}
        d = _eval_date(etype)
        Ev = request.env['nursery.evaluation'].sudo()
        ev = Ev.search([('student_id', '=', student.id),
                        ('etype', '=', etype), ('date', '=', d)], limit=1)
        try:
            scores = json.loads(ev.scores or '{}') if ev else {}
        except ValueError:
            scores = {}
        recent = Ev.search([('student_id', '=', student.id),
                            ('etype', '=', etype)], limit=5)
        return {
            'ok': True, 'student': student.name, 'etype': etype,
            'date': d.strftime('%Y-%m-%d'),
            'criteria': [{'k': k, 'label': lbl} for k, lbl in EVAL_CRITERIA[etype]],
            'scores': scores, 'note': (ev.note if ev else '') or '',
            'exists': bool(ev),
            'recent': [{'date': r.date.strftime('%Y-%m-%d'),
                        'note': (r.note or '')[:80]} for r in recent],
        }

    @http.route('/api/staff/eval/save', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_eval_save(self, st=None, student_id=None, etype=None,
                        scores=None, note=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not _is_teacher_user(u):
            return {'ok': False, 'error': 'غير مصرح'}
        etype = etype if etype in ('daily', 'weekly') else 'daily'
        try:
            student = request.env['nursery.student'].sudo().browse(int(student_id))
            assert student.exists()
        except Exception:
            return {'ok': False, 'error': 'طالب غير موجود'}
        if not _teacher_can_eval(u, emp, student):
            return {'ok': False, 'error': 'هذا الطالب ليس في فصولك'}
        # نظّف الدرجات: مفاتيح معتمدة فقط، قيم 1..5
        clean = {}
        allowed = dict(EVAL_CRITERIA[etype])
        for k, v in (scores or {}).items():
            if k in allowed:
                try:
                    v = int(v)
                except (TypeError, ValueError):
                    continue
                if 1 <= v <= 5:
                    clean[k] = v
        if not clean:
            return {'ok': False, 'error': 'قيّمي معياراً واحداً على الأقل'}
        note = (note or '').strip().replace('<', '').replace('>', '')[:1000]
        d = _eval_date(etype)
        Ev = request.env['nursery.evaluation'].sudo()
        ev = Ev.search([('student_id', '=', student.id),
                        ('etype', '=', etype), ('date', '=', d)], limit=1)
        vals = {'scores': json.dumps(clean), 'note': note,
                'teacher_id': emp.id if emp else False}
        if ev:
            ev.write(vals)
        else:
            vals.update({'student_id': student.id, 'etype': etype, 'date': d})
            Ev.create(vals)
        return {'ok': True, 'date': d.strftime('%Y-%m-%d')}

    @http.route('/api/staff/messages/post', type='json', auth='public',
                methods=['POST'], csrf=False, cors=WEBSITE)
    def staff_messages_post(self, st=None, student_id=None, body=None, **kw):
        u, emp = _staff_by_token(st)
        if not u:
            return {'error': 'unauthorized'}
        if not _is_teacher_user(u):
            return {'ok': False, 'error': 'غير مصرح'}
        env = request.env
        body = (body or '').strip()
        try:
            student_id = int(student_id)
        except (TypeError, ValueError):
            return {'ok': False}
        student = env['nursery.student'].sudo().browse(student_id)
        if not body or not student.exists():
            return {'ok': False}
        if not _teacher_owns(u, emp, student):
            return {'ok': False, 'error': 'هذا الطالب ليس في فصولك'}
        is_mgr = (u.has_group('nursery.group_nursery_manager')
                  or u.has_group('base.group_system'))
        trusted = bool(emp and emp.messages_trusted)
        state = 'approved' if (is_mgr or trusted) else 'pending'
        env['nursery.message'].sudo().create({
            'student_id': student_id, 'author_id': u.id,
            'body': body[:2000], 'state': state})
        return {'ok': True, 'pending': state == 'pending'}
