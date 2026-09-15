"use client";

import { useState } from "react";
import Image from "next/image";
import { useTranslations, useLocale } from "next-intl";
import PhotoFrame from "@/components/ui/PhotoFrame";
import Reveal from "@/components/ui/Reveal";

const CATEGORY_KEYS = ["all", "activities", "environment", "events", "learning"] as const;
type CategoryKey = (typeof CATEGORY_KEYS)[number];

interface GalleryTile {
  id: number;
  category: Exclude<CategoryKey, "all">;
  labelKey: string;
  /** يتضاف لما المالك يوافق على صورة حقيقية — لحد ذلك تفضل undefined فتظهر حالة "قريبًا". */
  src?: string;
}

const TILES: GalleryTile[] = [
  { id: 1, category: "activities", labelKey: "artCraft" },
  { id: 2, category: "environment", labelKey: "classroom" },
  { id: 3, category: "learning", labelKey: "reading" },
  { id: 4, category: "events", labelKey: "celebration" },
  { id: 5, category: "activities", labelKey: "garden" },
  { id: 6, category: "learning", labelKey: "maths" },
  { id: 7, category: "environment", labelKey: "nature" },
  { id: 8, category: "events", labelKey: "yearEnd" },
];

export default function GallerySection() {
  const t = useTranslations("gallery");
  const common = useTranslations("common");
  const locale = useLocale();
  const isAr = locale === "ar";

  const [activeCategory, setActiveCategory] = useState<CategoryKey>("all");

  const visibleTiles =
    activeCategory === "all" ? TILES : TILES.filter((tile) => tile.category === activeCategory);

  return (
    <section id="gallery" className="relative section-padding bg-white">
      <Image
        src="/decor/section-divider.svg"
        alt=""
        aria-hidden="true"
        width={220}
        height={160}
        className="pointer-events-none absolute -top-4 end-0 w-28 rotate-90 opacity-60"
      />
      <div className="max-w-7xl mx-auto">
        <Reveal>
          <div className="flex justify-center mb-4">
            <span className="badge surface-warm text-primary-600">{t("badge")}</span>
          </div>

          <h2 className="section-title mt-4 text-center text-gray-900">{t("title")}</h2>
          <p className="text-center text-gray-500 text-lg max-w-xl mx-auto mb-10 mt-4">
            {t("subtitle")}
          </p>
        </Reveal>

        <div className={`flex flex-wrap gap-2 justify-center mb-10 ${isAr ? "flex-row-reverse" : ""}`}>
          {CATEGORY_KEYS.map((cat) => {
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`min-h-[44px] rounded-full px-5 py-2 text-sm font-semibold transition-all hover:scale-105 focus-visible:outline-none focus-visible:ring-2 ${
                  isActive
                    ? "bg-primary-600 text-white shadow-md"
                    : "surface-warm text-primary-600 border border-primary-200"
                }`}
                aria-pressed={isActive}
                aria-label={`${t(`categories.${cat}`)} ${isActive ? "(selected)" : ""}`}
              >
                {t(`categories.${cat}`)}
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {visibleTiles.map((tile, i) => (
            <Reveal key={tile.id} delay={((i % 4) + 1) as 1 | 2 | 3 | 4} className="flex flex-col gap-2">
              <PhotoFrame
                src={tile.src}
                alt={t(`tiles.${tile.labelKey}`)}
                comingSoonLabel={common("comingSoonPhoto")}
                aspect="square"
                className="transition-transform duration-300 hover:scale-[1.03]"
              />
              <span className="text-center text-sm font-medium text-gray-600">
                {t(`tiles.${tile.labelKey}`)}
              </span>
            </Reveal>
          ))}

          {visibleTiles.length === 0 && (
            <div className="col-span-full flex items-center justify-center py-20 text-gray-400 text-sm">
              {t("empty")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
