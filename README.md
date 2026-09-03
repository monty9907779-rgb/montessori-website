# Montessori Nursery Website

موقع حضانة كوكب الطفل الحر في جدة، المملكة العربية السعودية.

المشروع الحالي هو موقع تعريفي وتسويقي حديث مبني باستخدام Next.js، مع دعم كامل للغتين العربية والإنجليزية، ونموذج تواصل، ورابط منفصل لبوابة أولياء الأمور المبنية على Odoo.

## نظرة عامة

الموقع يعرض:

- نبذة عن الحضانة وفلسفة مونتيسوري.
- البرامج التعليمية حسب المرحلة العمرية.
- المنهج والمجالات التعليمية.
- منهجية التعليم داخل الفصول.
- جدول اليوم والبيئة التعليمية.
- معرض الأنشطة.
- فريق العمل والوظائف.
- بيانات التواصل وخريطة الموقع.
- نموذج تواصل وإرسال استفسارات.
- رابط بوابة أولياء الأمور والإدارة.
- دعم العربية والإنجليزية مع اتجاه RTL للعربية.

## التقنيات

- Next.js `16.3.1`
- React `18`
- TypeScript `5.9.3`
- Tailwind CSS `3.4.1`
- next-intl للترجمة
- Lucide React للأيقونات
- Resend لإرسال رسائل نموذج الاتصال
- Vercel للنشر المقترح

## المتطلبات

- Node.js `18.18` أو أحدث
- npm `9` أو أحدث

يفضل استخدام إصدار LTS من Node.js عند تشغيل المشروع أو نشره.

## تشغيل المشروع محليًا

افتح Terminal وشغّل:

```bash
cd "/Users/mohamedmontaser/Documents/Claude/Projects/montessori website"
npm install
npm run dev
```

بعد ذلك افتح:

```text
http://localhost:3000
```

العربية:

```text
http://localhost:3000/ar
```

الإنجليزية:

```text
http://localhost:3000/en
```

## إعداد متغيرات البيئة

انسخ ملف الإعداد:

```bash
cp .env.example .env.local
```

ثم عدّل `.env.local`:

```env
# رابط الموقع الرئيسي
NEXT_PUBLIC_SITE_URL=https://montessori-ksa.com

# رابط نظام Odoo القديم
NEXT_PUBLIC_ODOO_URL=https://odoo.montessori-ksa.com

# إعدادات Resend لنموذج الاتصال
RESEND_API_KEY=re_your_actual_api_key_here
CONTACT_EMAIL_FROM=noreply@montessori-ksa.com
CONTACT_EMAIL_TO=info@montessori-ksa.com
```

لا ترفع `.env.local` أو أي API key إلى GitHub.

## بوابة أولياء الأمور

الموقع الحالي لا يحتوي على قاعدة بيانات أو تسجيل دخول داخلي. تسجيل الدخول والوظائف الإدارية موجودة في نظام Odoo القديم.

رابط البوابة الافتراضي:

```text
https://odoo.montessori-ksa.com/portal-login
```

يتم بناء الرابط من الملف:

```text
src/lib/legacy-platform.ts
```

ولتغيير الدومين، عدّل:

```env
NEXT_PUBLIC_ODOO_URL=https://odoo.montessori-ksa.com
```

## نموذج الاتصال

واجهة النموذج موجودة في:

```text
src/components/sections/ContactSection.tsx
```

والـ API موجود في:

```text
src/app/api/contact/route.ts
```

مسار الطلب:

```text
POST /api/contact
```

البيانات المتوقعة:

```json
{
  "name": "محمد أحمد",
  "email": "mohamed@example.com",
  "phone": "+966501234567",
  "childAge": "3",
  "program": "casa",
  "message": "أرغب في معرفة المزيد عن البرنامج"
}
```

الحماية الموجودة في النموذج:

- التحقق من الحقول المطلوبة.
- التحقق من البريد ورقم الهاتف.
- تحديد طول المدخلات.
- منع HTML وXSS داخل محتوى البريد.
- منع حقن أسطر جديدة في عنوان الرسالة.
- حد أقصى تقريبي قدره 5 طلبات لكل IP خلال ساعة.

يحتاج الإرسال الفعلي إلى `RESEND_API_KEY` صحيح ومفعّل.

## اللغات والترجمة

ملفات الترجمة:

```text
messages/ar.json
messages/en.json
```

نظام اللغات:

```text
src/i18n/request.ts
src/i18n/routing.ts
```

اللغة الافتراضية هي العربية، ويمكن تغييرها من الرابط أو زر اللغة في القائمة.

