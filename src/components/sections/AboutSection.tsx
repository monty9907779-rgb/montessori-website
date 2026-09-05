import { useTranslations } from "next-intl";

const valueIcons = ["🤝", "🕊️", "❤️", "⭐"];
const valueKeys = ["respect", "freedom", "love", "excellence"] as const;

export default function AboutSection() {
  const t = useTranslations("about");

  return (
    <section id="about" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Badge */}
        <div className="flex justify-center mb-4">
          <span
            className="badge"
            style={{ background: "#f0f7e6", color: "#2d5016" }}
          >
            🌿 {t("badge")}
          </span>
        </div>

        <h2 className="section-title text-center text-gray-900 mb-4 animate-slide-up">
          {t("headline")}
        </h2>

        <div className="grid md:grid-cols-2 gap-12 mt-12 items-center">
          {/* Text */}
          <div className="space-y-5">
            <p className="text-gray-600 leading-relaxed text-lg">{t("body1")}</p>
            <p className="text-gray-600 leading-relaxed text-lg">{t("body2")}</p>

            {/* Decorative quote */}
            <blockquote
              className="border-s-4 ps-5 py-2 italic text-primary-700 text-lg font-medium"
              style={{ borderColor: "#2d5016", color: "#2d5016" }}
            >
              {'"The greatest gifts we can give our children are the roots of responsibility and the wings of independence."'}
              <footer className="text-sm font-normal text-gray-500 mt-1 not-italic">
                — Maria Montessori
              </footer>
            </blockquote>
          </div>

          {/* Visual card */}
          <div className="relative">
            <div
              className="rounded-3xl p-8 text-white shadow-2xl"
              style={{
                background:
                  "linear-gradient(135deg, #2d5016 0%, #3d6b20 50%, #5aa01e 100%)",
              }}
            >
              <div className="text-6xl mb-4">🏫</div>
              <h3 className="text-2xl font-bold mb-3">
                Bada&apos;a Early Childhood Center
              </h3>
              <p className="text-green-100 text-sm leading-relaxed">
                21°29&apos;9&quot;N, 39°11&apos;33&quot;E · Jeddah, KSA
              </p>

              <div className="mt-6 grid grid-cols-2 gap-3">
                {[
                  t("features.montessori"),
                  t("features.bilingual"),
                  t("features.ages"),
                  t("features.established")
                ].map((f) => (
                  <div
                    key={f}
                    className="bg-white/10 rounded-xl px-3 py-2 text-xs font-medium"
                  >
                    ✓ {f}
                  </div>
                ))}
              </div>
            </div>

            {/* Accent dot */}
            <div
              className="absolute -top-4 -end-4 w-20 h-20 rounded-full opacity-30"
              style={{ background: "#f5a623" }}
            />
          </div>
        </div>

        {/* Values */}
        <div className="mt-16">
          <h3 className="text-2xl font-bold text-center text-gray-800 mb-8">
            {t("values.title")}
          </h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {valueKeys.map((key, i) => (
              <div
                key={key}
                className="card-hover p-6 rounded-2xl border border-gray-100 bg-gray-50 text-center"
              >
                <div className="text-4xl mb-3">{valueIcons[i]}</div>
                <h4
                  className="font-bold text-lg mb-2"
                  style={{ color: "#2d5016" }}
                >
                  {t(`values.${key}.title`)}
                </h4>
                <p className="text-gray-500 text-sm leading-relaxed">
                  {t(`values.${key}.desc`)}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
