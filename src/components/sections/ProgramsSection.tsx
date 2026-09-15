import { useTranslations, useLocale } from "next-intl";
import { CheckCircle2, Users, Award, Languages, Trees, Baby, Footprints, Home, Backpack } from "lucide-react";

const PROGRAM_KEYS = ["infants", "toddlers", "casa", "prep"] as const;
type ProgramKey = (typeof PROGRAM_KEYS)[number];

const PROGRAM_META: Record<
  ProgramKey,
  { Icon: typeof Baby; iconClass: string; badgeClass: string; pillClass: string; checkClass: string }
> = {
  infants: {
    Icon: Baby,
    iconClass: "text-primary-700 bg-primary-50 border-primary-700",
    badgeClass: "bg-primary-50 text-primary-700",
    pillClass: "border-primary-700 text-primary-700 bg-primary-50",
    checkClass: "text-primary-700",
  },
  toddlers: {
    Icon: Footprints,
    iconClass: "text-primary-600 bg-primary-50 border-primary-600",
    badgeClass: "bg-primary-50 text-primary-600",
    pillClass: "border-primary-600 text-primary-600 bg-primary-50",
    checkClass: "text-primary-600",
  },
  casa: {
    Icon: Home,
    iconClass: "text-accent-dark bg-amber-50 border-accent",
    badgeClass: "bg-amber-50 text-accent-dark",
    pillClass: "border-accent text-accent-dark bg-amber-50",
    checkClass: "text-accent-dark",
  },
  prep: {
    Icon: Backpack,
    iconClass: "text-blue-700 bg-blue-50 border-blue-700",
    badgeClass: "bg-blue-50 text-blue-700",
    pillClass: "border-blue-700 text-blue-700 bg-blue-50",
    checkClass: "text-blue-700",
  },
};

const FEATURE_ICONS = [
  { key: "smallClasses",      Icon: Users },
  { key: "certifiedTeachers", Icon: Award },
  { key: "bilingualAR",       Icon: Languages },
  { key: "outdoorPlay",       Icon: Trees },
] as const;

export default function ProgramsSection() {
  const t = useTranslations("programs");
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <section
      id="programs"
      className="section-padding"
      style={{ background: "#f0f7e6" }}
    >
      <div className="max-w-7xl mx-auto">
        {/* Badge */}
        <div className="flex justify-center mb-4">
          <span
            className="badge"
            style={{ background: "#dff0c8", color: "#2d5016" }}
          >
            🎓 {t("badge")}
          </span>
        </div>

        {/* Heading */}
        <h2 className="section-title text-center mb-4" style={{ color: "#2d5016" }}>
          {t("title")}
        </h2>
        <p className="text-center text-gray-600 text-lg max-w-2xl mx-auto mb-14 leading-relaxed">
          {t("subtitle")}
        </p>

        {/* Program Cards Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-14">
          {PROGRAM_KEYS.map((key) => {
            // Safely read arrays — fall back to empty if translation key absent
            let outcomes: string[] = [];
            let materials: string[] = [];
            try {
              outcomes = t.raw(`curriculum.${key}.outcomes`) as string[];
            } catch {
              outcomes = [];
            }
            try {
              materials = t.raw(`curriculum.${key}.materials`) as string[];
            } catch {
              materials = [];
            }

            const { Icon, iconClass, badgeClass, pillClass, checkClass } = PROGRAM_META[key];
            return (
              <div
                key={key}
                className="card-hover bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 flex flex-col"
              >
                <div className="p-6 flex flex-col flex-1">
                  <div className={`icon-tile mb-4 border ${iconClass}`}>
                    <Icon size={22} />
                  </div>

                  <h3 className="font-bold text-lg leading-snug mb-2 text-primary-700">
                    {t(`items.${key}.title`)}
                  </h3>

                  <span className={`inline-block self-start text-xs font-semibold px-3 py-1 rounded-full mb-3 ${badgeClass}`}>
                    {t(`items.${key}.age`)}
                  </span>

                  <p className="text-gray-500 text-sm leading-relaxed mb-4">
                    {t(`items.${key}.desc`)}
                  </p>

                  {outcomes.length > 0 && (
                    <ul className="space-y-2 mb-4">
                      {outcomes.slice(0, 3).map((outcome, i) => (
                        <li
                          key={i}
                          className={`flex items-start gap-2 text-xs text-gray-600 ${isAr ? "flex-row-reverse text-right" : ""}`}
                        >
                          <CheckCircle2 size={14} className={`mt-0.5 shrink-0 ${checkClass}`} />
                          <span>{outcome}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {materials.length > 0 && (
                    <div className={`flex flex-wrap gap-1.5 mb-5 ${isAr ? "flex-row-reverse" : ""}`}>
                      {materials.slice(0, 3).map((mat, i) => {
                        const label = mat.split(" ").slice(0, 3).join(" ");
                        return (
                          <span
                            key={i}
                            className={`text-xs px-2 py-0.5 rounded-full border font-medium ${pillClass}`}
                          >
                            {label}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  <div className="flex-1" />

                  <a href="#contact" className="pill-btn pill-btn--forest mt-2 !py-2 text-sm">
                    {t("learnMore")}
                  </a>
                </div>
              </div>
            );
          })}
        </div>

        {/* Feature badges */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-12">
          {FEATURE_ICONS.map(({ key, Icon }) => (
            <div
              key={key}
              className="flex items-center gap-3 bg-white rounded-2xl px-5 py-4 shadow-sm border border-green-100"
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: "#dff0c8" }}
              >
                <Icon size={18} style={{ color: "#2d5016" }} />
              </div>
              <span className="text-sm font-semibold text-gray-700">
                {t(`features.${key}`)}
              </span>
            </div>
          ))}
        </div>

        <div className="flex justify-center">
          <a href="#contact" className="pill-btn pill-btn--primary px-10 py-4 text-base">
            {t("cta")}
          </a>
        </div>
      </div>
    </section>
  );
}
