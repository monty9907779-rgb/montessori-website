import { useTranslations } from "next-intl";

type Platform = {
  key: string;
  name: string;
  emoji: string;
  handle: string;
  color: string;
  href: string;
};

const platforms: Platform[] = [
  {
    key:    "instagram",
    name:   "Instagram",
    emoji:  "📸",
    handle: "@montessori_nursery",
    color:  "linear-gradient(135deg, #833ab4 0%, #fd1d1d 50%, #fcb045 100%)",
    href:   "https://www.instagram.com/montessori_nursery/",
  },
  {
    key:    "facebook",
    name:   "Facebook",
    emoji:  "👍",
    handle: "Montessori Nursery",
    color:  "linear-gradient(135deg, #1877F2 0%, #0C63D4 100%)",
    href:   "https://www.facebook.com/p/Montessori-nursery-100063063920027/",
  },
  {
    key:    "whatsapp",
    name:   "WhatsApp",
    emoji:  "💬",
    handle: "+966 541558173",
    color:  "linear-gradient(135deg, #25D366 0%, #128C7E 100%)",
    href:   "https://wa.me/966541558173",
  },
];

export default function FollowUsSection() {
  const t = useTranslations("followUs");

  return (
    <section
      id="follow"
      className="section-padding"
      style={{ background: "#1a3009" }}
    >
      <div className="max-w-7xl mx-auto">
        {/* Decorative top accent */}
        <div className="flex justify-center mb-4">
          <span
            className="badge"
            style={{ background: "rgba(245,166,35,0.15)", color: "#f5a623", borderColor: "rgba(245,166,35,0.3)" }}
          >
            ✨ {t("badge")}
          </span>
        </div>

        {/* Title */}
        <h2 className="section-title text-center text-white mb-4 animate-slide-up">
          {t("title")}
        </h2>

        {/* Subtitle */}
        <p className="text-center text-green-300 text-lg max-w-xl mx-auto mb-14 animate-fade-in">
          {t("subtitle")}
        </p>

        {/* Platform Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {platforms.map((platform) => (
            <div
              key={platform.key}
              className="rounded-3xl p-7 flex flex-col items-center text-center transition-all duration-300 hover:-translate-y-2 hover:shadow-2xl border"
              style={{
                background: "rgba(255,255,255,0.05)",
                borderColor: "rgba(255,255,255,0.1)",
              }}
            >
              {/* Icon */}
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl shadow-lg mb-4"
                style={{ background: platform.color }}
              >
                {platform.emoji}
              </div>

              {/* Platform Name */}
              <h3 className="text-white font-bold text-lg mb-1">
                {platform.name}
              </h3>

              {/* Handle */}
              <p className="text-green-300 text-sm mb-5 font-mono">
                {platform.handle}
              </p>

              {/* Follow Button */}
              <a
                href={platform.href}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-2.5 rounded-xl text-sm font-bold text-white text-center transition-all hover:scale-105 active:scale-95 shadow-md"
                style={{ background: "#f5a623" }}
              >
                {t("cta")}
              </a>
            </div>
          ))}
        </div>

        {/* Divider */}
        <div className="mt-16 border-t border-white/10" />

        {/* Copyright */}
        <p className="text-center text-green-600 text-xs mt-6">
          &copy; {new Date().getFullYear()} Planet of the Free Child Nursery — Jeddah, Saudi Arabia.{" "}
            {t("copyright")}
        </p>
      </div>
    </section>
  );
}
