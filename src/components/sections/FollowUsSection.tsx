import { useTranslations } from "next-intl";
import { Instagram, Facebook, MessageCircle } from "lucide-react";
import { siteFacts } from "@/lib/site-facts";

type Platform = {
  key: string;
  name: string;
  Icon: typeof Instagram;
  handle: string;
  href: string;
};

const platforms: Platform[] = [
  { key: "instagram", name: "Instagram", Icon: Instagram, handle: "@montessori_nursery", href: siteFacts.contact.instagram },
  { key: "facebook", name: "Facebook", Icon: Facebook, handle: "Montessori Nursery", href: "https://www.facebook.com/p/Montessori-nursery-100063063920027/" },
  { key: "whatsapp", name: "WhatsApp", Icon: MessageCircle, handle: siteFacts.contact.phoneDisplay, href: siteFacts.contact.whatsapp },
];

export default function FollowUsSection() {
  const t = useTranslations("followUs");

  return (
    <section id="follow" className="section-padding surface-forest">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-center mb-4">
          <span className="badge border border-white/20 bg-white/10 text-white">{t("badge")}</span>
        </div>

        <h2 className="section-title mt-4 text-center text-white">{t("title")}</h2>
        <p className="text-center text-white/70 text-lg max-w-xl mx-auto mb-14 mt-4">
          {t("subtitle")}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {platforms.map(({ key, name, Icon, handle, href }) => (
            <div
              key={key}
              className="flex flex-col items-center rounded-3xl border border-white/10 bg-white/5 p-7 text-center transition-transform hover:-translate-y-1"
            >
              <div className="icon-tile icon-tile--lg mb-4 bg-white/10 text-white">
                <Icon size={26} />
              </div>
              <h3 className="text-white font-bold text-lg mb-1">{name}</h3>
              <p className="text-white/70 text-sm mb-5 font-mono">{handle}</p>
              <a href={href} target="_blank" rel="noopener noreferrer" className="pill-btn pill-btn--primary w-full">
                {t("cta")}
              </a>
            </div>
          ))}
        </div>

        <div className="mt-16 border-t border-white/10" />

        <p className="text-center text-white/50 text-xs mt-6">
          &copy; {new Date().getFullYear()} Planet of the Free Child Nursery — Jeddah, Saudi Arabia. {t("copyright")}
        </p>
      </div>
    </section>
  );
}
