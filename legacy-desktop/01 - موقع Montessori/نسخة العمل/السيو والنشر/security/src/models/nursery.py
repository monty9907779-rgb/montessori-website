# -*- coding: utf-8 -*-
import secrets
from datetime import datetime, time, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError

NURSERY_TZ = 'Asia/Riyadh'

# الشهر المتفق عليه في عقد الرسوم = 30 يوماً بالضبط. أي مبلغ يُدفع يُترجَم
# إلى أيام تغطية بهذا القاسم، وموعد الاستحقاق يتحرّك بعدد الأيام المدفوعة.
DAY_BASIS = 30


def days_for_amount(amount, monthly_fee):
    """عدد أيام التغطية لمبلغ مدفوع: (المدفوع ÷ الرسوم الشهرية) × 30.
    لو الرسوم غير محدّدة (صفر) نفترض أن الدفعة تغطّي شهراً كاملاً.
    (مقياس تقريبي للعرض فقط — لتحريك تاريخ الاستحقاق استخدم advance_due.)"""
    try:
        amount = float(amount or 0.0)
        fee = float(monthly_fee or 0.0)
    except (TypeError, ValueError):
        return 0
    if amount <= 0:
        return 0
    if fee <= 0:
        return DAY_BASIS
    return int(round(amount / fee * DAY_BASIS))


