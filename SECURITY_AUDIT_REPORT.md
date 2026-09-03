# 🔒 تقرير الأوديت الشامل - حضانة كوكب الطفل الحر
## Security & Technical Audit Report

**تاريخ التقرير:** 19 أغسطس 2026  
**المشروع:** Planet of the Free Child Nursery Website  
**التقنية:** Next.js 14.2.29 + TypeScript + Tailwind CSS  
**الدومين:** montessori-ksa.com  

---

## 📊 ملخص تنفيذي | Executive Summary

### ✅ النقاط الإيجابية
- **كود نظيف بدون ثغرات XSS:** لا يوجد استخدام لـ `dangerouslySetInnerHTML` أو `eval`
- **لا توجد أسرار مكشوفة:** لا يوجد API keys أو passwords في الكود
- **TypeScript:** استخدام كامل للـ TypeScript مع type safety
- **بدون console logs:** الكود production-ready
- **تحقق من المدخلات:** validation صحيح في الـ forms

### ⚠️ المشاكل الحرجة التي تحتاج إصلاح فوري
1. **6 ثغرات أمنية عالية الخطورة** في الـ dependencies
2. **معلومات اتصال غير مكتملة** (رقم هاتف وهمي)
3. **غياب ملفات SEO أساسية** (robots.txt, sitemap.xml)
4. **لا يوجد .gitignore** - خطر نشر ملفات حساسة
5. **البريد في Footer مختلف** عن باقي الموقع

---

## 🚨 القسم الأمني | Security Issues

### 1️⃣ ثغرات Dependencies الحرجة

#### التفاصيل:
```
• عدد الثغرات: 6 (1 متوسطة + 5 عالية)
• المكتبات المتأثرة:
  - Next.js (14.2.29) → يحتاج ترقية لـ 16.3.1
  - next-intl (3.26.5) → يحتاج ترقية لـ 4.13.7
  - postcss (مدمج مع Next.js)
  - glob (مدمج مع eslint-config-next)
```

#### الثغرات بالتفصيل:

**أ) Next.js - 5 ثغرات:**
- **DoS Attack** (GHSA-mwv6-3258-q52c, GHSA-5j59-xgg2-r9c4)
  - الخطورة: High (7.5 CVSS)
  - الوصف: إمكانية تعطيل الموقع عبر Server Components
  
- **SSRF Attack** (GHSA-4342-x723-ch2f)
  - الخطورة: Moderate (6.5 CVSS)
  - الوصف: إمكانية الوصول لمصادر داخلية عبر middleware redirect
  
- **Cache Confusion** (GHSA-g5qg-72qw-gw5v)
  - الخطورة: Moderate (6.2 CVSS)
  - الوصف: تسريب صور محسّنة لمستخدمين آخرين

- **Information Disclosure** (GHSA-955p-x3mx-jcvp)
  - الخطورة: Moderate
  - الوصف: كشف Server Function endpoints

**ب) next-intl - 2 ثغرات:**
- **Open Redirect** (GHSA-8f24-v5vv-gm5j)
  - الخطورة: Moderate
  - الوصف: إمكانية إعادة توجيه لمواقع خبيثة

- **Prototype Pollution** (GHSA-4c35-wcg5-mm9h)
  - الخطورة: Moderate (4.2 CVSS)
  - الوصف: تلوث Object prototype عبر translation keys

**ج) PostCSS - 4 ثغرات:**
- **Path Traversal** (GHSA-r28c-9q8g-f849, GHSA-6g55-p6wh-862q)
  - الخطورة: High (7.5 CVSS)
  - الوصف: قراءة ملفات .map من المسارات الداخلية

- **XSS via CSS** (GHSA-qx2v-qp2m-jg93)
  - الخطورة: Moderate (6.1 CVSS)
  - الوصف: XSS عبر `</style>` غير مُعالج

**د) glob - ثغرة واحدة:**
- **Command Injection** (GHSA-5j98-mcp5-4vw2)
  - الخطورة: High (7.5 CVSS)
  - الوصف: تنفيذ أوامر shell عبر CLI

