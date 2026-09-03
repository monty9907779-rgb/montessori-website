import { useTranslations, useLocale } from "next-intl";
import { CheckCircle2, Users, Award, Languages, Trees } from "lucide-react";

const PROGRAM_KEYS = ["infants", "toddlers", "casa", "prep"] as const;
type ProgramKey = (typeof PROGRAM_KEYS)[number];

const PROGRAM_META: Record<
  ProgramKey,
  { color: string; lightColor: string; emoji: string }
> = {
  infants:  { color: "#2d5016", lightColor: "#e8f5e0", emoji: "🍼" },
  toddlers: { color: "#5aa01e", lightColor: "#edf7e0", emoji: "👣" },
  casa:     { color: "#f5a623", lightColor: "#fef8ec", emoji: "🏠" },
  prep:     { color: "#1565c0", lightColor: "#e8f0fc", emoji: "🎒" },
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
            const { color, lightColor, emoji } = PROGRAM_META[key];

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

            return (
              <div
                key={key}
                className="card-hover bg-white rounded-3xl overflow-hidden shadow-sm border border-gray-100 flex flex-col"
              >
                {/* Colored top bar */}
                <div className="h-2 w-full" style={{ background: color }} />

                {/* Card body */}
                <div className="p-6 flex flex-col flex-1">
                  {/* Emoji icon */}
                  <div
                    className="w-14 h-14 rounded-2xl flex items-center justify-center text-2xl mb-4 shadow-sm"
                    style={{ background: lightColor }}
                  >
                    {emoji}
                  </div>

                  {/* Title */}
                  <h3
                    className="font-bold text-lg leading-snug mb-2"
                    style={{ color: "#2d5016" }}
                  >
                    {t(`items.${key}.title`)}
                  </h3>

                  {/* Age badge */}
                  <span
                    className="inline-block self-start text-xs font-semibold px-3 py-1 rounded-full mb-3"
                    style={{ background: lightColor, color }}
                  >
                    {t(`items.${key}.age`)}
                  </span>

                  {/* Description */}
                  <p className="text-gray-500 text-sm leading-relaxed mb-4">
                    {t(`items.${key}.desc`)}
                  </p>

                  {/* Outcomes — up to 3 checkmarks */}
                  {outcomes.length > 0 && (
                    <ul className="space-y-2 mb-4">
                      {outcomes.slice(0, 3).map((outcome, i) => (
                        <li
                          key={i}
                          className={`flex items-start gap-2 text-xs text-gray-600 ${isAr ? "flex-row-reverse text-right" : ""}`}
                        >
                          <CheckCircle2
                            size={14}
                            className="mt-0.5 shrink-0"
                            style={{ color }}
                          />
                          <span>{outcome}</span>
                        </li>
                      ))}
                    </ul>
                  )}

                  {/* Materials pills */}
                  {materials.length > 0 && (
                    <div className={`flex flex-wrap gap-1.5 mb-5 ${isAr ? "flex-row-reverse" : ""}`}>
                      {materials.slice(0, 3).map((mat, i) => {
                        // Trim to a short label (first 3–4 words)
                        const label = mat.split(" ").slice(0, 3).join(" ");
                        return (
                          <span
                            key={i}
                            className="text-xs px-2 py-0.5 rounded-full border font-medium"
                            style={{
                              borderColor: color,
                              color,
                              background: lightColor,
                            }}
                          >
                            {label}
                          </span>
                        );
                      })}
                    </div>
                  )}

                  {/* Spacer to push CTA to bottom */}
                  <div className="flex-1" />

                  {/* Learn More link */}
                  <a
                    href="#contact"
                    className="mt-2 inline-flex items-center justify-center text-sm font-semibold px-4 py-2 rounded-xl transition-all hover:opacity-90 hover:scale-[1.02] active:scale-95"
                    style={{ background: "#2d5016", color: "#fff" }}
                  >
                    {t("learnMore")} →
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

        {/* Enrol Now CTA */}
        <div className="flex justify-center">
          <a
            href="#contact"
            className="inline-flex items-center gap-2 px-10 py-4 rounded-2xl text-base font-bold text-white shadow-xl transition-all hover:scale-105 active:scale-95"
            style={{ background: "#f5a623" }}
          >
            🎒 {t("cta")}
          </a>
        </div>
      </div>
    </section>
  );
}
