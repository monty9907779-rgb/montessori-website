"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations, useLocale } from "next-intl";
import { Menu, X, Globe, LogIn } from "lucide-react";
import { parentPortalUrl } from "@/lib/legacy-platform";

const links = ["home", "about", "programs", "curriculum", "methodology", "dailyLife", "gallery", "roles", "contact"] as const;

export default function Navbar() {
  const t = useTranslations("nav");
  const locale = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const altLocale = locale === "ar" ? "en" : "ar";
  const altPath = pathname.replace(`/${locale}`, `/${altLocale}`);

  const getHref = (key: string) => {
    if (key === "home") return `/${locale}`;
    return `/${locale}#${key}`;
  };

  return (
    <header
      className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 h-16 md:h-20 ${
        scrolled ? "bg-white/95 backdrop-blur-md shadow-md" : "bg-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 md:px-8 h-full flex items-center justify-between gap-4">
        {/* Logo */}
        <Link href={`/${locale}`} className="flex items-center gap-3 shrink-0">
          <div className="w-10 h-10 rounded-xl bg-montessori flex items-center justify-center shadow-md">
            <span className="text-white text-lg font-bold">ب</span>
          </div>
          <div className="hidden sm:block">
            <div
              className={`font-bold text-base leading-tight ${
                scrolled ? "text-primary-600" : "text-white"
              }`}
              style={{ color: scrolled ? "#2d5016" : undefined }}
            >
              {locale === "ar" ? "حضانة كوكب الطفل الحر" : "Planet of the Free Child"}
            </div>
            <div
              className={`text-xs ${scrolled ? "text-gray-500" : "text-green-100"}`}
            >
              {locale === "ar" ? "مونتيسوري جدة" : "Montessori Jeddah"}
            </div>
          </div>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden lg:flex items-center gap-1">
          {links.map((key) => (
            <a
              key={key}
              href={getHref(key)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                scrolled
                  ? "text-gray-700 hover:text-primary-600 hover:bg-primary-50"
                  : "text-white/90 hover:text-white hover:bg-white/10"
              }`}
              style={
                scrolled
                  ? { "--tw-text-opacity": "1" } as React.CSSProperties
                  : undefined
              }
            >
              {t(key)}
            </a>
          ))}
        </nav>

        {/* Right actions */}
        <div className="flex items-center gap-2">
          {/* Language toggle */}
          <Link
            href={altPath}
            className={`hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition-all ${
              scrolled
                ? "border-primary-200 text-primary-700 hover:bg-primary-50"
                : "border-white/30 text-white hover:bg-white/10"
            }`}
          >
            <Globe size={14} />
            {altLocale === "ar" ? "عربي" : "EN"}
          </Link>

          {/* Parent portal from the legacy Odoo platform */}
          <a
            href={parentPortalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={`hidden lg:flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
              scrolled
                ? "text-primary-700 hover:bg-primary-50"
                : "text-white/90 hover:text-white hover:bg-white/10"
            }`}
          >
            <LogIn size={15} />
            {t("parentPortal")}
          </a>

          {/* CTA */}
          <a
            href={`/${locale}#contact`}
            className="hidden md:flex items-center px-4 py-2 rounded-xl text-sm font-semibold text-white transition-all hover:scale-105 shadow-md"
            style={{ background: "#2d5016" }}
          >
            {locale === "ar" ? "سجّل الآن" : "Enroll Now"}
          </a>

          {/* Mobile toggle */}
          <button
            onClick={() => setOpen(!open)}
            className={`lg:hidden p-2 rounded-lg ${
              scrolled ? "text-gray-700" : "text-white"
            }`}
            aria-label="Toggle menu"
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="lg:hidden bg-white border-t border-gray-100 shadow-xl">
          <div className="px-4 py-4 flex flex-col gap-1">
            {links.map((key) => (
              <a
                key={key}
                href={getHref(key)}
                onClick={() => setOpen(false)}
                className="px-4 py-3 rounded-lg text-gray-700 font-medium hover:bg-primary-50 hover:text-primary-700 transition-colors"
              >
                {t(key)}
              </a>
            ))}
            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
              <Link
                href={altPath}
                className="flex items-center gap-2 px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600"
              >
                <Globe size={14} />
                {altLocale === "ar" ? "عربي" : "English"}
              </Link>
              <a
                href={`/${locale}#contact`}
                className="px-5 py-2 rounded-xl text-sm font-semibold text-white"
                style={{ background: "#2d5016" }}
                onClick={() => setOpen(false)}
              >
                {locale === "ar" ? "سجّل الآن" : "Enroll Now"}
              </a>
            </div>
            <a
              href={parentPortalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 flex items-center justify-center gap-2 rounded-lg border border-primary-200 px-4 py-3 text-sm font-semibold text-primary-700 hover:bg-primary-50"
              onClick={() => setOpen(false)}
            >
              <LogIn size={16} />
              {t("parentPortal")}
            </a>
          </div>
        </div>
      )}
    </header>
  );
}