#### 🔧 الحل:
```bash
# ترقية المكتبات للإصدارات الآمنة
npm install next@16.3.1
npm install next-intl@4.13.7
npm install eslint-config-next@16.3.1
npm audit fix --force
```

⚠️ **ملاحظة:** الترقية لـ Next.js 16 و next-intl 4 قد تحتاج تعديلات في الكود (breaking changes).

---

### 2️⃣ معلومات اتصال غير صحيحة

**المشكلة:**
- رقم الهاتف: `+966 XX XXX XXXX` (placeholder وهمي)
- البريد في Footer: `info@planet-free-child.com` ❌
- البريد في باقي الموقع: `info@montessori-ksa.com` ✅

**التأثير:**
- عملاء محتملين لا يستطيعون التواصل
- تجربة مستخدم سيئة
- فقدان فرص تسجيل جديدة

**الحل:**
```tsx
// src/components/layout/Footer.tsx:64-65
- <li>📞 +966 XX XXX XXXX</li>
- <li>✉️ info@planet-free-child.com</li>
+ <li>📞 +966 XX XXX XXXX</li>  // ← استبدل برقم حقيقي
+ <li>✉️ info@montessori-ksa.com</li>
```

---

### 3️⃣ غياب .gitignore - خطر أمني

**المشكلة:**
- لا يوجد ملف `.gitignore`
- خطر نشر ملفات حساسة على Git:
  - `.env` و `.env.local` (أسرار)
  - `node_modules` (370 MB)
  - `.next` (57 MB build files)
  - logs و temp files

**الحل:**
سأنشئ `.gitignore` قياسي لـ Next.js

---

### 4️⃣ لا يوجد Content Security Policy (CSP)

**المشكلة:**
- لا توجد HTTP headers أمنية
- عدم وجود CSP يزيد من خطر XSS
- عدم وجود security headers أخرى

**الحل:**
إضافة security headers في `next.config.mjs`

---

## 🔍 القسم التقني | Technical Issues

### 5️⃣ مكتبات قديمة جداً

**المكتبات التي تحتاج ترقية:**
```
┌─────────────────────┬─────────┬──────────┬─────────┐
│ Package             │ Current │ Wanted   │ Latest  │
├─────────────────────┼─────────┼──────────┼─────────┤
│ @types/node         │ 20.x    │ 20.x     │ 26.2.0  │
│ @types/react        │ 18.x    │ 18.x     │ 19.2.18 │
│ @types/react-dom    │ 18.x    │ 18.x     │ 19.2.4  │
│ eslint              │ 8.57.1  │ 8.57.1   │ 10.8.1  │
│ framer-motion       │ 11.18.2 │ 11.18.2  │ 13.1.0  │
│ lucide-react        │ 0.383.0 │ 0.383.0  │ 1.33.0  │
│ next                │ 14.2.29 │ 14.2.29  │ 16.3.1  │
│ react               │ 18.3.1  │ 18.3.1   │ 19.2.8  │
│ react-dom           │ 18.3.1  │ 18.3.1   │ 19.2.8  │
│ tailwindcss         │ 3.4.19  │ 3.4.19   │ 4.3.3   │
│ typescript          │ 5.9.3   │ 5.9.3    │ 7.0.2   │
└─────────────────────┴─────────┴──────────┴─────────┘
```

**التأثير:**
- فقدان ميزات جديدة وتحسينات الأداء
- bugs معروفة لم يتم إصلاحها
- عدم compatibility مع أدوات جديدة

---

### 6️⃣ غياب ملفات SEO أساسية

**المفقود:**
1. ❌ `robots.txt` - لتوجيه محركات البحث
2. ❌ `sitemap.xml` - خريطة الموقع
3. ❌ `manifest.json` - لـ PWA
4. ❌ `favicon.ico` - أيقونة الموقع
5. ❌ OpenGraph images - للمشاركة على السوشيال ميديا

**التأثير على SEO:**
- صعوبة فهرسة الموقع على Google
- ظهور سيء عند المشاركة على WhatsApp/Twitter
- فقدان ترتيب في نتائج البحث

---

