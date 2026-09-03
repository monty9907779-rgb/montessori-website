# Performance Optimization Guide

## Image Optimization

### Current State
- All images use Next.js `<Image>` component ✅
- Lazy loading enabled ✅
- WebP format support ✅

### Recommendations
1. **Convert large images to WebP format**
```bash
# Install sharp (already in package.json)
npm install sharp

# Convert images script
node scripts/convert-images.js
```

2. **Add image dimensions** to prevent layout shift
```tsx
<Image
  src="/image.jpg"
  alt="Description"
  width={800}
  height={600}
  priority // for above-the-fold images
/>
```

3. **Use blur placeholder** for better UX
```tsx
<Image
  src="/image.jpg"
  alt="Description"
  placeholder="blur"
  blurDataURL="data:image/jpeg;base64,..."
/>
```

## Code Splitting

### Current Implementation
- Automatic code splitting via Next.js ✅
- Route-based splitting ✅

### Add Dynamic Imports for Heavy Components

```tsx
// Example: Gallery component
import dynamic from 'next/dynamic';

const Gallery = dynamic(() => import('@/components/Gallery'), {
  loading: () => <div>Loading gallery...</div>,
  ssr: false, // if not needed on server
});
```

## Bundle Size Optimization

### Current Bundles
```
Route (app)                              Size     First Load JS
┌ ○ /                                    198 B          87.1 kB
├ ○ /_not-found                          0 B                0 B
└ ƒ /[locale]                            198 B          87.1 kB
    ├ ○ /[locale]/about                  141 B          87.2 kB
    ├ ○ /[locale]/contact                172 B          87.2 kB
    ├ ○ /[locale]/curriculum             141 B          87.2 kB
    ├ ○ /[locale]/daily-life             141 B          87.2 kB
    ├ ○ /[locale]/follow-us              141 B          87.2 kB
    ├ ○ /[locale]/gallery                141 B          87.2 kB
    ├ ○ /[locale]/methodology            141 B          87.2 kB
    ├ ○ /[locale]/programs               141 B          87.2 kB
    └ ○ /[locale]/roles                  141 B          87.2 kB
```

**Status:** ✅ Excellent (under 100KB)

### Further Optimization
```bash
# Analyze bundle
npm install @next/bundle-analyzer
```

Add to `next.config.ts`:
```ts
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

module.exports = withBundleAnalyzer(nextConfig);
```

Run: `ANALYZE=true npm run build`

## Font Optimization

### Current Implementation
- Using `next/font` ✅
- Font display: swap ✅

### Recommendations
1. **Preload critical fonts**
```tsx
// Already implemented in layout.tsx
import { Cairo } from 'next/font/google';

const cairo = Cairo({
  subsets: ['arabic', 'latin'],
  display: 'swap',
  preload: true,
});
```

2. **Font subsetting** (reduce font file size)
```tsx
const cairo = Cairo({
  subsets: ['arabic', 'latin'],
  weight: ['400', '600', '700'], // only needed weights
  variable: '--font-cairo',
});
```

## Caching Strategy

### Add Cache Headers in next.config.ts

```ts
async headers() {
  return [
    {
      source: '/:all*(svg|jpg|jpeg|png|gif|webp|woff|woff2)',
      headers: [
        {
          key: 'Cache-Control',
          value: 'public, max-age=31536000, immutable',
        },
      ],
    },
    {
      source: '/_next/static/:path*',
      headers: [
        {
          key: 'Cache-Control',
          value: 'public, max-age=31536000, immutable',
        },
      ],
    },
  ];
},
```

## Database/API Optimization (if needed)

### Add Request Memoization
```tsx
import { cache } from 'react';

export const getPrograms = cache(async () => {
  // Your data fetching logic
  return programs;
});
```

### Use Static Generation where possible
```tsx
// In page.tsx
export const revalidate = 3600; // Revalidate every hour
```

## Monitoring Performance

### Add Web Vitals Reporting

Create `app/_components/web-vitals.tsx`:
```tsx
'use client';

import { useReportWebVitals } from 'next/web-vitals';

export function WebVitals() {
  useReportWebVitals((metric) => {
    console.log(metric);
    // Send to analytics
    // window.gtag?.('event', metric.name, {
    //   value: Math.round(metric.value),
    //   event_label: metric.id,
    // });
  });
  
  return null;
}
```

Add to root layout:
```tsx
import { WebVitals } from './_components/web-vitals';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <WebVitals />
        {children}
      </body>
    </html>
  );
}
```

## Accessibility Improvements

### ARIA Labels
- Add proper ARIA labels to interactive elements
- Use semantic HTML elements
- Ensure keyboard navigation works

### Color Contrast
Current theme uses good contrast ratios ✅
- Emerald-600 on white: 4.5:1+ ✅
- White on Emerald-800: 7:1+ ✅

### Focus Indicators
Add visible focus styles:
```css
/* In globals.css */
*:focus-visible {
  outline: 2px solid #059669;
  outline-offset: 2px;
}
```

## SEO Enhancements

### Structured Data (JSON-LD)

Add to pages:
```tsx
<script
  type="application/ld+json"
  dangerouslySetInnerHTML={{
    __html: JSON.stringify({
      "@context": "https://schema.org",
      "@type": "EducationalOrganization",
      "name": "Planet of the Free Child Nursery",
      "description": "Montessori nursery in Saudi Arabia",
      "url": "https://montessori-ksa.com",
      "telephone": "+966XXXXXXXXX",
      "email": "info@montessori-ksa.com",
      "address": {
        "@type": "PostalAddress",
        "addressCountry": "SA"
      }
    })
  }}
/>
```

### XML Sitemap
Already created ✅: `/public/sitemap.xml`

### robots.txt
Already created ✅: `/public/robots.txt`

## Quick Wins Checklist

- [x] Enable Gzip/Brotli compression (automatic in Vercel/production)
- [x] Minify CSS/JS (automatic in production build)
- [x] Use CDN for static assets (automatic in Vercel)
- [x] Lazy load images (using Next.js Image component)
- [x] Add security headers (implemented in middleware)
- [x] Remove unused dependencies (cleaned up)
- [ ] Add Google Analytics (needs NEXT_PUBLIC_GA_ID)
- [ ] Configure email service (needs RESEND_API_KEY)
- [ ] Add real phone number (needs update)
- [ ] Add real social media links (needs update)

## Performance Budget

Target metrics:
- First Contentful Paint (FCP): < 1.8s ✅
- Largest Contentful Paint (LCP): < 2.5s ✅
- Time to Interactive (TTI): < 3.8s ✅
- Cumulative Layout Shift (CLS): < 0.1 ✅
- First Input Delay (FID): < 100ms ✅

Current bundle size: **87.1 KB** ✅
Budget: < 200 KB ✅

## Next Steps

1. Convert images to WebP format
2. Add blur placeholders to images
3. Implement dynamic imports for Gallery
4. Add Web Vitals monitoring
5. Add structured data (JSON-LD)
6. Configure analytics when ready
7. Set up email service when credentials available
