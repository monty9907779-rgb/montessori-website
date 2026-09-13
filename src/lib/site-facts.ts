export const siteFacts = {
  name: {
    ar: "روضة كوكب الطفل الحر",
    en: "Planet of the Free Child Nursery",
  },
  ages: {
    minYears: 2,
    maxYears: 5,
    ar: "من عمر سنتين إلى ٥ سنوات",
    en: "Ages 2 to 5 years",
  },
  hours: {
    days: ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"],
    opens: "08:00",
    closes: "13:00",
    schema: "Su-Th 08:00-13:00",
    ar: "الأحد إلى الخميس، من ٨:٠٠ صباحًا حتى ١:٠٠ ظهرًا",
    arShort: "الأحد – الخميس: ٨:٠٠ص – ١:٠٠م",
    en: "Sunday to Thursday, 8:00 AM to 1:00 PM",
    enShort: "Sun – Thu: 8:00 AM – 1:00 PM",
  },
  visits: {
    opens: "10:00",
    closes: "12:00",
    ar: "الأحد إلى الخميس، من ١٠:٠٠ صباحًا حتى ١٢:٠٠ ظهرًا",
    en: "Sunday to Thursday, 10:00 AM to 12:00 PM",
  },
  address: {
    streetAr: "8603 شارع محمد عبدالكريم",
    streetEn: "8603 Muhammad Abdul Karim Street",
    districtAr: "حي الفيصلية",
    districtEn: "Al Faisaliyah District",
    cityAr: "جدة",
    cityEn: "Jeddah",
    postalCode: "23447",
    ar: "8603 شارع محمد عبدالكريم، حي الفيصلية، جدة 23447",
    en: "8603 Muhammad Abdul Karim Street, Al Faisaliyah District, Jeddah 23447",
  },
  contact: {
    phone: "+966541558173",
    phoneDisplay: "+966 54 155 8173",
    email: "info@montessori-ksa.com",
    whatsapp: "https://wa.me/966541558173",
    instagram: "https://www.instagram.com/montessori_nursery/",
    maps: "https://maps.app.goo.gl/M8cnBRL89M9ppDJY7",
  },
} as const;

export type SiteLocale = "ar" | "en";
