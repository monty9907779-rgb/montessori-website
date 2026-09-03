import { useTranslations, useLocale } from "next-intl";

const stats = [
  { key: "years", value: "+١٠", valueEn: "10+" },
  { key: "children", value: "+٥٠٠", valueEn: "500+" },
  { key: "programs", value: "٤", valueEn: "4" },
  { key: "teachers", value: "+٢٠", valueEn: "20+" },
];

export default function HeroSection() {
  const t = useTranslations("hero");
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <section
      id="home"
      className="relative min-h-screen flex items-center overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, #1a3009 0%, #2d5016 40%, #3d6b20 70%, #4a8026 100%)",
      }}
    >
      {/* Decorative circles */}
      <div
        className="absolute -top-32 -start-32 w-96 h-96 rounded-full opacity-10"
        style={{ background: "radial-gradient(circle, #f5a623 0%, transparent 70%)" }}
      />
      <div
        className="absolute -bottom-20 -end-20 w-80 h-80 rounded-full opacity-10"
        style={{ background: "radial-gradient(circle, #96cf5d 0%, transparent 70%)" }}
      />

      {/* Floating leaves */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {["🌿", "🍃", "🌱", "🌿", "🍃"].map((leaf, i) => (
          <span
            key={i}
            className="absolute text-2xl opacity-20 animate-pulse"
            style={{
              top: `${15 + i * 18}%`,
              left: i % 2 === 0 ? `${5 + i * 8}%` : undefined,
              right: i % 2 !== 0 ? `${5 + i * 6}%` : undefined,
              animationDelay: `${i * 0.8}s`,
              fontSize: `${1.2 + i * 0.2}rem`,
            }}
          >
            {leaf}
          </span>
        ))}
      </div>

      <div className="relative max-w-7xl mx-auto px-4 md:px-8 pt-24 pb-16 w-full">
        <div className="max-w-3xl">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 border border-white/20 text-white text-sm font-medium mb-6 animate-fade-in">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" style={{ background: "#f5a623" }} />
            {t("badge")}
          </div>

          {/* Headline */}
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-black text-white leading-tight mb-6 animate-slide-up delay-100">
            {t("headline")}
          </h1>

          {/* Sub */}
          <p className="text-lg md:text-xl text-white leading-relaxed mb-10 max-w-2xl animate-slide-up delay-200">
            {t("subheadline")}
          </p>

          {/* CTAs */}
          <div className={`flex flex-wrap gap-4 mb-16 animate-slide-up delay-300 ${isAr ? "flex-row-reverse justify-end" : ""}`}>
            <a
              href={`#programs`}
              className="px-8 py-4 rounded-2xl text-base font-bold text-white shadow-2xl transition-all hover:scale-105 active:scale-95"
              style={{ background: "#f5a623" }}
            >
              {t("cta")}
            </a>
            <a
              href={`#contact`}
              className="px-8 py-4 rounded-2xl text-base font-bold text-white border-2 border-white/30 hover:bg-white/10 transition-all"
            >
              {t("ctaSecondary")}
            </a>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 animate-slide-up delay-400">
            {stats.map(({ key, value, valueEn }) => (
              <div
                key={key}
                className="text-center p-4 rounded-2xl bg-white/10 border border-white/10 backdrop-blur-sm"
              >
                <div className="text-3xl font-black text-white mb-1">
                  {isAr ? value : valueEn}
                </div>
                <div className="text-xs text-green-200">{t(`stats.${key}`)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Wave */}
      <div className="absolute bottom-0 inset-x-0">
        <svg viewBox="0 0 1440 80" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M0 40C360 80 1080 0 1440 40V80H0V40Z"
            fill="white"
          />
        </svg>
      </div>
    </section>
  );
}
