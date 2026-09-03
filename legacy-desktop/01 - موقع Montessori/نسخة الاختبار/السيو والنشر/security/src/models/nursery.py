# -*- coding: utf-8 -*-
import secrets
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import ValidationError

NURSERY_TZ = 'Asia/Riyadh'


def _new_token():
    return secrets.token_hex(16)

TERMS = [
    ('term_2026', 'ترم 2026'),
    ('summer_2026', 'صيف 2026'),
    ('term_2027', 'ترم 2027'),
]

PAYMENT_METHODS = [
    ('cash', 'كاش'),
    ('transfer', 'تحويل بنكي'),
    ('card', 'بطاقة'),
    ('other', 'أخرى'),
]


class ResUsersNursery(models.Model):
    _inherit = 'res.users'

    nursery_api_token = fields.Char('توكن API للموقع', copy=False, index=True)

    def _ensure_api_token(self):
        self.ensure_one()
        if not self.nursery_api_token:
            self.sudo().nursery_api_token = _new_token()
        return self.nursery_api_token


class NurseryLinkRequest(models.Model):
    _name = 'nursery.link.request'
    _description = 'طلب ربط ولي أمر بطفله (من الموقع)'
    _order = 'create_date desc'

    parent_name = fields.Char('اسم ولي الأمر', required=True)
    parent_email = fields.Char('إيميل ولي الأمر', required=True, index=True)
    parent_phone = fields.Char('تليفون')
    child_name = fields.Char('اسم الطفل (كما كتبه ولي الأمر)', required=True)
    matched_student_id = fields.Many2one(
        'nursery.student', string='الطفل المطابَق',
        help='لو النظام لقى طفل بنفس الاسم')
    is_enrolled = fields.Boolean('الطفل من طلاب الحضانة', compute='_compute_enrolled', store=True)
    state = fields.Selection([
        ('pending', 'بانتظار المراجعة'),
        ('linked', 'تم الربط'),
        ('rejected', 'مرفوض'),
    ], default='pending', required=True, index=True)
    note = fields.Char('ملاحظة')
    nudged = fields.Boolean('بلّغ ولي الأمر', default=False)
    nudged_at = fields.Datetime('وقت التبليغ')

    @api.depends('matched_student_id')
    def _compute_enrolled(self):
        for rec in self:
            rec.is_enrolled = bool(rec.matched_student_id)

    @api.model
    def create_from_site(self, parent_name, parent_email, parent_phone, child_name):
        """يُستدعى من الـ API عند تسجيل ولي الأمر — يطابق الطفل تلقائياً."""
        def _clean(v):
            # شيل أي أقواس HTML (دفاع ضد XSS المخزَّن)
            return (v or '').replace('<', '').replace('>', '').strip()
        parent_name = _clean(parent_name)
        child_name = _clean(child_name)
        student = False
        cn = child_name.strip()
        # امنع wildcards الـ LIKE (% و _) عشان ماتبقاش مطابقة شاملة
        if cn and '%' not in cn and '_' not in cn:
            student = self.env['nursery.student'].sudo().search(
                [('name', '=ilike', cn), ('active', '=', True)], limit=1)
        req = self.sudo().create({
            'parent_name': (parent_name or '').strip()[:120] or '—',
            'parent_email': (parent_email or '').strip().lower()[:120],
            'parent_phone': (parent_phone or '').strip()[:40],
            'child_name': cn[:120],
            'matched_student_id': student.id if student else False,
        })
        return req

    def action_link(self):
        """المديرة تعتمد الطلب: تعلّم الطلب كمقبول.
        الربط الفعلي (parent_user_id) بيحصل بس لما ولي الأمر يسجّل دخول
        بجوجل بنفس الإيميل (في portal_home) — إثبات ملكية الإيميل. عشان
        كده مابنكتبش parent_user_id هنا بناءً على إيميل مش متحقّق منه."""
        for rec in self:
            if not rec.matched_student_id:
                raise ValidationError('اختاري الطفل الأول قبل الربط!')
            if not rec.matched_student_id.guardian_name:
                rec.matched_student_id.sudo().guardian_name = rec.parent_name
            if not rec.matched_student_id.guardian_phone and rec.parent_phone:
                rec.matched_student_id.sudo().guardian_phone = rec.parent_phone
            rec.state = 'linked'


