import { useTranslations } from "next-intl";
import Reveal from "@/components/ui/Reveal";

const stepIndices = [0, 1, 2, 3, 4] as const;

const stepAccentClass = [
  "bg-primary-600",
  "bg-primary-600",
  "bg-primary-500",
  "bg-accent",
  "bg-accent-dark",
] as const;

export default function MethodologySection() {
  const t = useTranslations("methodology");

  return (
    <section id="methodology" className="section-padding surface-warm">
      <div className="max-w-7xl mx-auto">
        <Reveal className="text-center mb-14">
          <span className="badge bg-white text-primary-600">{t("badge")}</span>
          <h2 className="section-title mt-4 text-gray-900">{t("title")}</h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed mt-4">
            {t("subtitle")}
          </p>
        </Reveal>

        <div className="relative">
          <div
            className="hidden lg:block absolute top-10 inset-x-32 h-0.5 bg-primary-300 opacity-40"
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 lg:gap-4 relative">
            {stepIndices.map((i) => (
              <Reveal
                key={i}
                delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                className="relative flex flex-col items-center text-center lg:px-2"
              >
                <div
                  className={`relative z-10 mb-5 flex h-20 w-20 items-center justify-center rounded-full border-4 border-white shadow-lg transition-transform duration-300 hover:scale-110 ${stepAccentClass[i]}`}
                >
                  <span className="text-white text-2xl font-black">
                    {t(`steps.${i}.step`)}
                  </span>
                </div>

                {i < 4 && (
                  <div
                    className={`lg:hidden absolute top-20 left-1/2 h-8 w-0.5 -translate-x-1/2 opacity-40 ${stepAccentClass[i + 1]}`}
                    aria-hidden="true"
                  />
                )}

                <h3 className="font-bold text-base mb-2 text-primary-600">
                  {t(`steps.${i}.title`)}
                </h3>
                <p className="text-gray-500 text-sm leading-relaxed">
                  {t(`steps.${i}.desc`)}
                </p>
              </Reveal>
            ))}
          </div>
        </div>

        <Reveal className="mt-16 max-w-3xl mx-auto">
          <blockquote className="relative rounded-3xl border-s-4 border-primary-600 bg-white p-8 shadow-md">
            <span
              className="absolute top-4 end-6 text-8xl font-serif leading-none text-primary-600 opacity-10 select-none"
              aria-hidden="true"
            >
              &ldquo;
            </span>
            <p className="relative z-10 text-xl md:text-2xl italic font-medium leading-relaxed mb-5 text-primary-600">
              &ldquo;{t("quote.text")}&rdquo;
            </p>
            <footer className="font-semibold text-gray-700 not-italic">
              {t("quote.author")}
            </footer>
          </blockquote>
        </Reveal>
      </div>
    </section>
  );
}