### 7️⃣ مشاكل Accessibility

**المشاكل:**
1. **Fonts من Google**: تحميل خارجي يبطئ الموقع
   ```tsx
   // src/app/[locale]/layout.tsx:54-57
   <link href="https://fonts.googleapis.com/..." />
   ```
   ✅ الحل: استخدام `next/font` لتحميل محلي

2. **لا يوجد Skip to content**: مهم لمستخدمي screen readers

3. **Focus styles غير واضحة**: صعوبة التنقل بالكيبورد

---

### 8️⃣ مشاكل الأداء | Performance

**حجم Bundle:**
- Build size: 57 MB (`.next/`)
- Dependencies: 370 MB (`node_modules`)
- Main page JS: ~204 KB (مقبول)

**المشاكل:**
1. **لا يوجد Image optimization**: الصور placeholder فقط
2. **Framer Motion**: مكتبة ثقيلة (40KB+) لـ animations بسيطة
3. **Google Fonts**: تحميل خارجي يؤخر FCP

**التحسينات المقترحة:**
- استبدال Framer Motion بـ CSS animations
- استخدام `next/font` بدل Google CDN
- إضافة صور حقيقية optimized

---

## 📝 القسم الوظيفي | Functional Issues

### 9️⃣ فورم Contact غير متصل

**المشكلة:**
```tsx
// src/components/sections/ContactSection.tsx:67-75
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  if (!validate()) return;
  setLoading(true);
  // Simulate async submit ← لا يرسل بيانات حقيقية!
  await new Promise((res) => setTimeout(res, 800));
  setLoading(false);
  setSubmitted(true);
};
```

**التأثير:**
- **الرسائل لا تصل!** العملاء المحتملين يظنون أنهم أرسلوا ولكن لا أحد يستلم
- فقدان leads ومبيعات محتملة

**الحل:**
- ربط Form بـ API endpoint
- استخدام SendGrid/Resend لإرسال إيميلات
- أو ربط بـ Google Forms/Typeform

---

### 🔟 روابط السوشيال ميديا وهمية

**المشكلة:**
```tsx
// src/components/layout/Footer.tsx:69-74
{ label: "Instagram", icon: "📷", href: "#" },  // ← روابط فارغة
{ label: "Twitter", icon: "✖️", href: "#" },
{ label: "Snapchat", icon: "👻", href: "#" },
{ label: "WhatsApp", icon: "💬", href: "#" },
```

**الحل:**
استبدال بروابط حقيقية أو إخفاء الأزرار.

---

## 🌐 مشاكل SEO و Metadata

### 1️⃣ Keywords قديمة

```tsx
// src/app/[locale]/layout.tsx:23
keywords: "montessori, nursery, Jeddah, KSA, preschool, early childhood, حضانة, مونتيسوري, جدة",
```

❌ لا تحتوي على الاسم الجديد "كوكب الطفل الحر / Planet of the Free Child"

**الحل:**
```tsx
keywords: "كوكب الطفل الحر, Planet of the Free Child, montessori, nursery, Jeddah, KSA, preschool, early childhood, حضانة, مونتيسوري, جدة",
```

---

### 2️⃣ OpenGraph siteName مختلف

```tsx
// src/app/[locale]/layout.tsx:29
siteName: "Planet of the Free Child Nursery",
```

يجب أن يكون متسقاً مع باقي الموقع.

---

### 3️⃣ themeColor في metadata (deprecated)

```tsx
// src/app/[locale]/layout.tsx:31
themeColor: "#2d5016",  // ← deprecated in Next.js 14+
```

⚠️ Warning يظهر عند Build - يجب نقله لـ `generateViewport`

---

## 📋 القسم الهيكلي | Structure Issues

### ✅ نقاط قوة الكود:
1. **بنية ممتازة**: components منظمة جيداً
2. **TypeScript كامل**: type safety في كل مكان
3. **Clean code**: بدون console.logs أو TODOs
4. **i18n implementation**: دعم العربية/الإنجليزية ممتاز
5. **Responsive design**: يعمل على جميع الأحجام
6. **No inline styles**: استخدام Tailwind بشكل صحيح
7. **Proper validation**: في forms
8. **Good naming**: متغيرات واضحة ومعبّرة

