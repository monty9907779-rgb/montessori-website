import Link from "next/link";
import { useLocale } from "next-intl";

const links = {
  ar: [
    ["/ar/hadana-qariba-minni", "حضانة قريبة مني في جدة"],
    ["/ar/kayfa-akhtar-hadana", "كيف أختار حضانة لطفلي؟"],
    ["/ar/rsum-alhadanat-fi-jeddah", "رسوم الحضانات في جدة"],
    ["/ar/what-is-montessori-method", "ما هو منهج مونتيسوري؟"],
  ],
  en: [
    ["/en/daycare-near-me-jeddah", "Daycare Near Me in Jeddah"],
    ["/en/preschool-near-me-jeddah", "Preschool Near Me in Jeddah"],
    ["/en/kindergarten-near-me-jeddah", "Kindergarten Near Me in Jeddah"],
    ["/en/what-is-montessori-method", "What Is the Montessori Method?"],
  ],
} as const;

export default function SeoLinksSection() {
  const locale = useLocale() as "ar" | "en";
  const isAr = locale === "ar";

  return (
    <section className="section-padding bg-[#f7faf3]" aria-labelledby="seo-guides-title">
      <div className="max-w-7xl mx-auto">
        <p className="badge w-fit" style={{ background: "#e9f3dc", color: "#2d5016" }}>
          {isAr ? "دليل أولياء الأمور" : "Parent Guides"}
        </p>
        <h2 id="seo-guides-title" className="section-title text-gray-900 mt-4 mb-3">
          {isAr ? "معلومات تساعدك على اتخاذ القرار" : "Guides for Your Next Decision"}
        </h2>
        <p className="text-gray-600 max-w-2xl mb-8">
          {isAr
            ? "اقرأ أدلتنا عن اختيار الحضانة، برامج التعليم المبكر، ومنهج مونتيسوري."
            : "Explore practical guides about childcare, early education, and the Montessori method."}
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {links[locale].map(([href, label]) => (
            <Link
              key={href}
              href={href}
              className="border border-[#dce8d0] bg-white p-5 rounded-lg font-semibold text-[#2d5016] hover:shadow-md transition-shadow"
            >
              {label}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