class HrEmployeeNursery(models.Model):
    _inherit = 'hr.employee'

    attendance_exempt = fields.Boolean(
        'معفي من تسجيل الحضور', default=False,
        help='الموظف المعفي لا يسجل حضور/انصراف ولا تُحسب عليه خصومات غياب أو تأخير')
    messages_trusted = fields.Boolean(
        'رسائلها لأولياء الأمور تعدي مباشرة', default=False,
        help='لو مفعّلة، رسائل هذه المعلمة تصل لولي الأمر فوراً بدون موافقة المديرة')


class NurseryClass(models.Model):
    _name = 'nursery.class'
    _description = 'الفصل الدراسي'
    _order = 'name'

    name = fields.Char('اسم الفصل', required=True)
    teacher_id = fields.Many2one('hr.employee', string='المعلمة المسؤولة')
    capacity = fields.Integer('السعة القصوى', default=15)
    term = fields.Selection(TERMS, string='الترم')
    student_ids = fields.One2many('nursery.student', 'class_id', string='الطلاب')
    student_count = fields.Integer('عدد الطلاب', compute='_compute_student_count')
    note = fields.Text('ملاحظات')
    active = fields.Boolean(default=True)

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)


class NurseryStudent(models.Model):
    _name = 'nursery.student'
    _description = 'الطالب'
    _inherit = ['mail.thread']
    _order = 'serial, name'

    name = fields.Char('اسم الطالب', required=True, tracking=True)
    serial = fields.Integer('الرقم التسلسلي')
    term = fields.Selection(TERMS, string='الترم', default='term_2026', tracking=True)
    class_id = fields.Many2one('nursery.class', string='الفصل', tracking=True)
    joining_date = fields.Date('تاريخ الالتحاق')

    guardian_name = fields.Char('اسم ولي الأمر')
    guardian_phone = fields.Char('تليفون ولي الأمر')
    guardian_phone2 = fields.Char('تليفون إضافي')
    emergency_note = fields.Char('ملاحظات طبية / طوارئ')

    fees = fields.Float('الرسوم الشهرية', tracking=True)
    books_fees = fields.Float('رسوم الكتب')
    paid = fields.Boolean('مدفوع', tracking=True)
    paid_at = fields.Date('تاريخ الدفع')
    paid_until = fields.Date('مدفوع حتى')
    payment_method = fields.Selection(PAYMENT_METHODS, string='طريقة الدفع')

    payment_ids = fields.One2many('nursery.fee.payment', 'student_id', string='المدفوعات')
    attendance_ids = fields.One2many('nursery.attendance', 'student_id', string='الحضور')
    book_move_ids = fields.One2many('nursery.book.move', 'student_id', string='الكتب')
    total_paid = fields.Float('إجمالي المدفوع', compute='_compute_total_paid')

    remark = fields.Text('ملاحظات')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='الشركة',
        default=lambda self: self.env.company)
    portal_token = fields.Char('رمز بوابة ولي الأمر', copy=False, index=True)
    portal_url = fields.Char('لينك ولي الأمر', compute='_compute_portal_url')
    parent_user_id = fields.Many2one(
        'res.users', string='حساب ولي الأمر (جوجل)', copy=False,
        help='لو ولي الأمر سجل دخول بجوجل، اربطه هنا — يدخل على /my-child ويلاقي ابنه')

    _sql_constraints = [
        ('portal_token_uniq', 'unique(portal_token)',
         'رمز بوابة ولي الأمر يجب أن يكون فريداً!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        # كل طالب لازم ياخد رمز فريد بنفسه وقت الإنشاء —
        # عمداً مش default= عشان ترقية الموديول (-u) بتحط نفس القيمة
        # لكل الصفوف القديمة دفعة واحدة (SQL backfill واحد)
        for vals in vals_list:
            vals.setdefault('portal_token', _new_token())
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # قاعدة: حساب ولي أمر واحد = طفل واحد فقط.
        # عند ربط ولي أمر بطفل، يُلغى ربطه بأي طفل آخر تلقائياً.
        uid = vals.get('parent_user_id')
        if uid:
            others = self.sudo().search([('parent_user_id', '=', uid),
                                         ('id', 'not in', self.ids)])
            if others:
                others.write({'parent_user_id': False})
        return res

    @api.depends('portal_token')
    def _compute_portal_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', 'https://odoo.montessori-ksa.com')
        for rec in self:
            rec.portal_url = '%s/parent/%s' % (base, rec.portal_token) if rec.portal_token else False

    def action_regenerate_token(self):
        for rec in self:
            rec.portal_token = _new_token()

    @api.model
    def cron_fee_reminders(self):
        """تذكير سداد الرسوم في شات ولي الأمر:
        قبل انتهاء المدفوع بـ3 أيام، ثم رسالة كل يومين طالما لم يُسدد."""
        tz = pytz.timezone(NURSERY_TZ)
        now_utc = datetime.utcnow()
        today = datetime.now(pytz.utc).astimezone(tz).date()
        Msg = self.env['nursery.message'].sudo()
        admin = self.env.ref('base.user_admin')
        for s in self.search([('active', '=', True), ('paid_until', '!=', False)]):
            days_left = (s.paid_until - today).days
            if days_left > 3:
                continue
            # رسالة واحدة كحد أقصى كل يومين لنفس فترة الاستحقاق
            marker_prefix = '⏰[%s' % s.paid_until
            recent = Msg.search([('student_id', '=', s.id),
                                 ('body', 'like', marker_prefix)],
                                order='create_date desc', limit=1)
            if recent and (now_utc - recent.create_date).days < 2:
                continue
            if days_left >= 0:
                text = ('تذكير ودّي 💜: اشتراك %s المدفوع ينتهي يوم %s — '
                        'برجاء تجديد الرسوم (%s ر.س) في الموعد.'
                        % (s.name, s.paid_until, int(s.fees)))
            else:
                text = ('تنبيه: رسوم %s مستحقة منذ %s يوم — '
                        'برجاء التواصل مع الإدارة لتجديد الاشتراك (%s ر.س).'
                        % (s.name, abs(days_left), int(s.fees)))
            marker = '⏰[%s:%s]' % (s.paid_until, today)
            Msg.create({
                'student_id': s.id,
                'author_id': admin.id,
                'is_parent': False,
                'body': '%s\n%s' % (text, marker),
            })

    @api.depends('payment_ids.amount')
    def _compute_total_paid(self):
        for rec in self:
            rec.total_paid = sum(rec.payment_ids.mapped('amount'))


class NurseryFeePayment(models.Model):
    _name = 'nursery.fee.payment'
    _description = 'دفعة رسوم'
    _order = 'date desc, id desc'

    student_id = fields.Many2one(
        'nursery.student', string='الطالب', required=True, ondelete='cascade')
    date = fields.Date('التاريخ', default=fields.Date.context_today, required=True)
    amount = fields.Float('المبلغ', required=True)
    method = fields.Selection(PAYMENT_METHODS, string='طريقة الدفع', default='cash')
    period = fields.Char('عن فترة')  # e.g. "يونيو 2026"
    note = fields.Char('ملاحظة')


class NurseryAttendance(models.Model):
    _name = 'nursery.attendance'
    _description = 'الحضور اليومي'
    _order = 'date desc, id desc'

    student_id = fields.Many2one(
        'nursery.student', string='الطالب', required=True, ondelete='cascade')
    date = fields.Date('التاريخ', default=fields.Date.context_today, required=True)
    status = fields.Selection([
        ('present', 'حاضر'),
        ('absent', 'غائب'),
        ('late', 'متأخر'),
        ('sick', 'مريض'),
        ('leave', 'إجازة'),
    ], string='الحالة', default='present', required=True)
    arrival = fields.Datetime('وقت الوصول')
    departure = fields.Datetime('وقت الخروج')
    by_parent = fields.Boolean('سجّله ولي الأمر', default=False)
    note = fields.Char('ملاحظة')

    _sql_constraints = [
        ('student_date_uniq', 'unique(student_id, date)',
         'يوجد تسجيل حضور لهذا الطالب في نفس اليوم بالفعل!'),
    ]


class NurseryBook(models.Model):
    _name = 'nursery.book'
    _description = 'كتاب / منهج'
    _order = 'name'

    name = fields.Char('اسم الكتاب', required=True)
    code = fields.Char('الكود')
    level = fields.Char('المستوى / السن')
    price = fields.Float('سعر البيع للطالب')
    cost = fields.Float('تكلفة الشراء')
    move_ids = fields.One2many('nursery.book.move', 'book_id', string='الحركات')
    received_qty = fields.Integer('إجمالي الوارد', compute='_compute_quantities')
    issued_qty = fields.Integer('المُسلَّم للطلاب', compute='_compute_quantities')
    stock_qty = fields.Integer('المتبقي في المخزن', compute='_compute_quantities')
    note = fields.Text('ملاحظات')
    active = fields.Boolean(default=True)

    @api.depends('move_ids.qty', 'move_ids.move_type')
    def _compute_quantities(self):
        for rec in self:
            rec_in = sum(m.qty for m in rec.move_ids if m.move_type == 'in')
            rec_out = sum(m.qty for m in rec.move_ids if m.move_type == 'out')
            rec_ret = sum(m.qty for m in rec.move_ids if m.move_type == 'return')
            rec.received_qty = rec_in
            rec.issued_qty = rec_out - rec_ret
            rec.stock_qty = rec_in + rec_ret - rec_out


class NurseryBookMove(models.Model):
    _name = 'nursery.book.move'
    _description = 'حركة كتاب (وارد / تسليم / مرتجع)'
    _order = 'date desc, id desc'

    book_id = fields.Many2one('nursery.book', string='الكتاب', required=True, ondelete='cascade')
    move_type = fields.Selection([
        ('in', 'وارد للحضانة'),
        ('out', 'تسليم لطالب'),
        ('return', 'مرتجع من طالب'),
    ], string='نوع الحركة', required=True, default='out')
    qty = fields.Integer('الكمية', required=True, default=1)
    date = fields.Date('التاريخ', default=fields.Date.context_today, required=True)
    student_id = fields.Many2one('nursery.student', string='الطالب', ondelete='set null')
    paid = fields.Boolean('تم تحصيل ثمنه')
    note = fields.Char('ملاحظة')

    _sql_constraints = [
        ('qty_positive', 'CHECK(qty > 0)', 'الكمية يجب أن تكون أكبر من صفر!'),
    ]

    @api.constrains('move_type', 'student_id')
    def _check_student_required(self):
        for rec in self:
            if rec.move_type in ('out', 'return') and not rec.student_id:
                raise ValidationError('لازم تختار الطالب في حركة التسليم أو المرتجع!')


class NurserySalary(models.Model):
    _name = 'nursery.salary'
    _description = 'رواتب الموظفين'
    _order = 'id desc'

    teacher = fields.Char('الموظف / المعلمة', required=True)
    employee_id = fields.Many2one('hr.employee', string='ملف الموظف')
    expected = fields.Float('الراتب المستحق')
    actual = fields.Float('المدفوع فعلياً')
    paid_date = fields.Date('تاريخ الدفع')
    term = fields.Selection(TERMS, string='الترم')
    notes = fields.Char('ملاحظات')


class NurseryHoliday(models.Model):
    _name = 'nursery.holiday'
    _description = 'إجازات الحضانة'
    _order = 'date_from'

    name = fields.Char('اسم الإجازة', required=True)
    date_from = fields.Date('من', required=True)
    date_to = fields.Date('إلى', required=True)
    note = fields.Char('ملاحظة')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_to < rec.date_from:
                raise ValidationError('تاريخ النهاية قبل تاريخ البداية!')


class NurseryAlbum(models.Model):
    _name = 'nursery.album'
    _description = 'ألبوم صور (من جوجل درايف)'
    _order = 'sequence, id desc'

    name = fields.Char('اسم الألبوم / الحفلة', required=True)
    drive_id = fields.Char('Drive Folder ID', index=True)
    cover_file_id = fields.Char('Drive cover file ID')
    sequence = fields.Integer(default=10)
    photo_ids = fields.One2many('nursery.photo', 'album_id', string='الصور')
    photo_count = fields.Integer(compute='_compute_photo_count')
    active = fields.Boolean(default=True)
    parent_visible = fields.Boolean('يظهر للأهالي', default=True)
    site_visible = fields.Boolean('يظهر في الصفحة الرئيسية', default=True)

    @api.depends('photo_ids')
    def _compute_photo_count(self):
        for rec in self:
            rec.photo_count = len(rec.photo_ids)


class NurseryPhoto(models.Model):
    _name = 'nursery.photo'
    _description = 'صورة (مرجع درايف فقط — بدون تخزين)'
    _order = 'name'

    album_id = fields.Many2one('nursery.album', string='الألبوم', required=True, ondelete='cascade')
    name = fields.Char('اسم الملف')
    drive_id = fields.Char('Drive File ID', required=True, index=True)
    thumb_url = fields.Char('رابط الصورة', compute='_compute_thumb_url')

    @api.depends('drive_id')
    def _compute_thumb_url(self):
        for rec in self:
            rec.thumb_url = ('https://drive.google.com/thumbnail?id=%s&sz=w600'
                             % rec.drive_id) if rec.drive_id else False


class NurseryAlbumGallery(models.Model):
    _inherit = 'nursery.album'

    def action_open_gallery(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': '/nursery-gallery/%d' % self.id,
            'target': 'new',
        }


class NurseryMessage(models.Model):
    _name = 'nursery.message'
    _description = 'رسالة تواصل مع ولي الأمر'
    _order = 'create_date asc'

    student_id = fields.Many2one(
        'nursery.student', string='الطالب', required=True, ondelete='cascade')
    author_id = fields.Many2one(
        'res.users', string='الكاتب', required=True,
        default=lambda self: self.env.user)
    is_parent = fields.Boolean('من ولي الأمر', default=False)
    body = fields.Text('الرسالة', required=True)
    state = fields.Selection([
        ('pending', 'بانتظار موافقة المديرة'),
        ('approved', 'معتمدة'),
        ('rejected', 'مرفوضة'),
    ], string='الحالة', default='approved', required=True, index=True)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})


