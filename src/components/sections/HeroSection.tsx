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
      <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-12 px-4 md:px-8 lg:grid-cols-[1.15fr_0.85fr] lg:items-center">
        <div>
          <span className="badge border border-white/20 bg-white/10 text-white">
            {t("badge")}
          </span>

          <h1 className="mt-6 text-display text-white">{t("headline")}</h1>

          <p className="mt-6 max-w-xl text-lg leading-relaxed text-white/85 md:text-xl">
            {t("subheadline")}
          </p>

          <div
            className={`mt-9 flex flex-wrap gap-4 ${
              isAr ? "flex-row-reverse justify-end" : ""
            }`}
          >
            <a href="#programs" className="pill-btn pill-btn--primary">
              {t("cta")}
            </a>
            <a href={secondaryHref} className="pill-btn pill-btn--outline text-white">
              {t("ctaSecondary")}
            </a>
          </div>

          <dl className="mt-14 grid grid-cols-2 gap-x-8 gap-y-6 sm:grid-cols-4">
            {stats.map(({ key, value, valueEn }) => (
              <div key={key}>
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
          className="w-full max-w-md justify-self-center lg:justify-self-end"
        />
      </div>
    </section>
  );
}
