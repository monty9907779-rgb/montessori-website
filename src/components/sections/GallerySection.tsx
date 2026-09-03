"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";

const CATEGORY_KEYS = ["all", "activities", "environment", "events", "learning"] as const;
type CategoryKey = (typeof CATEGORY_KEYS)[number];

interface GalleryTile {
  id: number;
  category: Exclude<CategoryKey, "all">;
  gradient: string;
  emoji: string;
  labelKey: string;
}

const TILES: GalleryTile[] = [
  {
    id: 1,
    category: "activities",
    gradient: "linear-gradient(135deg, #2d5016 0%, #5aa01e 100%)",
    emoji: "🎨",
    labelKey: "artCraft",
  },
  {
    id: 2,
    category: "environment",
    gradient: "linear-gradient(135deg, #1565c0 0%, #1e88e5 100%)",
    emoji: "🏫",
    labelKey: "classroom",
  },
  {
    id: 3,
    category: "learning",
    gradient: "linear-gradient(135deg, #f5a623 0%, #ffca56 100%)",
    emoji: "📖",
    labelKey: "reading",
  },
  {
    id: 4,
    category: "events",
    gradient: "linear-gradient(135deg, #6a1b9a 0%, #ab47bc 100%)",
    emoji: "🎉",
    labelKey: "celebration",
  },
  {
    id: 5,
    category: "activities",
    gradient: "linear-gradient(135deg, #3d6b20 0%, #7cb342 100%)",
    emoji: "🌱",
    labelKey: "garden",
  },
  {
    id: 6,
    category: "learning",
    gradient: "linear-gradient(135deg, #e65100 0%, #ff9800 100%)",
    emoji: "🔢",
    labelKey: "maths",
  },
  {
    id: 7,
    category: "environment",
    gradient: "linear-gradient(135deg, #00695c 0%, #26a69a 100%)",
    emoji: "🌿",
    labelKey: "nature",
  },
  {
    id: 8,
    category: "events",
    gradient: "linear-gradient(135deg, #c62828 0%, #ef5350 100%)",
    emoji: "🎊",
    labelKey: "yearEnd",
  },
];

export default function GallerySection() {
  const t = useTranslations("gallery");
  const locale = useLocale();
  const isAr = locale === "ar";

  const [activeCategory, setActiveCategory] = useState<CategoryKey>("all");

  const visibleTiles =
    activeCategory === "all"
      ? TILES
      : TILES.filter((tile) => tile.category === activeCategory);

  return (
    <section id="gallery" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        {/* Badge */}
        <div className="flex justify-center mb-4">
          <span
            className="badge"
            style={{ background: "#f0f7e6", color: "#2d5016" }}
          >
            🖼️ {t("badge")}
          </span>
        </div>

        {/* Heading */}
        <h2 className="section-title text-center text-gray-900 mb-4">
          {t("title")}
        </h2>
        <p className="text-center text-gray-500 text-lg max-w-xl mx-auto mb-10 leading-relaxed">
          {t("subtitle")}
        </p>

        {/* Category Filter Pills */}
        <div
          className={`flex flex-wrap gap-2 justify-center mb-10 ${
            isAr ? "flex-row-reverse" : ""
          }`}
        >
          {CATEGORY_KEYS.map((cat) => {
            const isActive = activeCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className="px-5 py-2 rounded-full text-sm font-semibold transition-all duration-200 hover:scale-105 active:scale-95 focus-visible:outline-none focus-visible:ring-2 min-h-[44px]"
                aria-pressed={isActive}
                aria-label={`${t(`categories.${cat}`)} ${isActive ? '(selected)' : ''}`}
                style={
                  isActive
                    ? {
                        background: "#2d5016",
                        color: "#fff",
                        boxShadow: "0 4px 14px rgba(45,80,22,0.3)",
                      }
                    : {
                        background: "#f0f7e6",
                        color: "#2d5016",
                        border: "1.5px solid #c8e6a0",
                      }
                }
              >
                {t(`categories.${cat}`)}
              </button>
            );
          })}
        </div>

        {/* Masonry-style tile grid */}
        <div
          className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4"
          style={{ minHeight: "300px" }}
        >
          {visibleTiles.map((tile) => (
            <div
              key={tile.id}
              className="group relative aspect-square rounded-2xl overflow-hidden cursor-pointer shadow-md hover:shadow-xl transition-all duration-300 hover:scale-[1.03]"
              style={{ background: tile.gradient }}
            >
              {/* Subtle dark overlay on hover */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all duration-300 rounded-2xl" />

              {/* Content */}
              <div className="relative h-full flex flex-col items-center justify-center gap-3 p-4">
                {/* Emoji */}
                <span
                  className="text-4xl sm:text-5xl drop-shadow-lg transition-transform duration-300 group-hover:scale-110"
                  role="img"
                  aria-label={t(`tiles.${tile.labelKey}`)}
                >
                  {tile.emoji}
                </span>

                {/* Label pill */}
                <span className="text-white text-xs sm:text-sm font-semibold px-3 py-1 rounded-full bg-black/25 backdrop-blur-sm text-center leading-tight">
                  {t(`tiles.${tile.labelKey}`)}
                </span>
              </div>

              {/* Corner shine accent */}
              <div className="absolute top-0 start-0 w-16 h-16 rounded-br-full bg-white/10" />
            </div>
          ))}

          {/* Empty-state if somehow no tiles match */}
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
