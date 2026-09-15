# إعادة التصميم البصري الدافئ — خطة التنفيذ

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** إزالة النمط البصري "القالبي" (إيموجي كأيقونات، gradient hero متكرر، بادجات زجاجية، `rounded-2xl` على كل شيء) من كل صفحات الموقع العامة، واستبداله بتايبوجرافي كبير + صور حقيقية (أو حالة "قريبًا" مصممة بقصد) + لمسات Nano Banana محدودة، بدون المساس بالمحتوى/الترجمة/منطق الحجز.

**Architecture:** طبقة tokens/utilities مشتركة جديدة (بدون مكتبة تصميم خارجية) + مكوّن `PhotoFrame` مشترك يتعامل مع صورة حقيقية أو حالة "قريبًا"، ثم إعادة كتابة كل سكشن على حدة ليستخدم نفس الـtokens بتخطيط مختلف عن جاره. زرار الرد الآلي على واتساب — الوحيد اللي مش خاص بالزوار العاديين — يتنقل من الـHero العام إلى صفحة إدارة موجودة بالفعل (`public/manage/index.html`).

**Tech Stack:** Next.js 16 (App Router) + React 18 + Tailwind CSS 3 + `next-intl` (ar/en) + `lucide-react` للأيقونات + `clsx`. صفحة الإدارة الثابتة `public/manage/index.html` نظام منفصل (IIFE + وحدة `NS.*` من `public/assets/app.js`، بدون React).

**Spec:** [docs/superpowers/specs/2026-09-15-warm-visual-redesign-design.md](../specs/2026-09-15-warm-visual-redesign-design.md)

## Global Constraints

- **مفيش أي `style={{...}}` جديد بقيمة ديناميكية** في أي كومبوننت React جوه `src/components` — كل قيمة لازم تبقى class ثابت في Tailwind أو `globals.css`. القيم الديناميكية الوحيدة المسموحة: `animationDelay` على عناصر قليلة معروفة مسبقًا (مش لكل عنصر في loop).
- **مفيش تعديل على محتوى `<style>` inline** داخل أي ملف من `public/*/index.html` بدون تحديث hash الـCSP على السيرفر (`/etc/nginx/snippets/mk-csp-parts.conf`) بعدها مباشرة. لو محتاج CSS جديد في `public/manage/index.html`، يتضاف في `public/assets/app-admin.css` (ملف خارجي، مش محتاج تحديث hash).
- **كل مفتاح ترجمة جديد لازم يتضاف في `messages/ar.json` و`messages/en.json` معًا** — `npm run verify:i18n` بيفشل لو فيه فرق.
- **الموقع RTL عربي أساسي.** أي تخطيط `grid`/`flex` جديد غير متماثل لازم يُتفحص فعليًا في `dir="rtl"` (عربي) قبل ما يتقال "خلص"، مش يُفترض إنه هينعكس صح تلقائيًا.
- **لا حذف لأي منطق أعمال** (نموذج التواصل، الرد الآلي على واتساب، بيانات `site-facts`) — كل تعديل هنا بصري/بنائي بس.
- بعد كل Task فيه تعديل React: `npm run lint && npm run type-check` لازم ينجحوا قبل الـcommit.

---

## Task 1: Tokens وUtilities مشتركة

**Files:**
- Modify: `tailwind.config.ts`
- Modify: `src/app/globals.css:1-97`

**Interfaces:**
- Produces (تستخدمها كل الـTasks اللاحقة): classes `.pill-btn`, `.pill-btn--primary`, `.pill-btn--forest`, `.pill-btn--outline`, `.icon-tile`, `.icon-tile--lg`, `.surface-warm`, `.surface-forest`; utility class Tailwind جديدة `text-display`؛ CSS var جديد `--color-surface-warm`.

- [ ] **Step 1: تحقّق (test) قبل التعديل أن الأنماط القديمة لسه موجودة**

```bash
grep -c "slide-in-r\|slide-in-l" src/app/globals.css tailwind.config.ts
```

Expected: عدد أكبر من صفر (سنتأكد إننا فعلاً بنمسح حاجة موجودة).

- [ ] **Step 2: عدّل `tailwind.config.ts`** — أضف `fontSize.display` واحذف الـkeyframes/animations الميتة (`slideInRight`, `slideInLeft` غير مستخدمين في أي كومبوننت):

في `theme.extend`, بدّل الكتلة دي:

```ts
      animation: {
        "fade-in":    "fadeIn 0.6s ease-out forwards",
        "slide-up":   "slideUp 0.6s ease-out forwards",
        "slide-in-r": "slideInRight 0.6s ease-out forwards",
        "slide-in-l": "slideInLeft 0.6s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%":   { opacity: "0", transform: "translateX(30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInLeft: {
          "0%":   { opacity: "0", transform: "translateX(-30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
```

بـ:

```ts
      fontSize: {
        display: ["clamp(2.75rem, 6vw, 4.75rem)", { lineHeight: "1.05", fontWeight: "900" }],
      },
      animation: {
        "fade-in":  "fadeIn 0.6s ease-out forwards",
        "slide-up": "slideUp 0.6s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%":   { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
```

- [ ] **Step 3: عدّل `src/app/globals.css`** — أضف الـvar الجديد في `:root` (بعد `--color-earth`):

```css
:root {
  --color-primary: #2d5016;
  --color-primary-light: #5aa01e;
  --color-accent: #f5a623;
  --color-earth: #f3d9a4;
  --color-surface-warm: #f0f7e6;
}
```

- [ ] **Step 4: احذف الكلاس الميت `.leaf-decoration::before`** (مش مستخدم في أي كومبوننت):

```css
/* Leaf decoration */
.leaf-decoration::before {
  content: "🌿";
  margin-inline-end: 0.5rem;
}
```

امسح الكتلة دي بالكامل.

- [ ] **Step 5: نظّف مرجع `slide-in-r/l` من قاعدة الـopacity** — بدّل:

```css
.animate-fade-in,
.animate-slide-up,
.animate-slide-in-r,
.animate-slide-in-l {
  opacity: 0;
  animation-fill-mode: forwards;
}
```

بـ:

```css
.animate-fade-in,
.animate-slide-up {
  opacity: 0;
  animation-fill-mode: forwards;
}
```

- [ ] **Step 6: أضف الـutilities الجديدة** في آخر الملف (قبل قسم `.seo-article`، عشان ميتقاطعش مع أنماط المدونة):

```css
/* ---- Warm redesign: shared button/surface utilities ---- */
.pill-btn {
  @apply inline-flex items-center justify-center gap-2 rounded-full px-7 py-3.5 text-sm font-bold transition-transform duration-200;
}
.pill-btn:hover { transform: translateY(-1px); }
.pill-btn:active { transform: translateY(0) scale(0.98); }
.pill-btn--primary {
  background: var(--color-accent);
  color: #fff;
  box-shadow: 0 10px 24px rgba(245, 166, 35, 0.28);
}
.pill-btn--forest {
  background: var(--color-primary);
  color: #fff;
  box-shadow: 0 10px 24px rgba(45, 80, 22, 0.24);
}
.pill-btn--outline {
  background: transparent;
  border: 1.5px solid currentColor;
}

.icon-tile {
  @apply inline-flex shrink-0 items-center justify-center rounded-2xl;
  width: 2.75rem;
  height: 2.75rem;
  background: var(--color-surface-warm);
  color: var(--color-primary);
}
.icon-tile--lg {
  width: 3.5rem;
  height: 3.5rem;
}

.surface-warm { background: var(--color-surface-warm); }
.surface-forest {
  background: linear-gradient(135deg, #1a3009 0%, #2d5016 45%, #3d6b20 100%);
}
```

- [ ] **Step 7: تحقّق (test) إن الحذف والإضافة اتمّوا صح**

```bash
grep -c "slide-in-r\|slide-in-l" src/app/globals.css tailwind.config.ts
grep -c "pill-btn--primary\|icon-tile\|surface-warm" src/app/globals.css
npx tailwindcss -i src/app/globals.css -o /tmp/out.css --config tailwind.config.ts 2>&1 | tail -20
```

Expected: أول أمر يرجّع `0` لكل ملف، تاني أمر يرجّع عدد أكبر من صفر، وبناء Tailwind ينجح من غير أخطاء.

- [ ] **Step 8: Commit**

```bash
git add tailwind.config.ts src/app/globals.css
git commit -m "design: add shared pill-btn/icon-tile/surface tokens, drop dead animations"
```

---

## Task 2: مكوّن `PhotoFrame` المشترك

**Files:**
- Create: `src/components/ui/PhotoFrame.tsx`
- Modify: `messages/ar.json`, `messages/en.json` (أضف namespace `common`)

**Interfaces:**
- Produces: `export default function PhotoFrame(props: PhotoFrameProps)` — `{ src?: string; alt: string; comingSoonLabel: string; aspect?: "square" | "video" | "portrait"; className?: string; sizes?: string; priority?: boolean }`. تستخدمه Tasks 5 (Hero), 7 (About), 10 (Gallery), 13 (DailyLife).
- Consumes: `clsx` (موجود في `package.json` بالفعل)، `next/image`، أيقونة `ImageOff` من `lucide-react`.

- [ ] **Step 1: أضف `common.comingSoonPhoto` في الترجمتين**

في `messages/ar.json`، أضف مفتاح جديد على أعلى المستوى (بعد `"meta"`):

```json
  "common": {
    "comingSoonPhoto": "صور حقيقية قريبًا"
  },
```

في `messages/en.json`، بنفس المكان:

```json
  "common": {
    "comingSoonPhoto": "Real photos coming soon"
  },
```

- [ ] **Step 2: تحقّق (test) إن التوازي بين اللغتين سليم**

```bash
npm run verify:i18n
```

Expected: `i18n verified` بدون رسائل `missing`/`empty`.

- [ ] **Step 3: اكتب `src/components/ui/PhotoFrame.tsx`**