def coverage_for(amount, monthly_fee):
    """تغطية الدفعة = (شهور كاملة، أيام إضافية).

    الشهور الكاملة تتحرّك كشهور تقويمية (٤ سبتمبر + ٣ شهور = ٤ ديسمبر)،
    والباقي فقط هو الذي يُحوَّل إلى أيام بقاسم 30. ده اللي بيخلّي
    «شهر + ٣ أيام» تطلع شهر وثلاث أيام بالظبط مهما كان طول الشهر."""
    try:
        amount = float(amount or 0.0)
        fee = float(monthly_fee or 0.0)
    except (TypeError, ValueError):
        return (0, 0)
    if amount <= 0:
        return (0, 0)
    if fee <= 0:
        return (1, 0)
    months = int(amount // fee)
    rem = amount - months * fee
    days = int(round(rem / fee * DAY_BASIS))
    if days >= DAY_BASIS:       # التقريب رفع الباقي لشهر كامل
        months += 1
        days = 0
    return (months, days)


def advance_due(anchor, amount, monthly_fee):
    """تاريخ الاستحقاق الجديد = المرساة + شهور كاملة تقويمية + أيام الباقي."""
    months, days = coverage_for(amount, monthly_fee)
    return anchor + relativedelta(months=months) + timedelta(days=days)


def _new_token():
    return secrets.token_hex(16)

TERMS = [
    ('term_2026', 'ترم 2026'),
    ('summer_2026', 'صيف 2026'),
    ('term_2027', 'ترم 2027'),
]

PLAN_CODES = [
    ('daily', 'يومي'),
    ('weekly', 'أسبوعي'),
    ('monthly', 'شهري'),
    ('term', 'ترم'),
    ('term2', 'ترمين'),
]

PAYMENT_METHODS = [
    ('cash', 'كاش'),
    ('transfer', 'تحويل بنكي'),
    ('card', 'بطاقة'),
    ('other', 'أخرى'),
]

STUDENT_LEVELS = [
    ('prekg', 'Pre-KG'),
    ('kg1', 'KG1'),
    ('kg2', 'KG2'),
    ('kg3', 'KG3'),
]
BOOKS_FEE_DEFAULT = 1000.0


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
    gclid = fields.Char('معرّف ضغطة إعلان جوجل', index=True,
                        help='بييجي من الموقع لما ولي الأمر يوصل من إعلان. '
                             'بيتستخدم لرفع التسجيلات الفعلية لجوجل.')

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
        """اعتماد الطلب يثبت دور ولي الأمر ويربط كل أطفاله الموجودين.

        الحساب الموجود في سجل المستخدمين هو المرجع المعتمد داخل النظام؛ لذلك
        لا نحتاج إلى إعادة تعيين الدور من صفحة الأدوار بعد قبول طلب الربط.
        """
        for rec in self:
            if not rec.matched_student_id:
                raise ValidationError('اختاري الطفل الأول قبل الربط!')
            student = rec.matched_student_id.sudo()
            if not student.guardian_name:
                student.guardian_name = rec.parent_name
            if not student.guardian_phone and rec.parent_phone:
                student.guardian_phone = rec.parent_phone
            user = self.env['res.users'].sudo().search([
                '&', ('active', '=', True), '|',
                ('login', '=ilike', rec.parent_email.strip()),
                ('email', '=ilike', rec.parent_email.strip()),
            ], limit=1)
            if user:
                base_user = self.env.ref('base.group_user')
                portal = self.env.ref('base.group_portal')
                manager = self.env.ref('nursery.group_nursery_manager')
                teacher = self.env.ref('nursery.group_nursery_teacher')
                user.write({'groups_id': [(3, base_user.id), (3, manager.id),
                                          (3, teacher.id), (4, portal.id)],
                            'nursery_api_token': False})
                student._link_parent_user(user)
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
    # ربط الفصل بقناة كاميرا في مسجّل DVR (بث «طفلي فقط»)
    camera_channel = fields.Integer(
        'قناة الكاميرا', default=0,
        help='رقم قناة الكاميرا في مسجّل DVR التي تصوّر هذا الفصل (0 = غير مربوط)')

    @api.depends('student_ids')
    def _compute_student_count(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)


class NurseryFeePlan(models.Model):
    """جدول أسعار الاشتراك حسب مدة الدفع.

    كل خطة = طول فترة بالأيام + سعر الفترة. كل ما المدة تطول يقلّ
    السعر اليومي — وده اللي بيخلّي الأسبوعي (٣٠٠ ÷ ٧ = ٤٢.٩/يوم)
    أغلى من الشهري (١١٠٠ ÷ ٣٠ = ٣٦.٧/يوم).

    ⚠️ النظام كله بيفوتر بـ«رسوم شهرية» على قاسم DAY_BASIS = ٣٠ يوم
    (شوف coverage_for و advance_due و nursery.month). فبدل ما نغيّر
    محرّك الفوترة، بنترجم أي خطة لمكافئها الشهري ونحطّه في
    student.fees — وبكده التغطية والاستحقاق والتناسب والذمم تفضل
    تشتغل من غير أي تعديل."""
    _name = 'nursery.fee.plan'
    _description = 'خطة الدفع'
    _order = 'days, id'

    name = fields.Char('الخطة', required=True)
    code = fields.Selection(PLAN_CODES, string='الكود', required=True)
    days = fields.Integer('طول الفترة (أيام)', required=True,
                          help='يومي=1، أسبوعي=7، شهري=30، الترم حسب تقويم الحضانة')
    price = fields.Float('سعر الفترة (ر.س)',
                         help='اتركه صفراً لو الخطة لسه ما اتسعّرتش — لن تظهر للاختيار')
    monthly_equiv = fields.Float('المكافئ الشهري (٣٠ يوم)',
                                 compute='_compute_rates', store=True)
    daily_rate = fields.Float('السعر اليومي', compute='_compute_rates', store=True)
    priced = fields.Boolean('مُسعَّرة', compute='_compute_rates', store=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'كل خطة دفع لازم يكون لها كود فريد!'),
    ]

    @api.depends('price', 'days')
    def _compute_rates(self):
        for rec in self:
            d = rec.days or 0
            p = rec.price or 0.0
            rec.daily_rate = round(p / d, 2) if d > 0 else 0.0
            rec.monthly_equiv = round(p / d * DAY_BASIS, 2) if d > 0 else 0.0
            rec.priced = bool(d > 0 and p > 0)

    @api.constrains('days')
    def _check_days(self):
        for rec in self:
            if rec.days <= 0:
                raise ValidationError('طول الفترة لازم يكون أكبر من صفر.')


