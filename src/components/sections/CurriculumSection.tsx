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

const principleKeys = [
  "preparedEnvironment",
  "workCycle",
  "mixedAges",
  "autoeducation",
] as const;

const principleIcons: Record<string, typeof Home> = {
  preparedEnvironment: Home,
  workCycle:           Clock,
  mixedAges:            Users,
  autoeducation:        Sprout,
};

const outcomeIndices = [0, 1, 2, 3] as const;

export default function CurriculumSection() {
  const t = useTranslations("curriculum");
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <section id="curriculum" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">

        {/* Badge + heading */}
        <div className="text-center mb-14">
          <div className="flex justify-center mb-4">
            <span className="badge" style={{ background: "#f0f7e6", color: "#2d5016" }}>
              📚 {t("badge")}
            </span>
          </div>
          <h2 className="section-title text-gray-900 mb-4">
            {t("title")}
          </h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            {t("subtitle")}
          </p>
        </div>

        {/* 5 Area cards — 3-col grid, last two centred on the 2nd row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
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

          {/* Spacer to centre the last two cards on the third row in lg */}
          <div className="hidden lg:block" aria-hidden="true" />
        </div>

        {/* 4 Core Principles */}
        <div>
          <h3
            className="text-2xl font-bold text-center mb-8"
            style={{ color: "#2d5016" }}
          >
            {t("principlesTitle")}
          </h3>
          <div className="grid sm:grid-cols-2 gap-5">
            {principleKeys.map((key) => (
              <div
                key={key}
                className="flex items-start gap-4 p-5 rounded-2xl border border-gray-100 bg-primary-50 card-hover"
                style={{ background: "#f0f7e6" }}
              >
                {(() => {
                  const Icon = principleIcons[key];
                  return (
                    <div className="icon-tile flex-shrink-0 bg-white shadow-sm">
                      <Icon size={22} />
                    </div>
                  );
                })()}
                <div>
                  <h4
                    className="font-bold text-base mb-1"
                    style={{ color: "#2d5016" }}
                  >
                    {t(`principles.${key}.title`)}
                  </h4>
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {t(`principles.${key}.desc`)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