class NurseryDeduction(models.Model):
    _name = 'nursery.deduction'
    _description = 'خصومات الغياب والتأخير'
    _order = 'date desc, id desc'

    # لائحة الحضانة: غياب بدون إبلاغ = يومين، غياب بإذن الإدارة = يوم (3 مرات/سنة كحد أقصى)
    TYPE_DAYS = {'absence': 2.0, 'absence_auth': 1.0}
    AUTH_ABSENCE_YEARLY_LIMIT = 3

    employee_id = fields.Many2one(
        'hr.employee', string='الموظفة', required=True, ondelete='cascade')
    date = fields.Date('التاريخ', required=True, default=fields.Date.context_today)
    dtype = fields.Selection([
        ('absence', 'غياب بدون إبلاغ'),
        ('absence_auth', 'غياب بإذن الإدارة'),
        ('late', 'تأخير'),
        ('other', 'أخرى'),
    ], string='النوع', required=True, default='late')
    minutes_late = fields.Integer('دقائق التأخير')
    days = fields.Float('الخصم (أيام)')
    amount = fields.Float('قيمة الخصم (ر.س)')
    state = fields.Selection([
        ('draft', 'قيد المراجعة'),
        ('confirmed', 'معتمد'),
        ('cancelled', 'ملغي'),
    ], string='الحالة', default='draft', required=True)
    note = fields.Char('ملاحظة')

    _sql_constraints = [
        ('emp_date_type_uniq', 'unique(employee_id, date, dtype)',
         'يوجد خصم من نفس النوع لنفس الموظفة في نفس اليوم بالفعل!'),
    ]

    @api.onchange('dtype')
    def _onchange_dtype(self):
        if self.dtype in self.TYPE_DAYS:
            self.days = self.TYPE_DAYS[self.dtype]
            self.amount = self.days * self._day_value(self.employee_id)

    @api.constrains('dtype', 'state', 'employee_id', 'date')
    def _check_auth_absence_quota(self):
        for rec in self:
            if rec.dtype == 'absence_auth' and rec.state == 'confirmed' and rec.date:
                year_start = rec.date.replace(month=1, day=1)
                year_end = rec.date.replace(month=12, day=31)
                others = self.search_count([
                    ('id', '!=', rec.id),
                    ('employee_id', '=', rec.employee_id.id),
                    ('dtype', '=', 'absence_auth'),
                    ('state', '=', 'confirmed'),
                    ('date', '>=', year_start), ('date', '<=', year_end),
                ])
                if others >= self.AUTH_ABSENCE_YEARLY_LIMIT:
                    raise ValidationError(
                        'الموظفة %s استنفدت الـ%d مرات غياب بإذن الإدارة المسموحة هذه السنة!'
                        % (rec.employee_id.name, self.AUTH_ABSENCE_YEARLY_LIMIT))

    def _day_value(self, employee):
        """قيمة اليوم = آخر راتب مستحق ÷ 30"""
        if not employee:
            return 0.0
        sal = self.env['nursery.salary'].sudo().search(
            [('employee_id', '=', employee.id)], order='id desc', limit=1)
        return (sal.expected / 30.0) if sal and sal.expected else 0.0

    @staticmethod
    def late_days_for(minutes):
        """درجات خصم التأخير حسب اللائحة (تقبل دقائق بكسور للدقة بالثانية):
        أقل من 10 دقائق = مسموح، 10 لأقل من 30 = ربع يوم،
        30 بالظبط = نص يوم، أكثر من 30 = يوم كامل"""
        if minutes < 10:
            return 0.0
        if minutes > 30:
            return 1.0
        if minutes >= 30:
            return 0.5
        return 0.25

    @api.model
    def cron_generate_daily(self):
        """يشتغل يومياً: يسجل خصم غياب لمن لم يسجل حضور اليوم،
        وخصم تأخير لمن حضر بعد موعد بداية الدوام + فترة السماح.
        الجمعة والسبت إجازة."""
        icp = self.env['ir.config_parameter'].sudo()

        def _num(key, default, conv=float):
            try:
                return conv(icp.get_param(key, default))
            except (TypeError, ValueError):
                return conv(default)

        grace_min = _num('nursery.late_grace_min', '10', int)

        tz = pytz.timezone(NURSERY_TZ)
        now_local = datetime.now(pytz.utc).astimezone(tz)
        today = now_local.date()
        if now_local.weekday() in (4, 5):  # الجمعة والسبت
            return

        start_s = icp.get_param('nursery.work_start', '08:00') or '08:00'
        try:
            h, m = (int(x) for x in start_s.split(':'))
            work_time = time(h, m)
        except ValueError:
            work_time = time(8, 0)
        work_start_local = tz.localize(datetime.combine(today, work_time))
        deadline_local = work_start_local + timedelta(minutes=grace_min)
        if now_local <= deadline_local:
            # الكرون اشتغل بدري قبل نهاية فترة السماح — استنى التشغيلة الجاية
            return

        day_start_utc = tz.localize(
            datetime.combine(today, time(0, 0))).astimezone(pytz.utc).replace(tzinfo=None)

        employees = self.env['hr.employee'].sudo().search(
            [('user_id', '!=', False), ('attendance_exempt', '=', False)])
        Att = self.env['hr.attendance'].sudo()
        for emp in employees:
            first = Att.search(
                [('employee_id', '=', emp.id), ('check_in', '>=', day_start_utc)],
                limit=1, order='check_in asc')
            day_value = self._day_value(emp)
            if not first:
                # غياب بدون إبلاغ = يومين — لو كان بإذن الإدارة، المدير يغيّر النوع
                existing = self.search([
                    ('employee_id', '=', emp.id), ('date', '=', today),
                    ('dtype', 'in', ('absence', 'absence_auth'))])
                if not existing:
                    days = self.TYPE_DAYS['absence']
                    self.create({
                        'employee_id': emp.id, 'date': today, 'dtype': 'absence',
                        'days': days, 'amount': days * day_value,
                        'note': 'تلقائي: لم يُسجَّل حضور — لو الغياب بإذن الإدارة غيّري النوع',
                    })
                continue
            check_in_local = pytz.utc.localize(first.check_in).astimezone(tz)
            minutes_f = (check_in_local - work_start_local).total_seconds() / 60.0
            days = self.late_days_for(minutes_f)
            if days:
                # لا تكرر الخصم لو اليوم عليه بالفعل تأخير أو غياب (من تشغيلة سابقة)
                existing = self.search([
                    ('employee_id', '=', emp.id), ('date', '=', today),
                    ('dtype', 'in', ('late', 'absence', 'absence_auth'))])
                if not existing:
                    self.create({
                        'employee_id': emp.id, 'date': today, 'dtype': 'late',
                        'minutes_late': int(minutes_f), 'days': days,
                        'amount': days * day_value,
                        'note': 'تلقائي: حضور %s' % check_in_local.strftime('%H:%M'),
                    })


