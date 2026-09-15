import { useTranslations } from "next-intl";
import Image from "next/image";
import { HandHeart, Feather, Heart, Sparkles, CheckCircle2 } from "lucide-react";
import PhotoFrame from "@/components/ui/PhotoFrame";
import Reveal from "@/components/ui/Reveal";

const valueIcons = [HandHeart, Feather, Heart, Sparkles];
const valueKeys = ["respect", "freedom", "love", "excellence"] as const;

export default function AboutSection() {
  const t = useTranslations("about");
  const common = useTranslations("common");

  return (
    <section id="about" className="relative section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        <Reveal>
          <span className="badge surface-warm text-primary-600">{t("badge")}</span>

          <h2 className="section-title mt-4 text-gray-900">{t("headline")}</h2>
        </Reveal>

        <div className="mt-12 grid items-center gap-12 md:grid-cols-2">
          <Reveal delay={1} className="space-y-5">
            <p className="text-gray-600 leading-relaxed text-lg">{t("body1")}</p>
            <p className="text-gray-600 leading-relaxed text-lg">{t("body2")}</p>

            <blockquote className="border-s-4 border-primary-600 ps-5 py-2 italic text-primary-600 text-lg font-medium">
              {'"The greatest gifts we can give our children are the roots of responsibility and the wings of independence."'}
              <footer className="text-sm font-normal text-gray-500 mt-1 not-italic">
                — Maria Montessori
              </footer>
            </blockquote>

            <ul className="grid grid-cols-2 gap-3 pt-2">
              {[
                t("features.montessori"),
                t("features.bilingual"),
                t("features.ages"),
                t("features.established"),
              ].map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-gray-700">
                  <CheckCircle2 size={16} className="shrink-0 text-primary-600" />
                  {f}
                </li>
              ))}
            </ul>
          </Reveal>

          <Reveal delay={2}>
            <PhotoFrame
              alt={t("photoAlt")}
              comingSoonLabel={common("comingSoonPhoto")}
              aspect="video"
              className="shadow-lg transition-transform duration-500 hover:scale-[1.02]"
            />
          </Reveal>
        </div>

        <div className="mt-16">
          <Reveal>
            <h3 className="text-2xl font-bold text-center text-gray-800 mb-8">
              {t("values.title")}
            </h3>
          </Reveal>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {valueKeys.map((key, i) => {
              const Icon = valueIcons[i];
              return (
                <Reveal
                  key={key}
                  delay={((i % 4) + 1) as 1 | 2 | 3 | 4}
                  className="card-hover p-6 rounded-2xl border border-gray-100 bg-gray-50 text-center"
                >
                  <div className="icon-tile icon-tile--lg mx-auto mb-3">
                    <Icon size={24} />
                  </div>
                  <h4 className="font-bold text-lg mb-2 text-primary-600">
                    {t(`values.${key}.title`)}
                  </h4>
                  <p className="text-gray-500 text-sm leading-relaxed">
                    {t(`values.${key}.desc`)}
                  </p>
                </Reveal>
              );
            })}
          </div>
        </div>
      </div>

      <Image
        src="/decor/section-divider.svg"
        alt=""
        aria-hidden="true"
        width={220}
        height={160}
        className="pointer-events-none absolute -bottom-6 start-1/2 w-40 -translate-x-1/2 opacity-70"
      />
    </section>
  );
}
