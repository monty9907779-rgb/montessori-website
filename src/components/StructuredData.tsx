import Script from "next/script";
import { siteFacts } from "@/lib/site-facts";

export function StructuredData({ locale }: { locale: string }) {
  const isArabic = locale === 'ar';

  const business = {
    "@context": "https://schema.org",
    "@id": "https://montessori-ksa.com/#childcare",
    "@type": ["ChildCare", "LocalBusiness"],
    "name": isArabic ? siteFacts.name.ar : siteFacts.name.en,
    "alternateName": isArabic ? siteFacts.name.en : siteFacts.name.ar,
    "description": isArabic
      ? "حضانة وروضة مونتيسوري في جدة للأطفال من عمر سنتين إلى ٥ سنوات، مع برامج ما قبل التمهيدي والتمهيدي والروضة."
      : "Montessori nursery in Jeddah for children aged 2 to 5 years, with Pre-KG and kindergarten programs.",
    "url": "https://montessori-ksa.com",
    "logo": "https://montessori-ksa.com/og-image.png",
    "image": "https://montessori-ksa.com/og-image.png",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": siteFacts.address.streetAr,
      "addressLocality": siteFacts.address.cityAr,
      "addressRegion": "مكة المكرمة",
      "postalCode": siteFacts.address.postalCode,
      "addressCountry": "SA"
    },
    "geo": {
      "@type": "GeoCoordinates",
      "latitude": "21.5795281",
      "longitude": "39.194829"
    },
    "telephone": siteFacts.contact.phone,
    "email": siteFacts.contact.email,
    "hasMap": siteFacts.contact.maps,
    "openingHoursSpecification": [
      {
        "@type": "OpeningHoursSpecification",
        "dayOfWeek": siteFacts.hours.days,
        "opens": siteFacts.hours.opens,
        "closes": siteFacts.hours.closes
      }
    ],
    "serviceType": isArabic
      ? ["حضانة أطفال", "روضة مونتيسوري", "تعليم مبكر"]
      : ["Child daycare", "Montessori nursery", "Early childhood education"],
    "knowsAbout": isArabic
      ? ["منهج مونتيسوري", "التعليم المبكر", "ما قبل التمهيدي", "التهيئة المدرسية"]
      : ["Montessori method", "Early childhood education", "Pre-KG", "School preparation"],
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
            "name": isArabic ? "برنامج ما قبل التمهيدي (سنتان)" : "Pre-KG Program (Age 2)",
            "description": isArabic ? "بيئة مونتيسورية تدعم الاستقلال واللغة والحركة" : "A Montessori environment supporting independence, language, and movement",
            "educationalProgramMode": "Full-time",
            "timeToComplete": "P1Y"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "EducationalOccupationalProgram",
            "name": isArabic ? "برنامج التمهيدي (٣-٤ سنوات)" : "KG1-KG2 Program (Ages 3-4)",
            "description": isArabic ? "تعزيز الاستقلال والمهارات الأكاديمية والاجتماعية" : "Building independence plus academic and social skills",
            "educationalProgramMode": "Full-time",
            "timeToComplete": "P2Y"
          }
        },
        {
          "@type": "Offer",
          "itemOffered": {
            "@type": "EducationalOccupationalProgram",
            "name": isArabic ? "برنامج الروضة (٥ سنوات)" : "KG3 Program (Age 5)",
            "description": isArabic ? "منهج مونتيسوري مع التهيئة للمرحلة المدرسية" : "Montessori learning with school preparation",
            "educationalProgramMode": "Full-time",
            "timeToComplete": "P1Y"
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