class NurseryEvaluation(models.Model):
    """تقييم المعلمة للطالب — يومي أو أسبوعي، يظهر في صفحة ولي الأمر."""
    _name = 'nursery.evaluation'
    _description = 'تقييم الطالب'
    _order = 'date desc, id desc'

    student_id = fields.Many2one('nursery.student', string='الطالب',
                                 required=True, ondelete='cascade', index=True)
    etype = fields.Selection([('daily', 'يومي'), ('weekly', 'أسبوعي')],
                             string='النوع', default='daily', required=True)
    date = fields.Date('التاريخ', required=True,
                       default=fields.Date.context_today)
    scores = fields.Text('الدرجات (JSON)', default='{}')
    note = fields.Text('ملاحظة المعلمة')
    teacher_id = fields.Many2one('hr.employee', string='المعلمة')

    _sql_constraints = [
        ('uniq_student_type_date', 'unique(student_id, etype, date)',
         'يوجد تقييم مسجّل بالفعل لنفس اليوم/الأسبوع — عدّلي التقييم الموجود.'),
    ]


class NurseryExpense(models.Model):
    _name = 'nursery.expense'
    _description = 'المصروفات'
    _order = 'id desc'

    date = fields.Date('التاريخ')
    value = fields.Float('القيمة', required=True, help='قيمة موجبة = مصروف، قيمة سالبة = دخل إضافي')
    term = fields.Selection(TERMS, string='الترم')
    note = fields.Char('البيان')