class NurseryStudent(models.Model):
    _name = 'nursery.student'
    _description = 'الطالب'
    _inherit = ['mail.thread']
    _order = 'serial, name'

    name = fields.Char('اسم الطالب', required=True, tracking=True)
    serial = fields.Integer('الرقم التسلسلي')
    term = fields.Selection(TERMS, string='الترم', default='term_2026', tracking=True)
    level = fields.Selection(STUDENT_LEVELS, string='المرحلة', tracking=True,
                             help='مرحلة الطالب التي تحدد قسم الكتب تلقائياً: KG1 أو KG2 أو KG3')
    class_id = fields.Many2one('nursery.class', string='الفصل', tracking=True)
    joining_date = fields.Date('تاريخ الالتحاق')

    guardian_name = fields.Char('اسم ولي الأمر')
    father_name = fields.Char('اسم الأب')
    mother_name = fields.Char('اسم الأم')
    guardian_phone = fields.Char('تليفون ولي الأمر')
    guardian_phone2 = fields.Char('تليفون إضافي')
    emergency_note = fields.Char('ملاحظات طبية / طوارئ')

    plan_id = fields.Many2one(
        'nursery.fee.plan', string='خطة الدفع', tracking=True,
        domain="[('priced', '=', True)]",
        help='اختيار الخطة بيملأ «الرسوم الشهرية» بمكافئها الشهري تلقائياً. '
             'تقدر تعدّل الرقم بعدها لو الطالب له اتفاق خاص.')
    plan_price = fields.Float('سعر الفترة', related='plan_id.price', readonly=True)
    plan_days = fields.Integer('طول الفترة (أيام)', related='plan_id.days', readonly=True)
    fees = fields.Float('الرسوم الشهرية', tracking=True,
                        help='المكافئ الشهري (٣٠ يوم) — الأساس اللي بتتحسب عليه '
                             'التغطية والاستحقاق مهما كانت خطة الدفع')
    books_fees = fields.Float('رسوم الكتب', default=BOOKS_FEE_DEFAULT)
    paid = fields.Boolean('مدفوع', tracking=True)
    paid_at = fields.Date('تاريخ الدفع')
    paid_until = fields.Date('مدفوع حتى')
    payment_method = fields.Selection(PAYMENT_METHODS, string='طريقة الدفع')

    payment_ids = fields.One2many('nursery.fee.payment', 'student_id', string='المدفوعات')
    attendance_ids = fields.One2many('nursery.attendance', 'student_id', string='الحضور')
    book_move_ids = fields.One2many('nursery.book.move', 'student_id', string='الكتب')
    total_paid = fields.Float('إجمالي المدفوع', compute='_compute_total_paid')
    books_paid = fields.Float('المدفوع من رسوم الكتب', compute='_compute_books_balance')
    books_remaining = fields.Float('المتبقي من رسوم الكتب', compute='_compute_books_balance')

    # ----- الذمم المدينة (A/R) عبر كشوف الشهور (محاسبة استحقاق) -----
    total_billed = fields.Float('إجمالي المفوتر', compute='_compute_ar',
                                help='مجموع الإيراد المُعترَف به (المستحق) عبر كل الشهور')
    total_collected = fields.Float('إجمالي المُحصَّل', compute='_compute_ar')
    receivable = fields.Float('الرصيد المستحق على وليّ الأمر', compute='_compute_ar',
                              help='المفوتر − المُحصَّل. موجب = مدين (عليه)، سالب = دائن (مقدّم)')

    def _compute_ar(self):
        Fee = self.env['nursery.month.fee'].sudo()
        for s in self:
            rows = Fee.search([('student_id', '=', s.id)])
            tuition_billed = sum(rows.mapped('fees'))
            tuition_collected = sum(rows.mapped('paid'))
            books_collected = sum(
                p.amount for p in s.payment_ids if p.payment_type == 'books')
            billed = tuition_billed + BOOKS_FEE_DEFAULT
            collected = tuition_collected + books_collected
            s.total_billed = billed
            s.total_collected = collected
            s.receivable = billed - collected

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
    parent_user_ids = fields.Many2many(
        'res.users', 'nursery_student_parent_rel', 'student_id', 'user_id',
        string='أولياء الأمور', copy=False,
        help='كل الحسابات المرتبطة بهذا الطفل؛ يسمح لولي الأمر الواحد بأكثر من طفل.')

    # ----- تسجيل الوجه (بث «طفلي فقط») -----
    face_photo_ids = fields.One2many('nursery.face.photo', 'student_id', string='صور الوجه')
    face_photo_count = fields.Integer('عدد صور الوجه', compute='_compute_face')
    face_ready = fields.Boolean('جاهز للتعرّف', compute='_compute_face',
                                help='يصبح جاهزاً عند رفع صورتين واضحتين للوجه على الأقل')
    face_enrolled = fields.Boolean(
        'تم استخراج البصمة', default=False, copy=False,
        help='يضعه سيرفر التعرّف بعد حساب بصمة ArcFace من الصور')

    @api.depends('face_photo_ids')
    def _compute_face(self):
        for rec in self:
            n = len(rec.face_photo_ids)
            rec.face_photo_count = n
            rec.face_ready = n >= 2

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
        recs = super().create(vals_list)
        for vals, rec in zip(vals_list, recs):
            if vals.get('parent_user_id'):
                rec._link_parent_user(self.env['res.users'].sudo().browse(vals['parent_user_id']))
        return recs

    def _link_parent_user(self, user):
        """أضف حساب ولي الأمر بدون إلغاء ربطه بالأطفال الآخرين."""
        self.ensure_one()
        user = user.sudo()
        if not user.exists():
            return
        self.sudo().write({'parent_user_ids': [(4, user.id)]})
        if not self.parent_user_id:
            self.sudo().write({'parent_user_id': user.id})

    def write(self, vals):
        res = super().write(vals)
        # اسم الطالب في كشوف الشهور (nursery.month.fee.name) لقطة نصّية
        # اتاخدت وقت فتح الشهر — عشان الصفوف اللي اتشال طالبها تفضل مقروءة.
        # لكن ده كان معناه إن تغيير الاسم في «الطلاب» ما يوصلش لـ«الحسابات».
        # نرحّل الاسم الجديد لكل صفوف الطالب في كل الشهور.
        if vals.get('name'):
            self.env['nursery.month.fee'].sudo().search(
                [('student_id', 'in', self.ids)]
            ).write({'name': vals['name']})
        # حافظ على الحقل القديم للتوافق، مع إضافة العلاقة الجديدة متعددة الأطفال.
        uid = vals.get('parent_user_id')
        if uid:
            user = self.env['res.users'].sudo().browse(uid)
            for rec in self:
                rec._link_parent_user(user)
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

    @api.onchange('plan_id')
    def _onchange_plan_id(self):
        """اختيار خطة بيملأ الرسوم الشهرية بمكافئها — onchange مش compute
        عشان يفضل ممكن تعدّل الرقم يدوياً لطالب له اتفاق خاص."""
        if self.plan_id and self.plan_id.monthly_equiv:
            self.fees = self.plan_id.monthly_equiv

    @api.depends('payment_ids.amount', 'payment_ids.payment_type')
    def _compute_total_paid(self):
        for rec in self:
            rec.total_paid = sum(
                p.amount for p in rec.payment_ids if p.payment_type != 'books')

    @api.depends('books_fees', 'payment_ids.amount', 'payment_ids.payment_type')
    def _compute_books_balance(self):
        for rec in self:
            due = BOOKS_FEE_DEFAULT
            paid = sum(
                p.amount for p in rec.payment_ids if p.payment_type == 'books')
            rec.books_paid = round(paid, 2)
            rec.books_remaining = round(max(0.0, due - paid), 2)