```tsx
import Image from "next/image";
import { ImageOff } from "lucide-react";
import clsx from "clsx";

type PhotoFrameProps = {
  src?: string;
  alt: string;
  comingSoonLabel: string;
  className?: string;
  aspect?: "square" | "video" | "portrait";
  sizes?: string;
  priority?: boolean;
};

const ASPECT_CLASS: Record<NonNullable<PhotoFrameProps["aspect"]>, string> = {
  square: "aspect-square",
  video: "aspect-video",
  portrait: "aspect-[3/4]",
};

export default function PhotoFrame({
  src,
  alt,
  comingSoonLabel,
  className,
  aspect = "square",
  sizes = "(min-width: 1024px) 33vw, 50vw",
  priority = false,
}: PhotoFrameProps) {
  return (
    <div
      className={clsx(
        "relative overflow-hidden rounded-3xl surface-warm",
        ASPECT_CLASS[aspect],
        className
      )}
    >
      {src ? (
        <Image
          src={src}
          alt={alt}
          fill
          sizes={sizes}
          priority={priority}
          className="object-cover"
        />
      ) : (
        <div className="flex h-full flex-col items-center justify-center gap-2 text-primary-600">
          <ImageOff size={28} className="opacity-60" aria-hidden="true" />
          <span className="text-sm font-semibold">{comingSoonLabel}</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: تحقّق (test) إن الكومبوننت بيبني وبيتفحص أنواعه**

```bash
npm run type-check
npm run lint
```

Expected: نجاح بدون أخطاء جديدة متعلقة بـ`PhotoFrame.tsx`.

- [ ] **Step 5: Commit**

```bash
git add src/components/ui/PhotoFrame.tsx messages/ar.json messages/en.json
git commit -m "feat: add shared PhotoFrame component with coming-soon fallback state"
```

---

## Task 3: Navbar

**Files:**
- Modify: `src/components/layout/Navbar.tsx:34-82`

**Interfaces:**
- Consumes: لا جديد.

- [ ] **Step 1: تحقّق (test) قبل التعديل — التاب بار حالياً بيستخدم `style={{...}}` ديناميكي**

```bash
grep -c "style={{" src/components/layout/Navbar.tsx
```

Expected: `2` (سطور 50 و75).

- [ ] **Step 2: احذف الـinline style الديناميكي في اللوجو والروابط**

بدّل (سطور 46-58):

```tsx
            <div
              className={`font-bold text-base leading-tight ${
                scrolled ? "text-primary-600" : "text-white"
              }`}
              style={{ color: scrolled ? "#2d5016" : undefined }}
            >
              {locale === "ar" ? "حضانة كوكب الطفل الحر" : "Planet of the Free Child"}
            </div>
            <div
              className={`text-xs ${scrolled ? "text-gray-500" : "text-green-100"}`}
            >
              {locale === "ar" ? "مونتيسوري جدة" : "Montessori Jeddah"}
            </div>
```

بـ (نفس المنطق، بدون `style`، الكلاس `text-primary-600` من `tailwind.config.ts` كفاية):

```tsx
            <div
              className={`font-bold text-base leading-tight ${
                scrolled ? "text-primary-600" : "text-white"
              }`}
            >
              {locale === "ar" ? "حضانة كوكب الطفل الحر" : "Planet of the Free Child"}
            </div>
            <div
              className={`text-xs ${scrolled ? "text-gray-500" : "text-green-100"}`}
            >
              {locale === "ar" ? "مونتيسوري جدة" : "Montessori Jeddah"}
            </div>
```

بدّل (سطور 64-81، إزالة الـ`style` الميت على روابط قائمة سطح المكتب):

```tsx
            <a
              key={key}
              href={getHref(key)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                scrolled
                  ? "text-gray-700 hover:text-primary-600 hover:bg-primary-50"
                  : "text-white/90 hover:text-white hover:bg-white/10"
              }`}
              style={
                scrolled
                  ? { "--tw-text-opacity": "1" } as React.CSSProperties
                  : undefined
              }
            >
              {t(key)}
            </a>
```

بـ:

```tsx
            <a
              key={key}
              href={getHref(key)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                scrolled
                  ? "text-gray-700 hover:text-primary-600 hover:bg-primary-50"
                  : "text-white/90 hover:text-white hover:bg-white/10"
              }`}
            >
              {t(key)}
            </a>
```

- [ ] **Step 3: وحّد زراري "سجّل الآن" (سطر ~115-121 وسطر ~158-165) على `.pill-btn`**

بدّل زرار سطح المكتب:

```tsx
          <a
            href={`/${locale}#contact`}
            className="hidden md:flex items-center px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:scale-105 shadow-md"
            style={{ background: "#2d5016" }}
          >
            {locale === "ar" ? "سجّل الآن" : "Enroll Now"}
          </a>
```

بـ:

```tsx
          <a
            href={`/${locale}#contact`}
            className="pill-btn pill-btn--forest hidden md:flex !px-5 !py-2.5 text-sm"
          >
            {locale === "ar" ? "سجّل الآن" : "Enroll Now"}
          </a>
```

وزرار القائمة الموبايل (نفس النمط):

```tsx
              <a
                href={`/${locale}#contact`}
                className="px-5 py-2 rounded-xl text-sm font-semibold text-white"
                style={{ background: "#2d5016" }}
                onClick={() => setOpen(false)}
              >
                {locale === "ar" ? "سجّل الآن" : "Enroll Now"}
              </a>
```

بـ:

```tsx
              <a
                href={`/${locale}#contact`}
                className="pill-btn pill-btn--forest !px-5 !py-2.5 text-sm"
                onClick={() => setOpen(false)}
              >
                {locale === "ar" ? "سجّل الآن" : "Enroll Now"}
              </a>