# ==================== النظام المحاسبي الشهري ====================
class NurseryMonth(models.Model):
    """دفتر شهري: رصيد افتتاحي + رسوم الطلبة + دخل/مصروفات/رواتب.
    الشهر المقفول لا يقبل أي تعديل."""
    _name = 'nursery.month'
    _description = 'الشهر المحاسبي'
    _order = 'ym desc'

    ym = fields.Char('الشهر (YYYY-MM)', required=True, index=True)
    state = fields.Selection([('open', 'مفتوح'), ('closed', 'مقفول')],
                             default='open', required=True)
    opening_balance = fields.Float('الرصيد الافتتاحي')
    closed_at = fields.Datetime('وقت القفل')
    fee_ids = fields.One2many('nursery.month.fee', 'month_id', string='رسوم الطلبة')
    entry_ids = fields.One2many('nursery.month.entry', 'month_id', string='القيود')

    _sql_constraints = [
        ('uniq_ym', 'unique(ym)', 'هذا الشهر مفتوح بالفعل!'),
    ]


class NurseryMonthFee(models.Model):
    """سطر طالب في كشف الشهر — الاسم يترحّل من الشهر السابق."""
    _name = 'nursery.month.fee'
    _description = 'رسوم طالب في شهر'
    _order = 'name'

    month_id = fields.Many2one('nursery.month', required=True,
                               ondelete='cascade', index=True)
    student_id = fields.Many2one('nursery.student', string='الطالب',
                                 ondelete='set null', index=True)
    name = fields.Char('اسم الطالب', required=True)
    fees = fields.Float('الرسوم المستحقة')
    paid = fields.Float('المدفوع')
    paid_date = fields.Date('تاريخ الدفع')
    method = fields.Selection(PAYMENT_METHODS, string='طريقة الدفع')
    note = fields.Char('ملاحظة')
    payment_id = fields.Many2one('nursery.fee.payment', string='سند الدفع',
                                 ondelete='set null')


class NurseryMonthEntry(models.Model):
    """قيد شهري: دخل إضافي / مصروف / راتب."""
    _name = 'nursery.month.entry'
    _description = 'قيد شهري'
    _order = 'date, id'

    month_id = fields.Many2one('nursery.month', required=True,
                               ondelete='cascade', index=True)
    etype = fields.Selection([('income', 'دخل إضافي'), ('expense', 'مصروف'),
                              ('salary', 'راتب')], required=True)
    name = fields.Char('البيان', required=True)
    amount = fields.Float('المبلغ')
    date = fields.Date('التاريخ')
    note = fields.Char('ملاحظة')
    expense_id = fields.Many2one('nursery.expense', string='سند المصروف',
                                 ondelete='set null')
