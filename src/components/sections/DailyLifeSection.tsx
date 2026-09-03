import { useTranslations } from "next-intl";

const scheduleIndices = [0, 1, 2, 3, 4, 5] as const;
const featureIndices  = [0, 1, 2, 3, 4] as const;

const scheduleAccents = [
  "#2d5016",
  "#3d6b20",
  "#5aa01e",
  "#f5a623",
  "#c07d10",
  "#2d5016",
] as const;

const featureIcons = ["🌿", "🎨", "📚", "🤝", "🌞"] as const;

const natureDecor = ["🌳", "🌸", "🦋", "🌻", "🐝", "🌿", "🍃", "🌺"] as const;

export default function DailyLifeSection() {
  const t = useTranslations("dailyLife");

  return (
    <section
      id="daily-life"
      className="section-padding bg-white relative overflow-hidden"
    >
      {/* Subtle dot-grid background pattern */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage:
            "radial-gradient(circle, #2d5016 1px, transparent 1px)",
          backgroundSize: "28px 28px",
        }}
        aria-hidden="true"
      />

      <div className="relative max-w-7xl mx-auto">

        {/* Badge + heading */}
        <div className="text-center mb-14">
          <div className="flex justify-center mb-4">
            <span className="badge" style={{ background: "#f0f7e6", color: "#2d5016" }}>
              🌅 {t("badge")}
            </span>
          </div>
          <h2 className="section-title text-gray-900 mb-4">
            {t("title")}
          </h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            {t("subtitle")}
          </p>
        </div>

        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">

          {/* LEFT — Daily schedule timeline */}
          <div>
            <h3
              className="text-xl font-bold mb-8"
              style={{ color: "#2d5016" }}
            >
              {t("scheduleTitle")}
            </h3>
            <ol className="relative space-y-0">
              {scheduleIndices.map((i) => {
                const accent = scheduleAccents[i];
                const isLast = i === scheduleIndices[scheduleIndices.length - 1];
                return (
                  <li key={i} className="relative flex gap-5 pb-8">
                    {/* Vertical connector */}
                    {!isLast && (
                      <div
                        className="absolute start-5 top-10 bottom-0 w-0.5 opacity-20"
                        style={{ background: accent }}
                        aria-hidden="true"
                      />
                    )}

                    {/* Emoji circle */}
                    <div
                      className="relative z-10 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-xl shadow border-2 border-white"
                      style={{ background: "#f0f7e6" }}
                    >
                      {t(`schedule.${i}.emoji`)}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span
                          className="inline-block px-3 py-0.5 rounded-full text-xs font-bold text-white"
                          style={{ background: accent }}
                        >
                          {t(`schedule.${i}.time`)}
                        </span>
                        <span className="font-semibold text-gray-800 text-sm">
                          {t(`schedule.${i}.activity`)}
                        </span>
                      </div>
                      <p className="text-gray-500 text-sm leading-relaxed">
                        {t(`schedule.${i}.desc`)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </div>

          {/* RIGHT — Our Environment card */}
          <div className="flex flex-col gap-6">
            <div
              className="rounded-3xl overflow-hidden shadow-lg border border-gray-100"
              style={{ background: "#f0f7e6" }}
            >
              {/* Card header */}
              <div
                className="px-7 py-6"
                style={{
                  background:
                    "linear-gradient(135deg, #2d5016 0%, #3d6b20 60%, #5aa01e 100%)",
                }}
              >
                <h3 className="text-xl font-bold text-white mb-1">
                  {t("environment.title")}
                </h3>
                <p className="text-green-100 text-sm leading-relaxed">
                  {t("environment.desc")}
                </p>
              </div>

              {/* Feature list */}
              <ul className="px-7 py-6 space-y-4">
                {featureIndices.map((i) => (
                  <li key={i} className="flex items-start gap-3">
                    <span
                      className="flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center text-base shadow-sm bg-white"
                    >
                      {featureIcons[i]}
                    </span>
                    <span className="text-gray-700 text-sm leading-relaxed pt-1">
                      {t(`environment.features.${i}`)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            {/* Decorative nature block */}
            <div
              className="rounded-3xl p-6 flex flex-wrap gap-3 items-center justify-center shadow-inner"
              style={{ background: "#edf7e3", minHeight: "10rem" }}
              aria-hidden="true"
            >
              {natureDecor.map((emoji, idx) => (
                <span
                  key={idx}
                  className="text-3xl select-none animate-pulse"
                  style={{
                    animationDelay: `${idx * 0.35}s`,
                    animationDuration: "3s",
                    opacity: 0.75,
                    fontSize: `${1.6 + (idx % 3) * 0.4}rem`,
                  }}
                >
                  {emoji}
                </span>
              ))}
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}