class NurseryFacePhoto(models.Model):
    """صورة وجه مرجعية لطفل — تُستخدم لاستخراج بصمة ArcFace لبث «طفلي فقط».
    تُخزَّن داخل أودو (خلف توكن المديرة) — لا تُنشر أبداً على رابط عام."""
    _name = 'nursery.face.photo'
    _description = 'صورة وجه مرجعية (بموافقة ولي الأمر)'
    _order = 'id desc'

    student_id = fields.Many2one(
        'nursery.student', string='الطالب', required=True,
        ondelete='cascade', index=True)
    image = fields.Image('الصورة', required=True, max_width=1024, max_height=1024)
    image_256 = fields.Image('مصغّرة', related='image', max_width=256, max_height=256, store=True)
    note = fields.Char('ملاحظة')
    # يضعها سيرفر التعرّف بعد استخراج بصمة صالحة من هذه الصورة
    embedded = fields.Boolean('استُخرجت بصمتها', default=False, copy=False)
    quality = fields.Char('جودة الوجه', copy=False,
                          help='ok / no_face / multi_face — يحدّده سيرفر التعرّف')

    def write(self, vals):
        # أي تعديل على الصورة يبطل البصمة القديمة → يُعاد الاستخراج
        if 'image' in vals:
            vals.setdefault('embedded', False)
        res = super().write(vals)
        if 'image' in vals:
            self.mapped('student_id').write({'face_enrolled': False})
        return res

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs.mapped('student_id').write({'face_enrolled': False})
        return recs