## بنية المشروع

```text
.
├── messages/
│   ├── ar.json
│   └── en.json
├── public/
│   ├── favicon.ico
│   ├── og-image.png
│   ├── robots.txt
│   ├── security.txt
│   └── sitemap.xml
├── src/
│   ├── app/
│   │   ├── [locale]/
│   │   ├── api/contact/
│   │   └── globals.css
│   ├── components/
│   │   ├── layout/
│   │   └── sections/
│   ├── i18n/
│   └── lib/
├── .env.example
├── next.config.mjs
├── package.json
├── tailwind.config.ts
└── tsconfig.json
```

## الأوامر

```bash
# تشغيل وضع التطوير
npm run dev

# إنشاء نسخة الإنتاج
npm run build

# تشغيل نسخة الإنتاج بعد نجاح البناء
npm start

# فحص TypeScript
npm run type-check

# فحص ESLint
npm run lint

# فحص ثغرات الحزم
npm run security-audit
```

## نتائج التحقق الحالية

تم التحقق من:

- صحة ملفات JSON الخاصة باللغتين.
- وجود مفاتيح الترجمة المستخدمة في الواجهة.
- صحة صياغة ملفات TypeScript وTSX.
- فحص الحزم المثبتة محليًا دون ثغرات معروفة في نتيجة `npm audit --offline`.

يجب إعادة تشغيل `npm run build` و`npm run lint` بعد تجهيز بيئة Node مستقرة وقبل النشر النهائي.

## الأمان

يستخدم المشروع عددًا من ترويسات الحماية، منها:

- `Strict-Transport-Security`
- `X-Frame-Options`
- `X-Content-Type-Options`
- `Referrer-Policy`
- `Permissions-Policy`
- `Content-Security-Policy`

تم ضبط `Content-Security-Policy` بحيث يسمح بـ `unsafe-eval` في التطوير فقط عند الحاجة، ولا يضيفه في الإنتاج.

## النشر على Vercel

### 1. رفع المشروع إلى GitHub

من داخل مجلد المشروع:

```bash
git init
git add .
git commit -m "Prepare Montessori nursery website"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

استبدل `USERNAME/REPOSITORY` ببيانات مستودعك.

### 2. ربط المشروع مع Vercel

1. افتح Vercel.
2. اختر `Add New Project`.
3. اختر مستودع GitHub.
4. اترك أمر البناء الافتراضي:

```bash
npm run build
```

5. أضف متغيرات البيئة التالية:

```text
NEXT_PUBLIC_SITE_URL
NEXT_PUBLIC_ODOO_URL
RESEND_API_KEY
CONTACT_EMAIL_FROM
CONTACT_EMAIL_TO
```

6. نفّذ Deploy.

## النشر من Terminal

يوجد سكربت نشر في:

```text
deploy.sh
```

قبل استخدامه، تأكد من:

- تسجيل الدخول إلى Vercel.
- ضبط متغيرات البيئة.
- نجاح `npm run build`.
- مراجعة المشروع والدومين قبل النشر العام.

## النسخة القديمة

يوجد نظام منفصل قديم في:

```text
/Users/mohamedmontaser/Documents/Codex/2026-08-21/new-chat-6/montessori-deploy
```

هذه النسخة مبنية على Python وOdoo، وتحتوي على:

- تسجيل دخول أولياء الأمور.
- ربط ولي الأمر بالطفل.
- بوابة متابعة الطفل.
- رسائل الأسرة والحضانة.
- إدارة الطلاب والفصول.
- الحضور والمدفوعات.
- الموظفين والصلاحيات.
- الإشعارات وبعض التكاملات الإدارية.

لا يتم نسخ ملفات Python وOdoo داخل مشروع Next.js. النسختان تعملان كجزأين منفصلين:

- Next.js: الموقع العام والتعريف بالحضانة.
- Odoo/Python: الحسابات والبوابة والإدارة.

## ملاحظات مهمة

- لا تضع مفاتيح API أو كلمات المرور داخل GitHub.
- لا تغيّر رابط Odoo إلا إذا كان النظام الجديد يستخدم نفس مسارات البوابة.
- يجب اختبار نموذج الاتصال بعد إضافة مفتاح Resend حقيقي.
- يجب اختبار العربي والإنجليزي على الهاتف والكمبيوتر قبل النشر.
- لم يتم تنفيذ نشر عام تلقائي من هذا الملف.

## الترخيص

هذا المشروع خاص بحضانة كوكب الطفل الحر. لا يُعاد توزيعه أو استخدامه تجاريًا بدون إذن مالك المشروع.
