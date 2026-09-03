import { useTranslations, useLocale } from "next-intl";

const areaKeys = [
  "practicalLife",
  "sensorial",
  "language",
  "mathematics",
  "cultural",
] as const;

const areaEmojis: Record<string, string> = {
  practicalLife: "🧹",
  sensorial:     "👁️",
  language:      "📖",
  mathematics:   "🔢",
  cultural:      "🌍",
};

const areaBorderColors: Record<string, string> = {
  practicalLife: "#2d5016",
  sensorial:     "#f5a623",
  language:      "#5aa01e",
  mathematics:   "#3d6b20",
  cultural:      "#c07d10",
};

const areaLightBg: Record<string, string> = {
  practicalLife: "#f0f7e6",
  sensorial:     "#fdf8f0",
  language:      "#f4fbec",
  mathematics:   "#edf7e3",
  cultural:      "#faefd8",
};

const principleKeys = [
  "preparedEnvironment",
  "workCycle",
  "mixedAges",
  "autoeducation",
] as const;

const principleIcons: Record<string, string> = {
  preparedEnvironment: "🏡",
  workCycle:           "⏳",
  mixedAges:           "👦🏽👧🏽",
  autoeducation:       "🌱",
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
          {areaKeys.map((key) => (
            <div
              key={key}
              className={`card-hover rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden border-s-4 ${
                key === "mathematics" || key === "cultural"
                  ? "lg:col-span-1"
                  : ""
              }`}
              style={{ borderInlineStartColor: areaBorderColors[key] }}
            >
              {/* Card header */}
              <div
                className="px-6 pt-6 pb-4"
                style={{ background: areaLightBg[key] }}
              >
                <div className="text-4xl mb-3">{areaEmojis[key]}</div>
                <h3
                  className="text-xl font-bold"
                  style={{ color: areaBorderColors[key] }}
                >
                  {t(`areas.${key}.title`)}
                </h3>
              </div>

              {/* Card body */}
              <div className="px-6 py-5">
                <p className="text-gray-600 text-sm leading-relaxed mb-4">
                  {t(`areas.${key}.desc`)}
                </p>
                <ul className="space-y-2">
                  {outcomeIndices.map((i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span
                        className="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center text-white text-xs font-bold"
                        style={{ background: areaBorderColors[key] }}
                      >
                        ✓
                      </span>
                      {t(`areas.${key}.outcomes.${i}`)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}

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
                <div
                  className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center text-2xl shadow-sm"
                  style={{ background: "#fff" }}
                >
                  {principleIcons[key]}
                </div>
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