class NurseryFeePayment(models.Model):
    _name = 'nursery.fee.payment'
    _description = 'دفعة رسوم'
    _order = 'date desc, id desc'

    student_id = fields.Many2one(
        'nursery.student', string='الطالب', required=True, ondelete='cascade')
    date = fields.Date('التاريخ', default=fields.Date.context_today, required=True)
    amount = fields.Float('المبلغ', required=True)
    payment_type = fields.Selection([
        ('tuition', 'رسوم الحضانة'),
        ('books', 'رسوم الكتب'),
    ], string='نوع الدفعة', required=True, default='tuition')
    method = fields.Selection(PAYMENT_METHODS, string='طريقة الدفع', default='cash')
    period = fields.Char('عن فترة')  # e.g. "يونيو 2026"
    note = fields.Char('ملاحظة')
    # تغطية الدفعة بالأيام (الشهر = 30 يوماً) — تُخزَّن وقت التسجيل حتى يمكن
    # عرضها لاحقاً والتراجع عنها بدقة عند حذف الدفعة.
    days = fields.Integer('عدد الأيام المغطاة')
    until_before = fields.Date('الاستحقاق قبل هذه الدفعة')
    until_after = fields.Date('الاستحقاق بعد هذه الدفعة')

    def unlink(self):
        """حذف سند الدفع يعكس أثره في كشف الشهر والاستحقاق تلقائياً.

        يمنع الحذف من الشهر المقفول حتى لو تم الحذف من واجهة Odoo مباشرة،
        وليس من API المديرة فقط.
        """
        Month = self.env['nursery.month'].sudo()
        Fee = self.env['nursery.month.fee'].sudo()
        for payment in self:
            month = Month.search([
                ('ym', '=', payment.date.strftime('%Y-%m') if payment.date else ''),
            ], limit=1)
            if month and month.state == 'closed':
                raise ValidationError('هذه الدفعة داخل شهر محاسبي مقفول — لا يمكن حذفها')
            linked = Fee.search([('payment_id', '=', payment.id)])
            if linked:
                linked.write({'paid': 0.0, 'paid_date': False, 'method': False,
                              'payment_id': False, 'days_paid': 0,
                              'until_before': False})
            student = payment.student_id
            if student and payment.until_before and payment.until_after \
                    and student.paid_until == payment.until_after:
                student.write({'paid_until': payment.until_before})
        return super().unlink()


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
    closed_by = fields.Many2one('res.users', string='أغلقه', readonly=True,
                                copy=False)
    fee_ids = fields.One2many('nursery.month.fee', 'month_id', string='رسوم الطلبة')
    entry_ids = fields.One2many('nursery.month.entry', 'month_id', string='القيود')

    _sql_constraints = [
        ('uniq_ym', 'unique(ym)', 'هذا الشهر مفتوح بالفعل!'),
    ]

    # ==================== محرّك الفوترة (محاسبة الاستحقاق) ====================
    @api.model
    def _prorated_fee(self, full_fee, joining_date, ym):
        """المستحق (الإيراد المُعترَف به) هذا الشهر: متناسب بالأيام في شهر الالتحاق
        فقط (قاسم ثابت 30)، وكامل بعده. الصيغة: (31 − يوم الالتحاق) ÷ 30 × الرسوم."""
        full_fee = full_fee or 0.0
        try:
            if joining_date and joining_date.strftime('%Y-%m') == ym:
                day = min(max(joining_date.day, 1), 30)
                return round(full_fee * (31 - day) / 30.0, 2)
        except Exception:
            pass
        return full_fee

    def _expense_cash_movement(self):
        """حركة المصروفات النقدية بإشارة الشيت.

        سطر نسرين الموجب هو مصدر الرصيد الافتتاحي، لذلك لا يدخل مرة ثانية
        في حركة الكاش. أما المصروفات الخارجة فتُسجّل بالسالب كما في الملف.
        الإدخال اليدوي القديم الذي يحفظ مصروفاً موجباً يُعامل كمصروف خارج.
        """
        opening = 0.0
        movement = 0.0
        for entry in self.entry_ids:
            if entry.etype != 'expense':
                continue
            amount = float(entry.amount or 0.0)
            if amount > 0 and 'نسرين' in (entry.name or ''):
                opening += amount
                continue
            movement += amount if amount < 0 else -amount
        return opening, movement

    def _month_closing(self):
        """الرصيد الختامي النقدي المرحّل، وليس صافي التشغيل.

        يطابق On hand Randa في الشيت: افتتاحي + كاش رندا + الدخل النقدي
        + المصروفات الخارجة. التحويل البنكي والرواتب لهما عرض/تدقيق منفصل.
        """
        self.ensure_one()
        methods = set(self.fee_ids.mapped('method'))
        collected = sum((f.paid or 0.0) for f in self.fee_ids
                        if not methods or f.method in (False, 'cash'))
        inc = sum(e.amount for e in self.entry_ids if e.etype == 'income')
        res = sum(e.amount for e in self.entry_ids if e.etype == 'reservation')
        _opening_entry, expense_movement = self._expense_cash_movement()
        return (self.opening_balance or 0.0) + collected + inc + res + expense_movement

    @api.model
    def _open_month(self, ym):
        """يفتح شهر فوترة (لو مش مفتوح): يُنشئ لكل طالب نشط فاتورة الشهر —
        يُعترَف بالإيراد (fees، متناسب في شهر التسجيل) ويُرحَّل رصيد الذمم
        (مدين على وليّ الأمر) الذي يُغلق لاحقاً بالتحصيل (paid). idempotent."""
        existing = self.search([('ym', '=', ym)], limit=1)
        if existing:
            return existing
        prev = self.search([('ym', '<', ym)], order='ym desc', limit=1)
        open_bal = prev._month_closing() if prev else 0.0
        month = self.create({'ym': ym, 'opening_balance': open_bal})
        Fee = self.env['nursery.month.fee']
        import calendar as _cal
        month_end = datetime.strptime(
            '%s-%02d' % (ym, _cal.monthrange(int(ym[:4]), int(ym[5:7]))[1]),
            '%Y-%m-%d').date()
        if prev:
            for f in prev.fee_ids:
                st = f.student_id
                if st and not st.active:
                    continue
                if st and st.joining_date and st.joining_date > month_end:
                    continue
                full = (st.fees if st else 0.0) or f.full_fee or f.fees or 0.0
                due = self._coverage_due(st, full, ym)
                carry = (f.carry_in or 0.0) + (f.paid or 0.0) - (f.fees or 0.0)
                Fee.create({'month_id': month.id, 'student_id': st.id or False,
                            'name': f.name, 'full_fee': full, 'fees': due,
                            'carry_in': carry})
        else:
            for s in self.env['nursery.student'].search(
                    [('active', '=', True)], order='name'):
                if s.joining_date and s.joining_date > month_end:
                    continue
                full = s.fees or 0.0
                due = self._coverage_due(s, full, ym)
                Fee.create({'month_id': month.id, 'student_id': s.id, 'name': s.name,
                            'full_fee': full, 'fees': due, 'carry_in': 0.0})
        return month

    def _coverage_due(self, student, full_fee, ym):
        """المستحق على أساس الأيام: أيام الشهر غير المغطّاة بتغطية سابقة.
        الطالب المدفوع لغاية ٢٧ أغسطس لا يُطالَب بشهر أغسطس كاملاً — بل بالأيام
        الباقية فقط. القاعدة: شهر = ٣٠ يوماً، والمستحق لا يتجاوز الرسوم الكاملة.
        (قرار المالك 2026-08-05: كشف الحسابات يتبع الأيام لا الشهر التقويمي.)"""
        import calendar as _cal
        import datetime as _dt
        y, mo = int(ym[:4]), int(ym[5:7])
        mstart = _dt.date(y, mo, 1)
        ndays = _cal.monthrange(y, mo)[1]
        covered = 0
        if student and student.paid_until:
            covered = max(0, min((student.paid_until - mstart).days, ndays))
        late = 0
        if student and student.joining_date and student.joining_date > mstart:
            late = min((student.joining_date - mstart).days, ndays)
        uncovered = max(0, ndays - covered - late)
        if not full_fee:
            return 0.0
        return round(min(full_fee, full_fee * uncovered / DAY_BASIS), 2)

    @api.model
    def cron_ensure_current_month(self):
        """كرون يومي: يفتح شهر الفوترة الحالي تلقائياً (بتوقيت الرياض) —
        فالفوترة الشهرية تتولّد من التسجيل دون تدخّل يدوي."""
        now = datetime.utcnow() + timedelta(hours=3)
        self._open_month(now.strftime('%Y-%m'))


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
    full_fee = fields.Float('الرسوم الشهرية الكاملة')
    fees = fields.Float('المستحق هذا الشهر')   # متناسب في شهر الالتحاق، كامل بعده
    paid = fields.Float('المدفوع')
    excel_remaining = fields.Float('الباقي من Excel')
    paid_date = fields.Date('تاريخ الدفع')
    method = fields.Selection(PAYMENT_METHODS, string='طريقة الدفع')
    note = fields.Char('ملاحظة')
    # محاسبة الاستحقاق: رصيد مُرحّل (+ رصيد دائن مدفوع مقدّماً / − متأخّرات)
    carry_in = fields.Float('رصيد مُرحّل من الشهر السابق')
    carry_out = fields.Float('الرصيد المُرحّل للتالي', compute='_compute_carry_out')
    payment_id = fields.Many2one('nursery.fee.payment', string='سند الدفع',
                                 ondelete='set null')
    # تغطية الدفعة بالأيام (الشهر = 30 يوماً). until_before = موعد الاستحقاق
    # قبل احتساب هذا السطر، حتى تظل إعادة الحفظ/التعديل مُتَّسقة ولا تُزحزح
    # التاريخ مرّتين.
    days_paid = fields.Integer('عدد الأيام المدفوعة')
    until_before = fields.Date('الاستحقاق قبل هذه الدفعة')

    @api.depends('carry_in', 'paid', 'fees')
    def _compute_carry_out(self):
        for r in self:
            r.carry_out = (r.carry_in or 0.0) + (r.paid or 0.0) - (r.fees or 0.0)


