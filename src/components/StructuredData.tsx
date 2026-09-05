import Script from "next/script";

export function StructuredData({ locale }: { locale: string }) {
  const isArabic = locale === 'ar';
  const localizedUrl = `https://montessori-ksa.com/${locale}`;

  const business = {
    "@type": ["ChildCare", "LocalBusiness"],
    "@id": "https://montessori-ksa.com/#childcare",
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
      "https://www.instagram.com/montessori_nursery/",
      "https://www.facebook.com/p/Montessori-nursery-100063063920027/"
    ],
    "availableLanguage": ["ar", "en"]
  };

  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      business,
      {
        "@type": "WebSite",
        "@id": "https://montessori-ksa.com/#website",
        "url": "https://montessori-ksa.com",
        "name": isArabic ? "روضة كوكب الطفل الحر" : "Planet of the Free Child Nursery",
        "description": isArabic
          ? "موقع روضة كوكب الطفل الحر في جدة، يقدم معلومات عن برامج مونتيسوري والرعاية المبكرة والتواصل مع الحضانة."
          : "The official website for Planet of the Free Child Nursery in Jeddah, with Montessori programs, early childcare information, and contact details.",
        "publisher": { "@id": "https://montessori-ksa.com/#childcare" },
        "inLanguage": ["ar", "en"]
      },
      {
        "@type": "WebPage",
        "@id": `${localizedUrl}#webpage`,
        "url": localizedUrl,
        "name": isArabic ? "روضة كوكب الطفل الحر في جدة" : "Planet of the Free Child Nursery in Jeddah",
        "description": isArabic
          ? "روضة مونتيسوري ثنائية اللغة في جدة للأطفال من 3 أشهر إلى 6 سنوات."
          : "A bilingual Montessori nursery in Jeddah for children from 3 months to 6 years.",
        "isPartOf": { "@id": "https://montessori-ksa.com/#website" },
        "about": { "@id": "https://montessori-ksa.com/#childcare" },
        "primaryImageOfPage": {
          "@type": "ImageObject",
          "url": "https://montessori-ksa.com/og-image.png",
          "width": 1200,
          "height": 630
        },
        "inLanguage": locale,
        "dateModified": "2026-09-05"
      },
      {
        "@type": "BreadcrumbList",
        "@id": `${localizedUrl}#breadcrumb`,
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "name": isArabic ? "الرئيسية" : "Home",
            "item": localizedUrl
          }
        ]
      },
      {
        "@type": "EducationalOrganization",
        "@id": "https://montessori-ksa.com/#organization",
        "name": isArabic ? "روضة كوكب الطفل الحر" : "Planet of the Free Child Nursery",
        "alternateName": isArabic ? "Planet of the Free Child Nursery" : "روضة كوكب الطفل الحر",
        "url": "https://montessori-ksa.com",
        "logo": "https://montessori-ksa.com/og-image.png",
        "address": business.address,
        "telephone": business.telephone,
        "email": business.email,
        "knowsAbout": [
          "Montessori Education",
          "Early Childhood Education",
          "Bilingual Education",
          "Child Development",
          "Preschool Education",
          "Nursery Care"
        ],
        "sameAs": business.sameAs
      }
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
