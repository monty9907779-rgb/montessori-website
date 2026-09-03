import Script from 'next/script';

export function StructuredData({ locale }: { locale: string }) {
  const isArabic = locale === 'ar';

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "ChildCare",
    "name": isArabic ? "روضة كوكب الطفل الحر" : "Planet of the Free Child Nursery",
    "alternateName": isArabic ? "Planet of the Free Child Nursery" : "روضة كوكب الطفل الحر",
    "description": isArabic
      ? "روضة منتسوري معتمدة في جدة، المملكة العربية السعودية. نتبع منهج مونتيسوري الأصيل المعتمد من AMI/AMS لتعليم الأطفال من عمر 3 أشهر إلى 6 سنوات."
      : "Certified Montessori nursery in Jeddah, Saudi Arabia. We follow the authentic AMI/AMS-aligned Montessori method for children aged 3 months to 6 years.",
    "url": "https://montessori-ksa.com",
    "logo": "https://montessori-ksa.com/og-image.png",
    "image": "https://montessori-ksa.com/og-image.png",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "حي الشاطئ",
      "addressLocality": "جدة",
      "addressRegion": "مكة المكرمة",
      "postalCode": "23421",
      "addressCountry": "SA"
    },
    "geo": {
      "@type": "GeoCoordinates",
      "latitude": "21.5795281",
      "longitude": "39.194829"
    },
    "telephone": "+966541558173",
    "email": "info@montessori-ksa.com",
    "priceRange": "$$",
    "openingHoursSpecification": [
      {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
        "opens": "07:00",
        "closes": "16:00"
      }
    ],
    "areaServed": {
      "@type": "City",
      "name": isArabic ? "جدة" : "Jeddah",
      "containedIn": {
        "@type": "Country",
        "name": isArabic ? "المملكة العربية السعودية" : "Saudi Arabia"
      }
    },
    "hasOfferCatalog": {
      "@type": "OfferCatalog",
      "name": isArabic ? "برامج الروضة" : "Nursery Programs",
      "itemListElement": [
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "EducationalOccupationalProgram",
            "name": isArabic ? "برنامج الرضع (3-12 شهر)" : "Infant Program (3-12 months)",
            "description": isArabic ? "بيئة هادئة ومحفزة لنمو الطفل" : "Calm and stimulating environment for infant development",
            "educationalProgramMode": "Full-time",
            "timeToComplete": "P9M"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "EducationalOccupationalProgram",
            "name": isArabic ? "برنامج الأطفال الصغار (12-36 شهر)" : "Toddler Program (12-36 months)",
            "description": isArabic ? "تعزيز الاستقلالية والمهارات الحركية" : "Fostering independence and motor skills",
            "educationalProgramMode": "Full-time",
            "timeToComplete": "P2Y"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "EducationalOccupationalProgram",
            "name": isArabic ? "برنامج بيت الأطفال (3-6 سنوات)" : "Casa dei Bambini (3-6 years)",
            "description": isArabic ? "منهج مونتيسوري الكامل للتعلم الأكاديمي والاجتماعي" : "Full Montessori curriculum for academic and social learning",
            "educationalProgramMode": "Full-time",
            "timeToComplete": "P3Y"
          }
        }
      ]
    },
    "sameAs": [
      "https://www.instagram.com/planet.of.the.free.child/",
      "https://www.facebook.com/PlanetoftheFreeChild",
      "https://www.tiktok.com/@planet.of.the.free.child"
    ]
  };

  return (
    <Script
      id="structured-data"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