class NurseryMonthEntry(models.Model):
    """قيد شهري: دخل إضافي / مصروف / راتب."""
    _name = 'nursery.month.entry'
    _description = 'قيد شهري'
    _order = 'date, id'

    month_id = fields.Many2one('nursery.month', required=True,
                               ondelete='cascade', index=True)
    etype = fields.Selection([('income', 'دخل إضافي'), ('expense', 'مصروف'),
                              ('salary', 'راتب'),
                              ('reservation', 'حجز مقدّم')], required=True)
    name = fields.Char('البيان', required=True)
    amount = fields.Float('المبلغ')
    date = fields.Date('التاريخ')
    note = fields.Char('ملاحظة')
    expense_id = fields.Many2one('nursery.expense', string='سند المصروف',
                                 ondelete='set null')


class NurseryAdClick(models.Model):
    """عدّاد يومي للنقرات المدفوعة الواصلة للموقع — تاريخ دائم.

    سجلّ nginx يتدوّر كل يومين تقريباً، فنُثبّت العدّ هنا قبل أن يُمحى.
    المصدر: معرّفات gclid/wbraid الفريدة في سجلّ الخادم — مستقلة تماماً
    عن حساب Google Ads.
    """
    _name = 'nursery.ad.click'
    _description = 'نقرات إعلانية يومية'
    _order = 'day desc, clicks desc'
    _rec_name = 'campaign'

    day = fields.Date('اليوم', required=True, index=True)
    campaign = fields.Char('معرّف الحملة', required=True, index=True)
    clicks = fields.Integer('النقرات', default=0)

    _sql_constraints = [
        ('day_campaign_uniq', 'unique(day, campaign)',
         'يوجد سجل لهذه الحملة في هذا اليوم بالفعل.'),
    ]

    @api.model
    def record(self, day, campaign, clicks):
        """تثبيت عدّ يوم/حملة. نأخذ الأكبر: العدّ ينمو خلال اليوم الجاري،
        وبعد تدوير السجلّ قد يعود ناقصاً — فلا نسمح له بالتراجع."""
        rec = self.sudo().search(
            [('day', '=', day), ('campaign', '=', campaign)], limit=1)
        if rec:
            if clicks > rec.clicks:
                rec.clicks = clicks
            return rec
        return self.sudo().create(
            {'day': day, 'campaign': campaign, 'clicks': clicks})


class NurseryVisit(models.Model):
    """موعد زيارة لعميل محتمل — يظهر في تقويم الزيارات ويُدار من قمع المبيعات."""
    _name = 'nursery.visit'
    _description = 'موعد زيارة'
    _order = 'when_dt asc'
    _rec_name = 'lead_name'

    lead_name = fields.Char('اسم العميل', required=True)
    phone = fields.Char('الجوال')
    conv_id = fields.Char('معرّف محادثة Chatwoot', index=True)
    when_dt = fields.Datetime('موعد الزيارة', required=True, index=True)
    note = fields.Char('ملاحظة')
    state = fields.Selection([
        ('scheduled', 'مجدولة'),
        ('done', 'تمّت'),
        ('missed', 'لم يحضر'),
        ('cancelled', 'ملغاة'),
    ], default='scheduled', required=True, index=True)
    source = fields.Selection([
        ('staff', 'حدّدها الفريق'),
        ('customer', 'حجزها العميل'),
    ], default='staff')
    reminded_day = fields.Boolean('ذُكِّر قبل يوم', default=False)
    reminded_soon = fields.Boolean('ذُكِّر قبل الموعد', default=False)
