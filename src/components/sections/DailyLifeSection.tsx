import { useTranslations } from "next-intl";
import { Sun, Puzzle, Trees, Utensils, BookOpen, Palette, Leaf, Users, Sparkles } from "lucide-react";
import PhotoFrame from "@/components/ui/PhotoFrame";

const scheduleIndices = [0, 1, 2, 3, 4, 5] as const;
const scheduleIcons = [Sun, Puzzle, Trees, Utensils, BookOpen, Palette] as const;

const featureIndices = [0, 1, 2, 3, 4] as const;
const featureIcons = [Sun, Leaf, Users, BookOpen, Sparkles] as const;

export default function DailyLifeSection() {
  const t = useTranslations("dailyLife");
  const common = useTranslations("common");

  return (
    <section id="daily-life" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <span className="badge surface-warm text-primary-600">{t("badge")}</span>
          <h2 className="section-title mt-4 text-gray-900">{t("title")}</h2>
          <p className="text-gray-500 text-lg max-w-2xl mx-auto leading-relaxed mt-4">
            {t("subtitle")}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-start">
          {/* LEFT — Daily schedule timeline */}
          <div>
            <h3 className="text-xl font-bold mb-8 text-primary-600">{t("scheduleTitle")}</h3>
            <ol className="relative space-y-0">
              {scheduleIndices.map((i) => {
                const Icon = scheduleIcons[i];
                const isLast = i === scheduleIndices[scheduleIndices.length - 1];
                return (
                  <li key={i} className="relative flex gap-5 pb-8">
                    {!isLast && (
                      <div
                        className="absolute start-5 top-10 bottom-0 w-0.5 bg-primary-300 opacity-30"
                        aria-hidden="true"
                      />
                    )}
                    <div className="icon-tile relative z-10 h-10 w-10 border-2 border-white shadow">
                      <Icon size={18} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2 mb-1">
                        <span className="inline-block rounded-full bg-primary-600 px-3 py-0.5 text-xs font-bold text-white">
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

          {/* RIGHT — Environment card + real classroom photo */}
          <div className="flex flex-col gap-6">
            <div className="surface-warm overflow-hidden rounded-3xl border border-gray-100 shadow-lg">
              <div className="surface-forest px-7 py-6">
                <h3 className="text-xl font-bold text-white mb-1">{t("environment.title")}</h3>
                <p className="text-white/80 text-sm leading-relaxed">{t("environment.desc")}</p>
              </div>
              <ul className="px-7 py-6 space-y-4">
                {featureIndices.map((i) => {
                  const Icon = featureIcons[i];
                  return (
                    <li key={i} className="flex items-start gap-3">
                      <span className="icon-tile flex-shrink-0 bg-white shadow-sm">
                        <Icon size={18} />
                      </span>
                      <span className="text-gray-700 text-sm leading-relaxed pt-1.5">
                        {t(`environment.features.${i}`)}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>

            <PhotoFrame
              alt={t("environmentPhotoAlt")}
              comingSoonLabel={common("comingSoonPhoto")}
              aspect="video"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