```

- [ ] **Step 4: تحقّق (test) إن كل الـ`style={{`الديناميكي اتشال**

```bash
grep -c "style={{" src/components/layout/Navbar.tsx
```

Expected: `0`.

- [ ] **Step 5: تحقّق build/lint**

```bash
npm run lint && npm run type-check
```

Expected: نجاح.

- [ ] **Step 6: Commit**

```bash
git add src/components/layout/Navbar.tsx
git commit -m "design: unify navbar CTA on pill-btn, drop dynamic inline styles"
```

---

## Task 4: Footer

**Files:**
- Modify: `src/components/layout/Footer.tsx:90-109`

**Interfaces:**
- Consumes: `MapPin`, `Phone`, `Mail`, `Instagram`, `Facebook`, `MessageCircle` من `lucide-react` (كلها موجودة في المكتبة — تم التحقق).

- [ ] **Step 1: تحقّق (test) قبل التعديل — الفوتر فيه إيموجي كأيقونات**

```bash
grep -c "📍\|📞\|✉️\|📷\|👍\|💬" src/components/layout/Footer.tsx
```

Expected: `6`.

- [ ] **Step 2: أضف الاستيراد**

بدّل سطر الاستيراد الأول:

```tsx
import { LogIn } from "lucide-react";
```

بـ:

```tsx
import { LogIn, MapPin, Phone, Mail, Instagram, Facebook, MessageCircle } from "lucide-react";
```

- [ ] **Step 3: بدّل قائمة التواصل** (سطور 89-93):

```tsx
          <ul className="space-y-2 text-sm text-gray-400">
            <li>📍 {locale === "ar" ? siteFacts.address.ar : siteFacts.address.en}</li>
            <li>📞 {siteFacts.contact.phoneDisplay}</li>
            <li>✉️ {siteFacts.contact.email}</li>
          </ul>
```

بـ:

```tsx
          <ul className="space-y-2 text-sm text-gray-400">
            <li className="flex items-start gap-2">
              <MapPin size={16} className="mt-0.5 shrink-0" />
              <span>{locale === "ar" ? siteFacts.address.ar : siteFacts.address.en}</span>
            </li>
            <li className="flex items-center gap-2">
              <Phone size={16} className="shrink-0" />
              <span>{siteFacts.contact.phoneDisplay}</span>
            </li>
            <li className="flex items-center gap-2">
              <Mail size={16} className="shrink-0" />
              <span>{siteFacts.contact.email}</span>
            </li>
          </ul>
```

- [ ] **Step 4: بدّل أيقونات السوشيال** (سطور 95-110):

```tsx
          <div className="flex gap-3 mt-5">
            {[
              { label: "Instagram", icon: "📷", href: siteFacts.contact.instagram },
              { label: "Facebook", icon: "👍", href: "https://www.facebook.com/p/Montessori-nursery-100063063920027/" },
              { label: "WhatsApp", icon: "💬", href: siteFacts.contact.whatsapp },
            ].map(({ label, icon, href }) => (
              <a
                key={label}
                href={href}
                aria-label={label}
                className="w-9 h-9 rounded-lg bg-gray-800 hover:bg-primary-600 flex items-center justify-center text-sm transition-colors"
              >
                {icon}
              </a>
            ))}
          </div>
```

بـ:

```tsx
          <div className="flex gap-3 mt-5">
            {[
              { label: "Instagram", Icon: Instagram, href: siteFacts.contact.instagram },
              { label: "Facebook", Icon: Facebook, href: "https://www.facebook.com/p/Montessori-nursery-100063063920027/" },
              { label: "WhatsApp", Icon: MessageCircle, href: siteFacts.contact.whatsapp },
            ].map(({ label, Icon, href }) => (
              <a
                key={label}
                href={href}
                aria-label={label}
                className="w-9 h-9 rounded-lg bg-gray-800 hover:bg-primary-600 flex items-center justify-center transition-colors"
              >
                <Icon size={16} />
              </a>
            ))}
          </div>
```

- [ ] **Step 5: تحقّق (test)**

```bash
grep -c "📍\|📞\|✉️\|📷\|👍\|💬" src/components/layout/Footer.tsx
npm run lint && npm run type-check
```

Expected: أول أمر `0`، تاني أمر ينجح.

- [ ] **Step 6: Commit**

```bash
git add src/components/layout/Footer.tsx
git commit -m "design: replace footer emoji icons with lucide icons"
```

---

## Task 5: HeroSection

**Files:**
- Modify: `src/components/sections/HeroSection.tsx` (rewrite كامل)
- Modify: `messages/ar.json`, `messages/en.json` (`hero` namespace)

**Interfaces:**
- Consumes: `PhotoFrame` (Task 2)، `.pill-btn`/`.surface-forest` (Task 1).
- Produces: `hero.photoAlt` مفتاح ترجمة جديد يُستخدم هنا فقط.
- ⚠️ هذا الـTask بيشيل UI الرد الآلي على واتساب من الصفحة العامة. الـAPI (`/api/whatsapp-auto-reply`) **يفضل زي ما هو** — Task 6 هيضيفله واجهة تانية في `public/manage/index.html`.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "🌿|🍃|🌱|animate-pulse|whatsapp-auto-reply" src/components/sections/HeroSection.tsx
```

Expected: عدد أكبر من صفر (الإيموجي العائمة + استدعاء الـAPI موجودين).

- [ ] **Step 2: بدّل `hero` namespace في `messages/ar.json`** — احذف `autoReply` بالكامل وأضف `photoAlt`:

قبل:

```json
  "hero": {
    "badge": "حضانة مونتيسوري معتمدة",
    "headline": "نُشعل شغف التعلّم منذ البداية",
    "subheadline": "في كوكب الطفل الحر، نؤمن بأن كل طفل يحمل بذرة عبقرية. نهجنا المونتيسوري يُنمّيها بحرية وإبداع وحب.",
    "cta": "اكتشف عالمنا",
    "ctaSecondary": "تواصل معنا",
    "autoReply": {
      "loading": "جاري تحميل الحالة...",
      "start": "تشغيل الرد الآلي",
      "stop": "إيقاف الرد الآلي",
      "on": "الرد الآلي مفعّل الآن",
      "off": "الرد الآلي متوقف الآن",
      "error": "تعذّر تحديث الحالة المركزية"
    },
```

بعد:

```json
  "hero": {
    "badge": "حضانة مونتيسوري معتمدة",
    "headline": "نُشعل شغف التعلّم منذ البداية",
    "subheadline": "في كوكب الطفل الحر، نؤمن بأن كل طفل يحمل بذرة عبقرية. نهجنا المونتيسوري يُنمّيها بحرية وإبداع وحب.",
    "cta": "اكتشف عالمنا",
    "ctaSecondary": "تواصل معنا",
    "photoAlt": "أطفال يستكشفون بيئة مونتيسوري في كوكب الطفل الحر",
```

(باقي مفاتيح `hero` زي `stats` تفضل زي ما هي — بس شيل `autoReply` وضيف `photoAlt` جنب `ctaSecondary`).

نفس التعديل بالظبط في `messages/en.json`، مع `"photoAlt": "Children exploring a Montessori environment at Planet of the Free Child"`.

- [ ] **Step 3: تحقّق (test) توازي الترجمة**

```bash
npm run verify:i18n
```

Expected: نجاح بدون `missing`.

- [ ] **Step 4: أعد كتابة `src/components/sections/HeroSection.tsx` بالكامل:**

```tsx
import { useTranslations, useLocale } from "next-intl";
import PhotoFrame from "@/components/ui/PhotoFrame";

const stats = [
  { key: "years", value: "+١٠", valueEn: "10+" },
  { key: "children", value: "+٥٠٠", valueEn: "500+" },
  { key: "programs", value: "٤", valueEn: "4" },
  { key: "teachers", value: "+٢٠", valueEn: "20+" },
];

export default function HeroSection() {
  const t = useTranslations("hero");
  const common = useTranslations("common");
  const locale = useLocale();
  const isAr = locale === "ar";
  const secondaryHref = isAr ? "/wa/" : "#contact";

  return (
    <section
      id="home"
      className="surface-forest relative overflow-hidden pb-20 pt-28 md:pb-28 md:pt-36"
    >
      <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-12 px-4 md:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
        <div>
          <span className="badge border border-white/20 bg-white/10 text-white">
            {t("badge")}
          </span>

          <h1 className="mt-6 text-display text-white">{t("headline")}</h1>

          <p className="mt-6 max-w-xl text-lg leading-relaxed text-white/85 md:text-xl">
            {t("subheadline")}
          </p>

          <div
            className={`mt-9 flex flex-wrap gap-4 ${
              isAr ? "flex-row-reverse justify-end" : ""
            }`}
          >
            <a href="#programs" className="pill-btn pill-btn--primary">
              {t("cta")}
            </a>
            <a href={secondaryHref} className="pill-btn pill-btn--outline text-white">
              {t("ctaSecondary")}
            </a>
          </div>

          <dl className="mt-14 grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
            {stats.map(({ key, value, valueEn }) => (
              <div key={key}>
                <dt className="sr-only">{t(`stats.${key}`)}</dt>
                <dd className="text-3xl font-black text-white">
                  {isAr ? value : valueEn}
                </dd>
                <div className="mt-1 text-xs text-white/70">{t(`stats.${key}`)}</div>
              </div>
            ))}
          </dl>
        </div>

        <PhotoFrame
          alt={t("photoAlt")}
          comingSoonLabel={common("comingSoonPhoto")}
          aspect="portrait"
          priority
          className="w-full max-w-md justify-self-center lg:justify-self-end"
        />
      </div>
    </section>
  );
}
```

- [ ] **Step 5: تحقّق (test) إن كل أثر للرد الآلي والإيموجي العائمة اتشال من الملف**

```bash
grep -cE "🌿|🍃|🌱|animate-pulse|whatsapp-auto-reply|autoReply" src/components/sections/HeroSection.tsx
```

Expected: `0`.

- [ ] **Step 6: build/lint**

```bash
npm run lint && npm run type-check
```

Expected: نجاح (لو فيه استخدام آخر لمفاتيح `hero.autoReply` في الكود، الـlint/type-check هيوريه — تأكد مفيش قبل الكوميت).

- [ ] **Step 7: Commit**

```bash
git add src/components/sections/HeroSection.tsx messages/ar.json messages/en.json
git commit -m "design: rebuild Hero with display typography and PhotoFrame, drop admin toggle from public page"
```

---

## Task 6: نقل زرار الرد الآلي على واتساب لصفحة الإدارة

**Files:**
- Modify: `public/assets/app-admin.css` (أضف قواعد جديدة، ملف خارجي — **لا يحتاج تحديث hash CSP**)
- Modify: `public/manage/index.html:192-223`

**Interfaces:**
- Consumes: `/api/whatsapp-auto-reply` (GET/POST) — نفس الـAPI اللي كان الـHero بيستخدمه، **بدون تعديل عليه**.
- Consumes: أنماط `.card`, `.card--pad`, `.btn`, `.btn--primary`, `.btn--soft` الموجودة بالفعل في `app-admin.css`.

- [ ] **Step 1: تحقّق (test) قبل التعديل — مفيش إعدادات رد آلي في صفحة الإدارة حاليًا**

```bash
grep -c "whatsapp-auto-reply" public/manage/index.html
```

Expected: `0`.

- [ ] **Step 2: أضف كلاسات CSS جديدة في نهاية `public/assets/app-admin.css`**

```css
.settings-card{margin-bottom:18px}
.settings-card .settings-row{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}
.settings-card .settings-copy{min-width:0}
.settings-card .settings-copy h3{margin:0 0 4px;font-size:1.05rem;color:var(--forest)}
.settings-card .settings-copy p{margin:0;color:var(--muted);font-size:.88rem}
```

- [ ] **Step 3: بدّل رقم نسخة `app-admin.css` في `public/manage/index.html`** (سطر 129) عشان يتجدد الكاش:

```html
<link rel="stylesheet" href="/assets/app-admin.css?v=11"/>
```

يبقى:

```html
<link rel="stylesheet" href="/assets/app-admin.css?v=12"/>
```

- [ ] **Step 4: أضف كارت الإعدادات في `render()`** — بدّل (سطور 209-223):

```js
function render(){
  app.innerHTML=
    NS.appbar({sub:'طلبات الربط', nav:NS.adminNav('manage')})+
    '<main class="app-main app-narrow">'+
      '<div class="page-head between" style="align-items:flex-end">'+
        '<div><h1>طلبات الربط</h1><div class="sub">'+(S.manager?NS.esc(S.manager):'مراجعة أولياء الأمور')+'</div></div>'+
        '<span class="count-pill" id="count"></span>'+
      '</div>'+
      '<div class="reqs-list" id="list"></div>'+
    '</main>'+
    '<footer style="text-align:center;color:var(--muted);font-size:.82rem;padding:20px">روضة كوكب الطفل الحر · جدة</footer>';
  NS.wireLogout('mt');
  updateCount();
  renderList();
}
```

بـ:

```js
function render(){
  app.innerHTML=
    NS.appbar({sub:'طلبات الربط', nav:NS.adminNav('manage')})+
    '<main class="app-main app-narrow">'+
      '<div class="page-head between" style="align-items:flex-end">'+
        '<div><h1>طلبات الربط</h1><div class="sub">'+(S.manager?NS.esc(S.manager):'مراجعة أولياء الأمور')+'</div></div>'+
        '<span class="count-pill" id="count"></span>'+
      '</div>'+
      '<div class="card card--pad settings-card" id="wa-settings"></div>'+
      '<div class="reqs-list" id="list"></div>'+
    '</main>'+
    '<footer style="text-align:center;color:var(--muted);font-size:.82rem;padding:20px">روضة كوكب الطفل الحر · جدة</footer>';
  NS.wireLogout('mt');
  updateCount();
  renderList();
  renderWaSettings();
}

/* ---------- WhatsApp auto-reply toggle (moved off the public Hero) ---------- */
var WA={enabled:null};

function renderWaSettings(){
  var el=document.getElementById('wa-settings');
  if(!el) return;
  waPaint(el);
  fetch('/api/whatsapp-auto-reply',{cache:'no-store'})
    .then(function(r){ if(!r.ok) throw new Error('http '+r.status); return r.json(); })
    .then(function(d){ WA.enabled=!!d.enabled; waPaint(el); })
    .catch(function(){ WA.enabled=null; waPaint(el,true); });
}

function waPaint(el, error){
  var loading = WA.enabled===null && !error;
  var statusText = error
    ? 'تعذّر تحديث الحالة'
    : loading
      ? 'جاري تحميل الحالة...'
      : (WA.enabled ? 'الرد الآلي مفعّل الآن' : 'الرد الآلي متوقف الآن');
  var btnLabel = WA.enabled ? 'إيقاف الرد الآلي' : 'تشغيل الرد الآلي';
  var btnClass = WA.enabled ? 'btn btn--primary' : 'btn btn--soft';
  el.innerHTML=
    '<div class="settings-row">'+
      '<div class="settings-copy"><h3>الرد الآلي على واتساب</h3><p>'+statusText+'</p></div>'+
      '<button class="'+btnClass+'" id="wa-toggle" '+(loading?'disabled':'')+'>'+
        I('bolt')+' '+btnLabel+
      '</button>'+
    '</div>';
  var btn=document.getElementById('wa-toggle');
  if(btn) btn.addEventListener('click', waToggle);
}

function waToggle(){
  var el=document.getElementById('wa-settings');
  if(!el || WA.enabled===null) return;
  var btn=document.getElementById('wa-toggle');
  if(btn){ btn.classList.add('is-loading'); btn.disabled=true; }
  fetch('/api/whatsapp-auto-reply',{
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({enabled:!WA.enabled})
  })
    .then(function(r){ if(!r.ok) throw new Error('http '+r.status); return r.json(); })
    .then(function(d){ WA.enabled=!!d.enabled; waPaint(el); NS.toast('تم التحديث','ok'); })
    .catch(function(){ waPaint(el,true); NS.toast('تعذّر تحديث الحالة','err'); });
}
```

> ملحوظة: `I('bolt')` بيستخدم نفس دالة الأيقونات `NS.icon` المستخدمة في باقي الملف (`I('checkCircle')`, `I('wifi')`...). لو أيقونة `bolt` مش موجودة في مجموعة `NS.icon`، استخدم أي أيقونة موجودة بالفعل في `public/assets/app.js` (مثلاً `I('refresh')`) بدل ما تضيف SVG جديد.

- [ ] **Step 5: تحقّق (test) إن الكارت اتضاف وبيستخدم الـAPI الصح**

```bash
grep -c "whatsapp-auto-reply" public/manage/index.html
grep -c "settings-card" public/assets/app-admin.css
```

Expected: أول أمر `2` على الأقل (GET وPOST)، تاني أمر أكبر من صفر.

- [ ] **Step 6: تحقّق يدوي في المتصفح** — شغّل `npm run dev`، افتح `/manage/index.html` بعد تسجيل دخول مدير تجريبي (أو استخدم بيئة staging)، اتأكد إن الكارت ظاهر، الزرار بيبدّل الحالة، ومفيش خطأ CSP في الـconsole (`read_console_messages` أو أدوات المتصفح).

- [ ] **Step 7: Commit**

```bash
git add public/assets/app-admin.css public/manage/index.html
git commit -m "feat: move WhatsApp auto-reply toggle from public Hero to manager dashboard"
```

---

## Task 7: AboutSection

**Files:**
- Modify: `src/components/sections/AboutSection.tsx` (rewrite كامل)

**Interfaces:**
- Consumes: `PhotoFrame` (Task 2)، `.icon-tile` (Task 1)، أيقونات `HandHeart`, `Feather`, `Heart`, `Sparkles` من `lucide-react`.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "🤝|🕊️|❤️|⭐|🌿|🏫|✓ " src/components/sections/AboutSection.tsx
```

Expected: عدد أكبر من صفر.

- [ ] **Step 2: أعد كتابة `src/components/sections/AboutSection.tsx` بالكامل:**

```tsx
import { useTranslations } from "next-intl";
import { HandHeart, Feather, Heart, Sparkles, CheckCircle2 } from "lucide-react";
import PhotoFrame from "@/components/ui/PhotoFrame";

const valueIcons = [HandHeart, Feather, Heart, Sparkles];
const valueKeys = ["respect", "freedom", "love", "excellence"] as const;

export default function AboutSection() {
  const t = useTranslations("about");
  const common = useTranslations("common");

  return (
    <section id="about" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        <span className="badge surface-warm text-primary-700">{t("badge")}</span>

        <h2 className="section-title mt-4 text-gray-900">{t("headline")}</h2>

        <div className="mt-12 grid items-center gap-12 md:grid-cols-2">
          <div className="space-y-5">
            <p className="text-gray-600 leading-relaxed text-lg">{t("body1")}</p>
            <p className="text-gray-600 leading-relaxed text-lg">{t("body2")}</p>

            <blockquote className="border-s-4 border-primary-700 ps-5 py-2 italic text-primary-700 text-lg font-medium">
              {'"The greatest gifts we can give our children are the roots of responsibility and the wings of independence."'}
              <footer className="text-sm font-normal text-gray-500 mt-1 not-italic">
                — Maria Montessori
              </footer>
            </blockquote>

            <ul className="grid grid-cols-2 gap-3 pt-2">
              {[
                t("features.montessori"),
                t("features.bilingual"),
                t("features.ages"),
                t("features.established"),
              ].map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-gray-700">
                  <CheckCircle2 size={16} className="shrink-0 text-primary-600" />
                  {f}
                </li>
              ))}
            </ul>
          </div>

          <PhotoFrame
            alt={t("photoAlt")}
            comingSoonLabel={common("comingSoonPhoto")}
            aspect="video"
            className="shadow-lg"
          />
        </div>

        <div className="mt-16">
          <h3 className="text-2xl font-bold text-center text-gray-800 mb-8">
            {t("values.title")}
          </h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {valueKeys.map((key, i) => {
              const Icon = valueIcons[i];
              return (
                <div
                  key={key}
                  className="card-hover p-6 rounded-2xl border border-gray-100 bg-gray-50 text-center"
                >
                  <div className="icon-tile icon-tile--lg mx-auto mb-3">
                    <Icon size={24} />
                  </div>
                  <h4 className="font-bold text-lg mb-2 text-primary-700">
                    {t(`values.${key}.title`)}
                  </h4>
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {t(`values.${key}.desc`)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
```

> الكارت الأخضر القديم ("Bada'a Early Childhood Center" + إحداثيات) اتشال بالكامل واتبدّل بـ`PhotoFrame` + قائمة مميزات — نفس المعلومات (`features.*`) لسه موجودة كنص، بس من غير كارت gradient منفصل. لو محتاج تفاصيل الإحداثيات تفضل ظاهرة في مكان تاني، أضفها في `ContactSection` (فيها خريطة بالفعل) مش هنا.

- [ ] **Step 3: أضف `about.photoAlt` في الترجمتين** (بجوار `about.badge`):

`messages/ar.json`: `"photoAlt": "أطفال يتعلمون في بيئة مونتيسوري بكوكب الطفل الحر",`
`messages/en.json`: `"photoAlt": "Children learning in a Montessori environment at Planet of the Free Child",`

- [ ] **Step 4: تحقّق (test)**

```bash
grep -cE "🤝|🕊️|❤️|⭐|🌿|🏫" src/components/sections/AboutSection.tsx
npm run verify:i18n
npm run lint && npm run type-check
```

Expected: أول أمر `0`، الباقي ينجح.

- [ ] **Step 5: Commit**

```bash
git add src/components/sections/AboutSection.tsx messages/ar.json messages/en.json
git commit -m "design: rebuild About with lucide icons and PhotoFrame, drop gradient location card"
```

---

## Task 8: RolesSection

**Files:**
- Modify: `src/components/sections/RolesSection.tsx` (rewrite كامل)

**Interfaces:**
- Consumes: `.pill-btn`, `.icon-tile` (Task 1)، أيقونات `UserCog`, `GraduationCap`, `Handshake`, `Award`, `ClipboardList`, `Briefcase` من `lucide-react`.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "👩‍💼|👩‍🏫|🤝|🎓|📋|💼|🌱|✦" src/components/sections/RolesSection.tsx
```

Expected: عدد أكبر من صفر.

- [ ] **Step 2: أعد كتابة `src/components/sections/RolesSection.tsx` بالكامل:**

```tsx
import { useTranslations, useLocale } from "next-intl";
import { UserCog, GraduationCap, Handshake, Award, ClipboardList, Briefcase } from "lucide-react";

type RoleKey = "director" | "lead_teacher" | "assistant" | "specialist" | "coordinator" | "admin";

const roleIcons: Record<RoleKey, typeof UserCog> = {
  director: UserCog,
  lead_teacher: GraduationCap,
  assistant: Handshake,
  specialist: Award,
  coordinator: ClipboardList,
  admin: Briefcase,
};

const roleKeys: RoleKey[] = ["director", "lead_teacher", "assistant", "specialist", "coordinator", "admin"];

export default function RolesSection() {
  const t = useTranslations("roles");
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <section id="team" className="section-padding bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <span className="badge surface-warm text-primary-700">{t("badge")}</span>

        <h2 className="section-title mt-4 text-center text-gray-900">{t("title")}</h2>
        <p className="text-center text-gray-500 text-lg max-w-2xl mx-auto mb-14 mt-4">
          {t("subtitle")}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {roleKeys.map((key) => {
            const Icon = roleIcons[key];
            return (
              <div
                key={key}
                className="card-hover flex items-start gap-4 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm"
              >
                <div className="icon-tile icon-tile--lg">
                  <Icon size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-primary-700">
                    {t(`items.${key}.title`)}
                  </h3>
                  <p
                    className="mt-1 text-gray-500 text-sm leading-relaxed"
                    dir={isAr ? "rtl" : "ltr"}
                  >
                    {t(`items.${key}.desc`)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="surface-forest mt-16 flex flex-col items-center justify-between gap-6 rounded-3xl px-8 py-10 shadow-lg md:flex-row">
          <div className="text-center md:text-start">
            <p className="text-white/70 text-sm font-medium uppercase tracking-widest mb-2">
              {t("hiring.eyebrow")}
            </p>
            <h3 className="text-2xl md:text-3xl font-black text-white">
              {t("hiring.title")}
            </h3>
            <p className="text-white/80 mt-2 text-sm max-w-md">{t("hiring.body")}</p>
          </div>
          <a href="#contact" className="pill-btn pill-btn--primary shrink-0 whitespace-nowrap">
            {t("hiring.cta")}
          </a>
        </div>
      </div>
    </section>
  );
}
```

> بند "We Are Hiring" كان نص إنجليزي مكتوب مباشرة جوه الكومبوننت (مش عبر `t()`) — ده تسرّب لمحتوى غير مُدار عبر i18n. نقلناه لمفاتيح `roles.hiring.eyebrow/title/body/cta` بدل ما نسيبه hardcoded.

- [ ] **Step 3: أضف `roles.hiring.*` في الترجمتين** (namespace `roles`، بعد `subtitle`):

`messages/ar.json`:
```json
    "hiring": {
      "eyebrow": "انضم لفريقنا",
      "title": "نبحث عن معلمين شغوفين بالتعليم",
      "body": "لو بتحب الأطفال وتؤمن بفلسفة مونتيسوري، يسعدنا نتعرف عليك. تواصل معنا وكن جزءًا من عائلتنا المتنامية في جدة.",
      "cta": "قدّم الآن"
    }
```

`messages/en.json`:
```json
    "hiring": {
      "eyebrow": "Join Our Team",
      "title": "We're Hiring Passionate Educators",
      "body": "If you love children and believe in the Montessori philosophy, we'd love to meet you. Reach out and be part of our growing family in Jeddah.",
      "cta": "Apply Now"
    }
```

- [ ] **Step 4: تحقّق (test)**

```bash
grep -cE "👩‍💼|👩‍🏫|🤝|🎓|📋|💼|✦" src/components/sections/RolesSection.tsx
npm run verify:i18n
npm run lint && npm run type-check
```

Expected: أول أمر `0`، الباقي ينجح.

- [ ] **Step 5: Commit**

```bash
git add src/components/sections/RolesSection.tsx messages/ar.json messages/en.json
git commit -m "design: rebuild Roles with icon-tile list layout, move hardcoded hiring copy into i18n"
```

---

## Task 9: MethodologySection

**Files:**
- Modify: `src/components/sections/MethodologySection.tsx` (rewrite كامل)

**Interfaces:**
- Consumes: `.surface-warm` (Task 1). تخطيط التايم لاين الأساسي يفضل زي ما هو (مش قالبي — كروت متكررة مطابقة)، التعديل بس تنظيف الإيموجي والـinline styles الديناميكية.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "🎓|🌺" src/components/sections/MethodologySection.tsx
```

Expected: `2`.

- [ ] **Step 2: أعد كتابة `src/components/sections/MethodologySection.tsx` بالكامل:**

```tsx
import { useTranslations } from "next-intl";

const stepIndices = [0, 1, 2, 3, 4] as const;

const stepAccentClass = [
  "bg-primary-700",
  "bg-primary-600",
  "bg-primary-500",
  "bg-accent",
  "bg-accent-dark",
] as const;

export default function MethodologySection() {
  const t = useTranslations("methodology");

  return (
    <section id="methodology" className="section-padding surface-warm">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <span className="badge bg-white text-primary-700">{t("badge")}</span>
          <h2 className="section-title mt-4 text-gray-900">{t("title")}</h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed mt-4">
            {t("subtitle")}
          </p>
        </div>

        <div className="relative">
          <div
            className="hidden lg:block absolute h-0.5 bg-primary-300 opacity-40"
            style={{ top: "2.5rem", insetInline: "8rem" }}
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 lg:gap-4 relative">
            {stepIndices.map((i) => (
              <div key={i} className="relative flex flex-col items-center text-center lg:px-2">
                <div
                  className={`relative z-10 mb-5 flex h-20 w-20 items-center justify-center rounded-full border-4 border-white shadow-lg ${stepAccentClass[i]}`}
                >
                  <span className="text-white text-2xl font-black">
                    {t(`steps.${i}.step`)}
                  </span>
                </div>

                {i < 4 && (
                  <div
                    className={`lg:hidden absolute top-20 left-1/2 h-8 w-0.5 -translate-x-1/2 opacity-40 ${stepAccentClass[i + 1]}`}
                    aria-hidden="true"
                  />
                )}

                <h3 className="font-bold text-base mb-2 text-primary-700">
                  {t(`steps.${i}.title`)}
                </h3>
                <p className="text-gray-500 text-sm leading-relaxed">
                  {t(`steps.${i}.desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-16 max-w-3xl mx-auto">
          <blockquote className="relative rounded-3xl border-s-4 border-primary-700 bg-white p-8 shadow-md">
            <span
              className="absolute top-4 end-6 text-8xl font-serif leading-none text-primary-700 opacity-10 select-none"
              aria-hidden="true"
            >
              &ldquo;
            </span>
            <p className="relative z-10 text-xl md:text-2xl italic font-medium leading-relaxed mb-5 text-primary-700">
              &ldquo;{t("quote.text")}&rdquo;
            </p>
            <footer className="font-semibold text-gray-700 not-italic">
              {t("quote.author")}
            </footer>
          </blockquote>
        </div>
      </div>
    </section>
  );
}
```

> `style={{ top: "2.5rem", insetInline: "8rem" }}` سطر ثابت (مش قيمة ديناميكية متغيرة بحسب data) — مسموح مؤقتًا لأنه أبسط من `arbitrary value` في Tailwind لخط أفقي بعرض متغير حسب المسافة الداخلية؛ لو الـCSP هنا برضه هيرفضه لأنه inline على عنصر React (مش نفس قيد الـ`<style>` بتاع صفحات `public/*`)، بدّله بكلاس Tailwind: `className="hidden lg:block absolute top-10 inset-x-32 h-0.5 bg-primary-300 opacity-40"` واحذف الـ`style` بالكامل. **افحص الاثنين وخلي اللي بيمر من `npm run build` بدون تحذير.**

- [ ] **Step 3: تحقّق (test)**

```bash
grep -cE "🎓|🌺" src/components/sections/MethodologySection.tsx
npm run lint && npm run type-check
```

Expected: أول أمر `0`، الباقي ينجح.

- [ ] **Step 4: Commit**

```bash
git add src/components/sections/MethodologySection.tsx
git commit -m "design: clean up Methodology emoji/inline styles, keep timeline layout"
```

---

## Task 10: GallerySection — الإصلاح الأهم في الـspec

**Files:**
- Modify: `src/components/sections/GallerySection.tsx` (rewrite كامل)
- Modify: `messages/ar.json`, `messages/en.json` (`gallery.tiles` تحتاج مسارات صور اختيارية)

**Interfaces:**
- Consumes: `PhotoFrame` (Task 2).
- ⚠️ لسه مفيش صور حقيقية معتمدة في `public/` (اتفحص في مرحلة الـspec). التصميم هنا لازم يشتغل صح في حالة "كله قريبًا" **وبرضه** يشتغل صح لما تتوفر صورة حقيقية — من غير أي تعديل إضافي على الكومبوننت وقتها، بس تحديث مصفوفة `TILES` بمسار `src`.

- [ ] **Step 1: تحقّق (test) قبل التعديل — تايلز الجاليري كلها gradient+إيموجي، مفيش صورة حقيقية واحدة**

```bash
grep -c "gradient" src/components/sections/GallerySection.tsx
grep -c "next/image\|PhotoFrame" src/components/sections/GallerySection.tsx
```

Expected: أول أمر `8` (تايلز)، تاني أمر `0`.

- [ ] **Step 2: أعد كتابة `src/components/sections/GallerySection.tsx` بالكامل:**

```tsx
"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import PhotoFrame from "@/components/ui/PhotoFrame";

const CATEGORY_KEYS = ["all", "activities", "environment", "events", "learning"] as const;
type CategoryKey = (typeof CATEGORY_KEYS)[number];

interface GalleryTile {
  id: number;
  category: Exclude<CategoryKey, "all">;
  labelKey: string;
  /** يتضاف لما المالك يوافق على صورة حقيقية — لحد ذلك تفضل undefined فتظهر حالة "قريبًا". */
  src?: string;
}

const TILES: GalleryTile[] = [
  { id: 1, category: "activities", labelKey: "artCraft" },
  { id: 2, category: "environment", labelKey: "classroom" },
  { id: 3, category: "learning", labelKey: "reading" },
  { id: 4, category: "events", labelKey: "celebration" },
  { id: 5, category: "activities", labelKey: "garden" },
  { id: 6, category: "learning", labelKey: "maths" },
  { id: 7, category: "environment", labelKey: "nature" },
  { id: 8, category: "events", labelKey: "yearEnd" },
];

export default function GallerySection() {
  const t = useTranslations("gallery");
  const common = useTranslations("common");
  const locale = useLocale();
  const isAr = locale === "ar";

  const [activeCategory, setActiveCategory] = useState<CategoryKey>("all");

  const visibleTiles =
    activeCategory === "all" ? TILES : TILES.filter((tile) => tile.category === activeCategory);

  return (
    <section id="gallery" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        <span className="badge surface-warm text-primary-700">{t("badge")}</span>

        <h2 className="section-title mt-4 text-center text-gray-900">{t("title")}</h2>
        <p className="text-center text-gray-500 text-lg max-w-xl mx-auto mb-10 mt-4">
          {t("subtitle")}
        </p>

        <div className={`flex flex-wrap gap-2 justify-center mb-10 ${isAr ? "flex-row-reverse" : ""}`}>
          {CATEGORY_KEYS.map((cat) => {
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`min-h-[44px] rounded-full px-5 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 ${
                  isActive
                    ? "bg-primary-700 text-white shadow-md"
                    : "surface-warm text-primary-700 border border-primary-200"
                }`}
                aria-pressed={isActive}
                aria-label={`${t(`categories.${cat}`)} ${isActive ? "(selected)" : ""}`}
              >
                {t(`categories.${cat}`)}
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {visibleTiles.map((tile) => (
            <div key={tile.id} className="flex flex-col gap-2">
              <PhotoFrame
                src={tile.src}
                alt={t(`tiles.${tile.labelKey}`)}
                comingSoonLabel={common("comingSoonPhoto")}
                aspect="square"
              />
              <span className="text-center text-sm font-medium text-gray-600">
                {t(`tiles.${tile.labelKey}`)}
              </span>
            </div>
          ))}

          {visibleTiles.length === 0 && (
            <div className="col-span-full flex items-center justify-center py-20 text-gray-400 text-sm">
              {t("empty")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: تحقّق (test) إن كل الـgradient/إيموجي اتشالوا**

```bash
grep -c "gradient\|emoji" src/components/sections/GallerySection.tsx
```

Expected: `0`.

- [ ] **Step 4: build/lint**

```bash
npm run lint && npm run type-check
```

Expected: نجاح.

- [ ] **Step 5: Commit**

```bash
git add src/components/sections/GallerySection.tsx
git commit -m "fix: replace gradient+emoji gallery tiles with real-photo-ready PhotoFrame grid"
```

---

## Task 11: ProgramsSection

**Files:**
- Modify: `src/components/sections/ProgramsSection.tsx:1-22, 74-89, 191-199`

**Interfaces:**
- Consumes: `.icon-tile`, `.pill-btn` (Task 1)، أيقونات `Baby`, `Footprints`, `Home`, `Backpack` من `lucide-react` بدل الإيموجي.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "🍼|👣|🏠|🎒" src/components/sections/ProgramsSection.tsx
```

Expected: `5` (٤ إيموجي بالميتا + ١ في الـCTA).

- [ ] **Step 2: بدّل الاستيراد والميتاداتا** (سطور 1-15):

```tsx
import { useTranslations, useLocale } from "next-intl";
import { CheckCircle2, Users, Award, Languages, Trees } from "lucide-react";

const PROGRAM_KEYS = ["infants", "toddlers", "casa", "prep"] as const;
type ProgramKey = (typeof PROGRAM_KEYS)[number];

const PROGRAM_META: Record<
  ProgramKey,
  { color: string; lightColor: string; emoji: string }
> = {
  infants:  { color: "#2d5016", lightColor: "#e8f5e0", emoji: "🍼" },
  toddlers: { color: "#5aa01e", lightColor: "#edf7e0", emoji: "👣" },
  casa:     { color: "#f5a623", lightColor: "#fef8ec", emoji: "🏠" },
  prep:     { color: "#1565c0", lightColor: "#e8f0fc", emoji: "🎒" },
};
```

بـ (كل قيم الكلاسات هنا **حروف ثابتة كاملة** مش مبنية بالـconcatenation وقت التشغيل — Tailwind JIT بيمسح نص الملف الخام، فلازم كل class يظهر حرفيًا في الكود):

```tsx
import { useTranslations, useLocale } from "next-intl";
import { CheckCircle2, Users, Award, Languages, Trees, Baby, Footprints, Home, Backpack } from "lucide-react";

const PROGRAM_KEYS = ["infants", "toddlers", "casa", "prep"] as const;
type ProgramKey = (typeof PROGRAM_KEYS)[number];

const PROGRAM_META: Record<
  ProgramKey,
  { Icon: typeof Baby; iconClass: string; badgeClass: string; pillClass: string; checkClass: string }
> = {
  infants: {
    Icon: Baby,
    iconClass: "text-primary-700 bg-primary-50 border-primary-700",
    badgeClass: "bg-primary-50 text-primary-700",
    pillClass: "border-primary-700 text-primary-700 bg-primary-50",
    checkClass: "text-primary-700",
  },
  toddlers: {
    Icon: Footprints,
    iconClass: "text-primary-600 bg-primary-50 border-primary-600",
    badgeClass: "bg-primary-50 text-primary-600",
    pillClass: "border-primary-600 text-primary-600 bg-primary-50",
    checkClass: "text-primary-600",
  },
  casa: {
    Icon: Home,
    iconClass: "text-accent-dark bg-amber-50 border-accent",
    badgeClass: "bg-amber-50 text-accent-dark",
    pillClass: "border-accent text-accent-dark bg-amber-50",
    checkClass: "text-accent-dark",
  },
  prep: {
    Icon: Backpack,
    iconClass: "text-blue-700 bg-blue-50 border-blue-700",
    badgeClass: "bg-blue-50 text-blue-700",
    pillClass: "border-blue-700 text-blue-700 bg-blue-50",
    checkClass: "text-blue-700",
  },
};
```

- [ ] **Step 3: بدّل جسم كارت البرنامج بالكامل** (سطور 73-165) — من الفتح لحد زرار "Learn More"، احذف الاعتماد على `color`/`lightColor`/`emoji` القدامى بالكامل:

```tsx
            const { Icon, iconClass, badgeClass, pillClass, checkClass } = PROGRAM_META[key];
            return (
              <div
                key={key}
                className="card-hover bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 flex flex-col"
              >
                <div className="p-6 flex flex-col flex-1">
                  <div className={`icon-tile mb-4 border ${iconClass}`}>
                    <Icon size={22} />
                  </div>

                  <h3 className="font-bold text-lg leading-snug mb-2 text-primary-700">
                    {t(`items.${key}.title`)}
                  </h3>

                  <span className={`inline-block self-start text-xs font-semibold px-3 py-1 rounded-full mb-3 ${badgeClass}`}>
                    {t(`items.${key}.age`)}
                  </span>

                  <p className="text-gray-500 text-sm leading-relaxed mb-4">
                    {t(`items.${key}.desc`)}
                  </p>

                  {outcomes.length > 0 && (
                    <ul className="space-y-2 mb-4">
                      {outcomes.slice(0, 3).map((outcome, i) => (
                        <li
                          key={i}
                          className={`flex items-start gap-2 text-xs text-gray-600 ${isAr ? "flex-row-reverse text-right" : ""}`}
                        >
                          <CheckCircle2 size={14} className={`mt-0.5 shrink-0 ${checkClass}`} />
                          <span>{outcome}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {materials.length > 0 && (
                    <div className={`flex flex-wrap gap-1.5 mb-5 ${isAr ? "flex-row-reverse" : ""}`}>
                      {materials.slice(0, 3).map((mat, i) => {
                        const label = mat.split(" ").slice(0, 3).join(" ");
                        return (
                          <span
                            key={i}
                            className={`text-xs px-2 py-0.5 rounded-full border font-medium ${pillClass}`}
                          >
                            {label}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  <div className="flex-1" />

                  <a href="#contact" className="pill-btn pill-btn--forest mt-2 !py-2 text-sm">
                    {t("learnMore")}
                  </a>
                </div>
              </div>
            );
```

هذا الجسم بيستبدل من `return (` بعد فتح `.map((key) => {` (بعد بلوك `try/catch` بتاع `outcomes`/`materials` اللي يفضل زي ما هو زي ما هو) لحد `})}` بتاعة الكارت — راجع الملف الأصلي عشان تلزق الجسم الجديد مكان الصح بالظبط.

- [ ] **Step 4: بدّل زرار الـCTA النهائي** (سطور 191-199):

```tsx
        <div className="flex justify-center">
          <a
            href="#contact"
            className="inline-flex items-center gap-2 px-10 py-4 rounded-2xl text-base font-bold text-white shadow-xl transition-all hover:scale-105 active:scale-95"
            style={{ background: "#f5a623" }}
          >
            🎒 {t("cta")}
          </a>
        </div>
```

بـ:

```tsx
        <div className="flex justify-center">
          <a href="#contact" className="pill-btn pill-btn--primary px-10 py-4 text-base">
            {t("cta")}
          </a>
        </div>
```

- [ ] **Step 5: تحقّق (test)**

```bash
grep -cE "🍼|👣|🏠|🎒" src/components/sections/ProgramsSection.tsx
npm run lint && npm run type-check
```

Expected: أول أمر `0`، الباقي ينجح (لو الـlint وقف على أي مرجع باقي لـ`color`/`lightColor`/`emoji` القديمة، كمّل تحديثها زي الملاحظة في Step 3).

- [ ] **Step 6: Commit**

```bash
git add src/components/sections/ProgramsSection.tsx
git commit -m "design: replace program emoji icons with lucide icons and pill CTA"
```

---

## Task 12: CurriculumSection

**Files:**
- Modify: `src/components/sections/CurriculumSection.tsx:1-47, 92, 142-147`

**Interfaces:**
- Consumes: أيقونات `Hand`, `Eye`, `BookOpen`, `Calculator`, `Globe`, `Home`, `Clock`, `Users`, `Sprout` من `lucide-react`.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "🧹|👁️|📖|🔢|🌍|🏡|⏳|👦🏽👧🏽|🌱|📚" src/components/sections/CurriculumSection.tsx
```

Expected: عدد أكبر من صفر.

- [ ] **Step 2: بدّل خرائط الإيموجي بأيقونات** (سطور 1-47) — من:

```tsx
import { useTranslations, useLocale } from "next-intl";

const areaKeys = [
  "practicalLife",
  "sensorial",
  "language",
  "mathematics",
  "cultural",
] as const;

const areaEmojis: Record<string, string> = {
  practicalLife: "🧹",
  sensorial:     "👁️",
  language:      "📖",
  mathematics:   "🔢",
  cultural:      "🌍",
};
```

لـ:

```tsx
import { useTranslations, useLocale } from "next-intl";
import { Hand, Eye, BookOpen, Calculator, Globe, Home, Clock, Users, Sprout } from "lucide-react";

const areaKeys = [
  "practicalLife",
  "sensorial",
  "language",
  "mathematics",
  "cultural",
] as const;

const areaIcons: Record<string, typeof Hand> = {
  practicalLife: Hand,
  sensorial:     Eye,
  language:      BookOpen,
  mathematics:   Calculator,
  cultural:      Globe,
};

/* حروف كلاسات ثابتة كاملة — بديل مباشر لـareaBorderColors/areaLightBg القديمة
   (لازم تكون literal strings كاملة عشان Tailwind JIT يمسكها؛ ممنوع بناء الاسم
   بـ string concatenation وقت التشغيل زي .replace("border-","bg-")). */
const areaAccent: Record<string, { border: string; bg: string; text: string; dot: string }> = {
  practicalLife: { border: "border-primary-700", bg: "bg-primary-50", text: "text-primary-700", dot: "bg-primary-700" },
  sensorial:     { border: "border-accent",       bg: "bg-amber-50",   text: "text-accent-dark", dot: "bg-accent" },
  language:      { border: "border-primary-500",  bg: "bg-primary-50", text: "text-primary-600", dot: "bg-primary-500" },
  mathematics:   { border: "border-primary-600",  bg: "bg-primary-50", text: "text-primary-700", dot: "bg-primary-600" },
  cultural:      { border: "border-accent-dark",  bg: "bg-amber-50",   text: "text-accent-dark", dot: "bg-accent-dark" },
};
```

وبدّل:

```tsx
const principleIcons: Record<string, string> = {
  preparedEnvironment: "🏡",
  workCycle:           "⏳",
  mixedAges:           "👦🏽👧🏽",
  autoeducation:       "🌱",
};
```

لـ:

```tsx
const principleIcons: Record<string, typeof Home> = {
  preparedEnvironment: Home,
  workCycle:           Clock,
  mixedAges:            Users,
  autoeducation:        Sprout,
};
```

- [ ] **Step 3: بدّل كارت المنطقة بالكامل** (سطور ~77-121، من فتح `.map((key) =>` لقفل الكارت) — احذف الاعتماد على `areaBorderColors`/`areaLightBg`/`areaEmojis` واستخدم `areaAccent`:

```tsx
          {areaKeys.map((key) => {
            const Icon = areaIcons[key];
            const accent = areaAccent[key];
            return (
              <div
                key={key}
                className={`card-hover rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden border-s-4 ${accent.border} ${
                  key === "mathematics" || key === "cultural" ? "lg:col-span-1" : ""
                }`}
              >
                <div className={`px-6 pt-6 pb-4 ${accent.bg}`}>
                  <Icon size={32} className={`mb-3 ${accent.text}`} />
                  <h3 className={`text-xl font-bold ${accent.text}`}>
                    {t(`areas.${key}.title`)}
                  </h3>
                </div>

                <div className="px-6 py-5">
                  <p className="text-gray-600 text-sm leading-relaxed mb-4">
                    {t(`areas.${key}.desc`)}
                  </p>
                  <ul className="space-y-2">
                    {outcomeIndices.map((i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                        <span
                          className={`mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-white text-xs font-bold ${accent.dot}`}
                        >
                          ✓
                        </span>
                        {t(`areas.${key}.outcomes.${i}`)}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
```

- [ ] **Step 4: بدّل استخدام أيقونات المبادئ** (سطور ~142-147):

```tsx
                <div
                  className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-sm"
                  style={{ background: "#fff" }}
                >
                  {principleIcons[key]}
                </div>
```

بـ:

```tsx
                {(() => {
                  const Icon = principleIcons[key];
                  return (
                    <div className="icon-tile flex-shrink-0 bg-white shadow-sm">
                      <Icon size={22} />
                    </div>
                  );
                })()}
```

- [ ] **Step 5: تحقّق (test)**

```bash
grep -cE "🧹|👁️|📖|🔢|🌍|🏡|⏳|👦🏽👧🏽|🌱" src/components/sections/CurriculumSection.tsx
npm run lint && npm run type-check
```

Expected: أول أمر `0`، الباقي ينجح.

- [ ] **Step 6: Commit**

```bash
git add src/components/sections/CurriculumSection.tsx
git commit -m "design: replace curriculum area/principle emoji with lucide icons"
```

---

## Task 13: DailyLifeSection

**Files:**
- Modify: `src/components/sections/DailyLifeSection.tsx` (rewrite كامل)

**Interfaces:**
- Consumes: `PhotoFrame` (Task 2)، أيقونات `Sun`, `Puzzle`, `Trees`, `Utensils`, `BookOpen`, `Palette`, `Leaf`, `Users`, `Sparkles` من `lucide-react`.
- ⚠️ ترجمة `dailyLife.schedule[i].emoji` هتبقى مفتاح يتيم (unused) — سيبها في الترجمة (الحذف مش ضروري ولا بيكسر `verify:i18n`)، بس الكومبوننت هيستخدم أيقونة ثابتة بدل ما يقرأها.

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "🌳|🌸|🦋|🌻|🐝|🌿|🍃|🌺|🌅|🎨|📚|🤝|🌞" src/components/sections/DailyLifeSection.tsx
```

Expected: عدد أكبر من صفر.

- [ ] **Step 2: أعد كتابة `src/components/sections/DailyLifeSection.tsx` بالكامل:**

```tsx
import { useTranslations } from "next-intl";
import { Sun, Puzzle, Trees, Utensils, BookOpen, Palette, Leaf, Users, Sparkles } from "lucide-react";
import PhotoFrame from "@/components/ui/PhotoFrame";

const scheduleIndices = [0, 1, 2, 3, 4, 5] as const;
const scheduleIcons = [Sun, Puzzle, Trees, Utensils, BookOpen, Palette] as const;

const featureIndices = [0, 1, 2, 3, 4] as const;
const featureIcons = [Sun, Leaf, Users, BookOpen, Sparkles] as const;

export default function DailyLifeSection() {
  const t = useTranslations("dailyLife");
  const common = useTranslations("common");

  return (
    <section id="daily-life" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <span className="badge surface-warm text-primary-700">{t("badge")}</span>
          <h2 className="section-title mt-4 text-gray-900">{t("title")}</h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed mt-4">
            {t("subtitle")}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          {/* LEFT — Daily schedule timeline */}
          <div>
            <h3 className="text-xl font-bold mb-8 text-primary-700">{t("scheduleTitle")}</h3>
            <ol className="relative space-y-0">
              {scheduleIndices.map((i) => {
                const Icon = scheduleIcons[i];
                const isLast = i === scheduleIndices[scheduleIndices.length - 1];
                return (
                  <li key={i} className="relative flex gap-5 pb-8">
                    {!isLast && (
                      <div
                        className="absolute start-5 top-10 bottom-0 w-0.5 bg-primary-300 opacity-30"
                        aria-hidden="true"
                      />
                    )}
                    <div className="icon-tile relative z-10 h-10 w-10 border-2 border-white shadow">
                      <Icon size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="inline-block rounded-full bg-primary-700 px-3 py-0.5 text-xs font-bold text-white">
                          {t(`schedule.${i}.time`)}
                        </span>
                        <span className="font-semibold text-gray-800 text-sm">
                          {t(`schedule.${i}.activity`)}
                        </span>
                      </div>
                      <p className="text-gray-500 text-sm leading-relaxed">
                        {t(`schedule.${i}.desc`)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          {/* RIGHT — Environment card + real classroom photo */}
          <div className="flex flex-col gap-6">
            <div className="surface-warm overflow-hidden rounded-3xl border border-gray-100 shadow-lg">
              <div className="surface-forest px-7 py-6">
                <h3 className="text-xl font-bold text-white mb-1">{t("environment.title")}</h3>
                <p className="text-white/80 text-sm leading-relaxed">{t("environment.desc")}</p>
              </div>
              <ul className="px-7 py-6 space-y-4">
                {featureIndices.map((i) => {
                  const Icon = featureIcons[i];
                  return (
                    <li key={i} className="flex items-start gap-3">
                      <span className="icon-tile flex-shrink-0 bg-white shadow-sm">
                        <Icon size={18} />
                      </span>
                      <span className="text-gray-700 text-sm leading-relaxed pt-1.5">
                        {t(`environment.features.${i}`)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>

            <PhotoFrame
              alt={t("environmentPhotoAlt")}
              comingSoonLabel={common("comingSoonPhoto")}
              aspect="video"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: أضف `dailyLife.environmentPhotoAlt`** في الترجمتين (بجوار `environment.title`):

`messages/ar.json`: `"environmentPhotoAlt": "زاوية من فصول كوكب الطفل الحر",`
`messages/en.json`: `"environmentPhotoAlt": "A corner of a Planet of the Free Child classroom",`

- [ ] **Step 4: تحقّق (test)**

```bash
grep -cE "🌳|🌸|🦋|🌻|🐝|🌿|🍃|🌺|🌅|🎨|📚|🤝|🌞" src/components/sections/DailyLifeSection.tsx
npm run verify:i18n
npm run lint && npm run type-check
```

Expected: أول أمر `0`، الباقي ينجح.

- [ ] **Step 5: Commit**

```bash
git add src/components/sections/DailyLifeSection.tsx messages/ar.json messages/en.json
git commit -m "design: replace DailyLife emoji decoration with icons and a real-photo slot"
```

---

## Task 14: FollowUsSection وContactSection

**Files:**
- Modify: `src/components/sections/FollowUsSection.tsx` (rewrite كامل)
- Modify: `src/components/sections/ContactSection.tsx:113-116, 209-239, 247-271` (لمسة أخف — النموذج نفسه يفضل زي ما هو)

**Interfaces:**
- Consumes: `Instagram`, `Facebook`, `MessageCircle`, `MapPin`, `CheckCircle2` من `lucide-react` (كلها مستوردة بالفعل في `ContactSection` عدا `CheckCircle2`).

- [ ] **Step 1: تحقّق (test) قبل التعديل**

```bash
grep -cE "📸|👍|💬|✨" src/components/sections/FollowUsSection.tsx
grep -cE "📍|✅" src/components/sections/ContactSection.tsx
```

Expected: أول أمر `4`، تاني أمر `2`.

- [ ] **Step 2: أعد كتابة `src/components/sections/FollowUsSection.tsx` بالكامل:**

```tsx
import { useTranslations } from "next-intl";
import { Instagram, Facebook, MessageCircle } from "lucide-react";
import { siteFacts } from "@/lib/site-facts";

type Platform = {
  key: string;
  name: string;
  Icon: typeof Instagram;
  handle: string;
  href: string;
};

const platforms: Platform[] = [
  { key: "instagram", name: "Instagram", Icon: Instagram, handle: "@montessori_nursery", href: siteFacts.contact.instagram },
  { key: "facebook", name: "Facebook", Icon: Facebook, handle: "Montessori Nursery", href: "https://www.facebook.com/p/Montessori-nursery-100063063920027/" },
  { key: "whatsapp", name: "WhatsApp", Icon: MessageCircle, handle: siteFacts.contact.phoneDisplay, href: siteFacts.contact.whatsapp },
];

export default function FollowUsSection() {
  const t = useTranslations("followUs");

  return (
    <section id="follow" className="section-padding surface-forest">
      <div className="max-w-7xl mx-auto">
        <span className="badge border border-white/20 bg-white/10 text-white">{t("badge")}</span>

        <h2 className="section-title mt-4 text-center text-white">{t("title")}</h2>
        <p className="text-center text-white/70 text-lg max-w-xl mx-auto mb-14 mt-4">
          {t("subtitle")}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {platforms.map(({ key, name, Icon, handle, href }) => (
            <div
              key={key}
              className="flex flex-col items-center rounded-3xl border border-white/10 bg-white/5 p-7 text-center transition-transform hover:-translate-y-1"
            >
              <div className="icon-tile icon-tile--lg mb-4 bg-white/10 text-white">
                <Icon size={26} />
              </div>
              <h3 className="text-white font-bold text-lg mb-1">{name}</h3>
              <p className="text-white/70 text-sm mb-5 font-mono">{handle}</p>
              <a href={href} target="_blank" rel="noopener noreferrer" className="pill-btn pill-btn--primary w-full">
                {t("cta")}
              </a>
            </div>
          ))}
        </div>

        <div className="mt-16 border-t border-white/10" />

        <p className="text-center text-white/50 text-xs mt-6">
          &copy; {new Date().getFullYear()} Planet of the Free Child Nursery — Jeddah, Saudi Arabia. {t("copyright")}
        </p>
      </div>
    </section>
  );
}
```

- [ ] **Step 3: نظّف `ContactSection.tsx`** — بدّل البادج (سطور 113-116):

```tsx
            <div className="flex mb-4">
              <span className="badge" style={{ background: "#f0f7e6", color: "#2d5016" }}>
                📍 {t("badge")}
              </span>
            </div>
```

بـ:

```tsx
            <span className="badge surface-warm text-primary-700">{t("badge")}</span>
```

بدّل بلوك خريطة الـPlaceholder (سطور 209-239) — احذف الإيموجي 📍 واستخدم أيقونة `MapPin` المستوردة بالفعل:

```tsx
            <div
              className="rounded-3xl overflow-hidden border border-gray-100 shadow-sm flex flex-col items-center justify-center gap-3 py-10 px-6 text-center"
              style={{ background: "#f0f7e6", minHeight: "180px" }}
            >
              <span className="text-5xl">📍</span>
```

بـ:

```tsx
            <div className="surface-warm rounded-3xl overflow-hidden border border-gray-100 shadow-sm flex flex-col items-center justify-center gap-3 py-10 px-6 text-center min-h-[180px]">
              <MapPin size={40} className="text-primary-700" aria-hidden="true" />
```

بدّل أيقونة النجاح (سطور 247-256) — استورد `CheckCircle2` وبدّل الإيموجي:

سطر الاستيراد:

```tsx
import { ArrowUpRight, Clock, Mail, MapPin, Phone } from "lucide-react";
```

يبقى:

```tsx
import { ArrowUpRight, CheckCircle2, Clock, Mail, MapPin, Phone } from "lucide-react";
```

وجسم الحالة الناجحة:

```tsx
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center text-4xl shadow-lg"
                  style={{ background: "linear-gradient(135deg, #2d5016, #5aa01e)" }}
                >
                  ✅
                </div>
```

بـ:

```tsx
                <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary-700 text-white shadow-lg">
                  <CheckCircle2 size={36} />
                </div>
```

- [ ] **Step 4: تحقّق (test)**

```bash
grep -cE "📸|👍|💬|✨" src/components/sections/FollowUsSection.tsx
grep -cE "📍|✅" src/components/sections/ContactSection.tsx
npm run lint && npm run type-check
```

Expected: أول أمرين `0`، الباقي ينجح.

- [ ] **Step 5: Commit**

```bash
git add src/components/sections/FollowUsSection.tsx src/components/sections/ContactSection.tsx
git commit -m "design: replace FollowUs/Contact emoji with lucide icons and shared surfaces"
```

---

## Task 15: لمسات Nano Banana الزخرفية

**Files:**
- Create: `public/decor/section-divider.svg` (أو `.png` شفاف حسب مخرجات التوليد)
- Modify: قسمين بس من اللي اتصمموا فوق — نطاق ضيق ومقصود، مش كل سكشن (زي ما نص الـspec §4)

**Interfaces:**
- Consumes: لا كود جديد — أصول ثابتة بس.

- [ ] **Step 1: ولّد شكل عضوي واحد (ورقة/دائرة ناعمة) بلوحة الألوان المعتمدة (`#2d5016`, `#5aa01e`, `#f5a623`, `#f3d9a4`) عبر Nano Banana**، شفاف الخلفية، بصيغة SVG أو PNG-شفاف، وخزّنه في `public/decor/section-divider.svg`. هذا Task تنفيذي مباشر (مش كود) — ينفَّذ هنا مش عبر Codex.

- [ ] **Step 2: تحقّق (test) إن الملف اتولّد وحجمه معقول**

```bash
ls -la public/decor/section-divider.svg
```

Expected: الملف موجود، الحجم أقل من ٥٠كيلوبايت.

- [ ] **Step 3: ضيف الشكل كخلفية زخرفية في سكشنين بس** — مثلاً بين `HeroSection` و`AboutSection`، وبين `GallerySection` و`ProgramsSection`. مثال تطبيق في `AboutSection.tsx` (أضف قبل `</section>` الأخيرة):

```tsx
        <img
          src="/decor/section-divider.svg"
          alt=""
          aria-hidden="true"
          className="pointer-events-none absolute -bottom-6 start-1/2 w-40 -translate-x-1/2 opacity-70"
        />
```

(السكشن محتاج `relative` على الـ`<section>` نفسها عشان `absolute` يشتغل صح — تأكد إنها موجودة، أضفها لو مش موجودة).

- [ ] **Step 4: تحقّق بصري في المتصفح** (ar وen) إن الشكل مش بيتكرر بنفس الوضعية في كل سكشن ومش بيغطي نص.

- [ ] **Step 5: Commit**

```bash
git add public/decor/ src/components/sections/AboutSection.tsx src/components/sections/GallerySection.tsx
git commit -m "design: add sparse Nano Banana decorative accents between two sections"
```

---

## Task 16: فحص شامل قبل النشر

**Files:** لا تعديل كود — فحص فقط.

- [ ] **Step 1: تحقّق (test) شامل محليًا**

```bash
npm run test:ci
```

Expected: `lint` + `type-check` + `verify:i18n` + `verify:css` + `verify:assets` + `verify:site-facts` + `build` كلهم بينجحوا.

- [ ] **Step 2: تحقّق (test) عدم وجود إيموجي وظيفي متبقي في أي سكشن**

```bash
grep -rlP "[\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}]" src/components/sections/*.tsx src/components/layout/*.tsx
```

Expected: لا نتائج (أو نتائج فاضية) — لو فيه ملف باقي فيه إيموجي، ارجع للـTask بتاعه وكمّله.

- [ ] **Step 3: تحقّق (test) عدم وجود `style={{` ديناميكي متبقٍ في الكومبوننتس المعاد تصميمها**

```bash
grep -rn "style={{" src/components/sections/*.tsx src/components/layout/*.tsx
```

Expected: النتائج المتبقية (لو فيه) لازم تكون قيم ثابتة/غير مشتقة من props وموثّقة ليه اتسابت (زي ملحوظة Task 9)، مش قيم ديناميكية جديدة.

- [ ] **Step 4: افتح الموقع في المتصفح (`npm run dev` + Browser tool) وافحص بصريًا:**
  - الصفحة الرئيسية عربي (`/ar`) — تأكد التخطيط غير المتماثل بيبان صح RTL، مفيش نص متراكب.
  - نفس الصفحة إنجليزي (`/en`) — تأكد التخطيط بيبان صح LTR.
  - `/manage/index.html` — تأكد كارت الرد الآلي على واتساب ظاهر وبيشتغل، ومفيش أخطاء CSP في الـconsole (`read_console_messages`).
  - تأكد زرار الرد الآلي **مش موجود** في `/ar` أو `/en` (الصفحة الرئيسية).

- [ ] **Step 5: انشر التغييرات على السيرفر** حسب سكربت النشر الحالي في `deploy.sh`.

- [ ] **Step 6: بعد النشر — لو أي ملف من `public/manage/index.html` أو غيره اتغيّر فيه محتوى `<style>` inline (مش الحالة هنا لأن Task 6 استخدم `app-admin.css` الخارجي فقط)، حدّث `/etc/nginx/snippets/mk-csp-parts.conf` على السيرفر بالهاش الجديد، ثم:**

```bash
nginx -t && systemctl reload nginx
```

- [ ] **Step 7: حدّث pristine baseline وhashes.txt الخاصين بفحص العبث (tamper check)** لكل الملفات المنشورة الجديدة، وتأكد إن الفحص بيرجّع `tamper=0`.

- [ ] **Step 8: راجع معايير القبول في الـspec وحدد كل بند "تم/لسه":**
  - [ ] مفيش إيموجي كأيقونة وظيفية
  - [ ] مفيش سكشنين متتاليين بنفس تركيبة گريد كروت + gradient + بادج زجاجي
  - [ ] الگاليري صور حقيقية أو حالة "قريبًا" مصممة بقصد
  - [ ] زرار الرد الآلي مش في الصفحة الرئيسية العامة
  - [ ] `npm run build`/`lint` ناجحين
  - [ ] `nginx -t` ناجح، pristine محدّث، تفتيش العبث = 0

- [ ] **Step 9: Commit أي تعديل تنظيفي أخير اكتشفته في الفحص، ثم أغلق الـPlan.**

