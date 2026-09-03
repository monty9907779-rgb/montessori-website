import React from "react";

export default function JsonLd() {
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "ChildCare",
    "name": "Planet of the Free Child Nursery",
    "alternateName": [
      "حضانة كوكب الطفل الحر",
      "Bedaya Montessori",
      "بداية منتسوري"
    ],
    "description": "Authentic Montessori nursery in Jeddah, Saudi Arabia, offering bilingual education for children aged 3 months to 6 years.",
    "url": "https://montessori-ksa.com",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "Al Shati District",
      "addressLocality": "Jeddah",
      "addressRegion": "Makkah Province",
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
    "openingHours": "Su-Th 07:30-15:00",
    "priceRange": "$$",
    "foundingDate": "2014",
    "areaServed": {
      "@type": "City",
      "name": "Jeddah"
    },
    "availableLanguage": ["Arabic", "English"],
    "image": "https://montessori-ksa.com/og-image.png",
    "sameAs": [
      "https://www.instagram.com/montessori_ksa",
      "https://twitter.com/montessori_ksa"
    ]
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  );
}
