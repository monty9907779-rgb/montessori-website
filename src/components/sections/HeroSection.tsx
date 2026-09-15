import { useTranslations, useLocale } from "next-intl";
import PhotoFrame from "@/components/ui/PhotoFrame";

const stats = [
  { key: "years", value: "+١٠", valueEn: "10+" },
  { key: "children", value: "+٧٠", valueEn: "70+" },
  { key: "programs", value: "٤", valueEn: "4" },
  { key: "teachers", value: "+٢٠", valueEn: "20+" },
];

export default function HeroSection() {
  const t = useTranslations("hero");
  const common = useTranslations("common");
  const locale = useLocale();
  const isAr = locale === "ar";
  const secondaryHref = isAr ? "/wa/" : "#contact";

  return (
    <section
      id="home"
      className="surface-forest relative overflow-hidden pb-20 pt-28 md:pb-28 md:pt-36"
    >
      <div
        className="ambient-blob ambient-blob--a -top-24 -start-16 h-80 w-80 bg-accent/20"
        aria-hidden="true"
      />
      <div
        className="ambient-blob ambient-blob--b -bottom-28 -end-10 h-96 w-96 bg-primary-light/25"
        aria-hidden="true"
      />

      <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-12 px-4 md:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
        <div>
          <span className="badge animate-fade-in border border-white/20 bg-white/10 text-white">
            {t("badge")}
          </span>

          <h1 className="mt-6 animate-slide-up text-display text-white [animation-delay:100ms]">
            {t("headline")}
          </h1>

          <p className="mt-6 max-w-xl animate-slide-up text-lg leading-relaxed text-white/85 [animation-delay:200ms] md:text-xl">
            {t("subheadline")}
          </p>

          <div
            className={`mt-9 flex animate-slide-up flex-wrap gap-4 [animation-delay:300ms] ${
              isAr ? "flex-row-reverse justify-end" : ""
            }`}
          >
            <a href="#programs" className="pill-btn pill-btn--primary hover:scale-105">
              {t("cta")}
            </a>
            <a href={secondaryHref} className="pill-btn pill-btn--outline text-white hover:scale-105">
              {t("ctaSecondary")}
            </a>
          </div>

          <dl className="mt-14 grid animate-slide-up grid-cols-2 gap-x-8 gap-y-6 [animation-delay:400ms] sm:grid-cols-4">
            {stats.map(({ key, value, valueEn }) => (
              <div key={key} className="transition-transform duration-300 hover:-translate-y-1">
                <dt className="sr-only">{t(`stats.${key}`)}</dt>
                <dd className="text-3xl font-black text-white">
                  {isAr ? value : valueEn}
                </dd>
                <div className="mt-1 text-xs text-white/70">{t(`stats.${key}`)}</div>
              </div>
            ))}
          </dl>
        </div>

        <PhotoFrame
          alt={t("photoAlt")}
          comingSoonLabel={common("comingSoonPhoto")}
          aspect="portrait"
          priority
          className="w-full max-w-md animate-fade-in justify-self-center transition-transform duration-500 [animation-delay:150ms] hover:scale-[1.02] lg:justify-self-end"
        />
      </div>
    </section>
  );
}
