import Script from "next/script";

export function StructuredData({ locale }: { locale: string }) {
  const isArabic = locale === 'ar';

  const business = {
    "@context": "https://schema.org",
    "@id": "https://montessori-ksa.com/#childcare",
    "@type": ["ChildCare", "LocalBusiness"],
    "name": isArabic ? "روضة كوكب الطفل الحر" : "Planet of the Free Child Nursery",
    "alternateName": isArabic ? "Planet of the Free Child Nursery" : "روضة كوكب الطفل الحر",
    "description": isArabic
      ? "حضانة وروضة مونتيسوري في جدة للأطفال من عمر 3 أشهر إلى 6 سنوات، مع برامج للرضع والأطفال الصغار وبيت الأطفال والتهيئة المدرسية."
      : "Montessori nursery in Jeddah for children aged 3 months to 6 years, with infant, toddler, Children's House, and school-preparation programs.",
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
    "hasMap": "https://www.google.com/maps/place/%D8%B1%D9%88%D8%B6%D8%A9+%D9%83%D9%88%D9%83%D8%A8+%D8%A7%D9%84%D8%B7%D9%81%D9%84+%D8%A7%D9%84%D8%AD%D8%B1%E2%80%AD/@21.5795281,39.194829,673m/data=!3m2!1e3!4b1!4m6!3m5!1s0x15c3d18ac84c1d4d:0xaee1671b468377fb!8m2!3d21.5795281!4d39.194829!16s%2Fg%2F11s619kg25",
    "openingHoursSpecification": [
      {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
        "opens": "07:30",
        "closes": "15:00"
      }
    ],
    "serviceType": isArabic
      ? ["حضانة أطفال", "روضة مونتيسوري", "تعليم مبكر"]
      : ["Child daycare", "Montessori nursery", "Early childhood education"],
    "knowsAbout": isArabic
      ? ["منهج مونتيسوري", "التعليم المبكر", "رعاية الرضع", "التهيئة المدرسية"]
      : ["Montessori method", "Early childhood education", "Infant care", "School preparation"],
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

  return (
    <Script
      id="structured-data"
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(business) }}
    />
  );
}