### ⚠️ نقاط التحسين:
1. **لا يوجد Error Boundary**: لا يوجد handling للـ runtime errors
2. **لا يوجد Loading states**: في أول تحميل للصفحة
3. **لا يوجد 404 page مخصص**: الـ default قبيح
4. **لا يوجد Analytics**: لا tracking للزيارات
5. **لا يوجد Monitoring**: لا reporting للـ errors

---

## 🎯 خطة العمل الموصى بها | Action Plan

### 🔴 عالي الأولوية (افعلها الآن):
1. ✅ إنشاء `.gitignore` file
2. ⚠️ ترقية Next.js و next-intl (بحذر - breaking changes)
3. 📞 تحديث رقم الهاتف والبريد في Footer
4. 📧 ربط Contact form بـ email service
5. 🔒 إضافة Security Headers

### 🟡 متوسطة الأولوية (خلال أسبوع):
6. 🤖 إضافة `robots.txt` و `sitemap.xml`
7. 🎨 إضافة `favicon` و OG images
8. 📱 إضافة روابط سوشيال ميديا حقيقية
9. ⚡ تحسين الـ fonts (next/font)
10. 🏷️ تحديث keywords و metadata

### 🟢 منخفضة الأولوية (تحسينات مستقبلية):
11. 📊 إضافة Google Analytics
12. 🐛 إضافة Error tracking (Sentry)
13. 🎭 إضافة Loading states أفضل
14. ♿ تحسين Accessibility (skip links, focus)
15. 🚀 تحسينات الأداء (استبدال Framer Motion)

---

## 📈 درجة الأمان الحالية

```
┌──────────────────────────┬─────────┬─────────┐
│ Category                 │ Score   │ Status  │
├──────────────────────────┼─────────┼─────────┤
│ Security                 │ 4/10    │ 🔴 Poor │
│ Code Quality             │ 9/10    │ 🟢 Excellent │
│ Performance              │ 7/10    │ 🟡 Good │
│ SEO                      │ 5/10    │ 🟡 Fair │
│ Accessibility            │ 6/10    │ 🟡 Fair │
│ Functionality            │ 7/10    │ 🟡 Good │
├──────────────────────────┼─────────┼─────────┤
│ OVERALL                  │ 6.3/10  │ 🟡 Needs Work │
└──────────────────────────┴─────────┴─────────┘
```

---

## 💰 تقدير التكلفة (إذا كنت تستأجر مطوّر)

| المهمة | الوقت المقدر | التكلفة (SAR) |
|--------|--------------|---------------|
| إصلاح الثغرات الأمنية | 8 ساعات | 2,400 |
| إصلاح معلومات الاتصال | 1 ساعة | 300 |
| ربط Contact form | 4 ساعات | 1,200 |
| إضافة SEO files | 3 ساعات | 900 |
| Security headers | 2 ساعات | 600 |
| تحسينات Performance | 6 ساعات | 1,800 |
| **المجموع** | **24 ساعة** | **7,200 ريال** |

*(بافتراض 300 ريال/ساعة - سعر السوق السعودي)*

---

## 📞 التوصية النهائية

**الموقع جيد تقنياً** لكنه **يحتاج تحديثات أمنية عاجلة** و**معلومات اتصال صحيحة** قبل النشر الرسمي.

**أولوية قصوى:**
1. إصلاح الثغرات الأمنية (ترقية Dependencies)
2. إضافة رقم هاتف حقيقي
3. ربط الـ Contact form

**بدون هذه الإصلاحات، الموقع:**
- ❌ عرضة للاختراق
- ❌ لا يستقبل رسائل العملاء
- ❌ يفقد فرص تسجيل محتملة

---

**تم إعداد هذا التقرير بواسطة:**  
Claude Fable 5 - AI Code Auditor  
19 أغسطس 2026

**للاستفسارات أو تطبيق الإصلاحات، استخدم هذا التقرير كدليل خطوة بخطوة.**
