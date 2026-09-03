import { useTranslations } from "next-intl";

const stepIndices = [0, 1, 2, 3, 4] as const;

const stepAccents = [
  "#2d5016",
  "#3d6b20",
  "#5aa01e",
  "#f5a623",
  "#c07d10",
] as const;

export default function MethodologySection() {
  const t = useTranslations("methodology");

  return (
    <section id="methodology" className="section-padding" style={{ background: "#f0f7e6" }}>
      <div className="max-w-7xl mx-auto">

        {/* Badge + heading */}
        <div className="text-center mb-14">
          <div className="flex justify-center mb-4">
            <span className="badge" style={{ background: "#d4edaa", color: "#2d5016" }}>
              🎓 {t("badge")}
            </span>
          </div>
          <h2 className="section-title text-gray-900 mb-4">
            {t("title")}
          </h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed">
            {t("subtitle")}
          </p>
        </div>

        {/* Steps — horizontal timeline on desktop, vertical list on mobile */}
        <div className="relative">

          {/* Horizontal connector line — desktop only */}
          <div
            className="hidden lg:block absolute top-10 left-0 right-0 h-0.5 opacity-30"
            style={{
              background: "linear-gradient(90deg, #2d5016, #5aa01e, #f5a623)",
              top: "2.5rem",
              marginInline: "8rem",
            }}
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 lg:gap-4 relative">
            {stepIndices.map((i) => {
              const accent = stepAccents[i];
              return (
                <div
                  key={i}
                  className="relative flex flex-col items-center text-center lg:px-2"
                >
                  {/* Step circle */}
                  <div
                    className="relative z-10 w-20 h-20 rounded-full flex items-center justify-center shadow-lg mb-5 border-4 border-white"
                    style={{ background: accent }}
                  >
                    <span className="text-white text-2xl font-black">
                      {t(`steps.${i}.step`)}
                    </span>
                  </div>

                  {/* Mobile vertical connector */}
                  {i < 4 && (
                    <div
                      className="lg:hidden absolute top-20 left-1/2 -translate-x-1/2 w-0.5 h-8 opacity-40"
                      style={{ background: stepAccents[i + 1] }}
                      aria-hidden="true"
                    />
                  )}

                  <h3
                    className="font-bold text-base mb-2"
                    style={{ color: "#2d5016" }}
                  >
                    {t(`steps.${i}.title`)}
                  </h3>
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {t(`steps.${i}.desc`)}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Maria Montessori quote */}
        <div className="mt-16 max-w-3xl mx-auto">
          <blockquote
            className="relative rounded-3xl p-8 shadow-md border-s-4 bg-white"
            style={{ borderInlineStartColor: "#2d5016" }}
          >
            {/* Decorative large quote mark */}
            <span
              className="absolute top-4 end-6 text-8xl font-serif leading-none opacity-10 select-none"
              style={{ color: "#2d5016" }}
              aria-hidden="true"
            >
              &ldquo;
            </span>

            <p
              className="relative z-10 text-xl md:text-2xl italic font-medium leading-relaxed mb-5"
              style={{ color: "#2d5016" }}
            >
              &ldquo;{t("quote.text")}&rdquo;
            </p>
            <footer className="flex items-center gap-3">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-xl shadow-sm"
                style={{ background: "#f0f7e6" }}
              >
                🌺
              </div>
              <span className="font-semibold text-gray-700 not-italic">
                {t("quote.author")}
              </span>
            </footer>
          </blockquote>
        </div>

      </div>
    </section>
  );
}
