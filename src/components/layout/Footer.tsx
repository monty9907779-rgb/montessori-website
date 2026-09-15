import { useTranslations, useLocale } from "next-intl";
import Link from "next/link";
import { LogIn, MapPin, Phone, Mail, Instagram, Facebook, MessageCircle } from "lucide-react";
import { parentPortalUrl } from "@/lib/legacy-platform";
import { siteFacts } from "@/lib/site-facts";

export default function Footer() {
  const t = useTranslations("footer");
  const nav = useTranslations("nav");
  const locale = useLocale();

  const sections = [
    { key: "about", label: nav("about") },
    { key: "programs", label: nav("programs") },
    { key: "gallery", label: nav("gallery") },
    { key: "roles", label: nav("roles") },
    { key: "contact", label: nav("contact") },
  ];

  return (
    <footer className="bg-gray-900 text-gray-300">
      <div className="max-w-7xl mx-auto px-4 md:px-8 py-14 grid grid-cols-1 md:grid-cols-3 gap-10">
        {/* Brand */}
        <div>
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-montessori flex items-center justify-center">
              <span className="text-white font-bold text-lg">ك</span>
            </div>
            <div>
              <div className="text-white font-bold">
                {locale === "ar" ? siteFacts.name.ar : siteFacts.name.en}
              </div>
              <div className="text-xs text-gray-400">
                {locale === "ar" ? "مونتيسوري جدة" : "Montessori Jeddah"}
              </div>
            </div>
          </div>
          <p className="text-sm text-gray-400 leading-relaxed">{t("tagline")}</p>
        </div>

        {/* Quick links */}
        <div>
          <h3 className="text-white font-semibold mb-4">
            {locale === "ar" ? "روابط سريعة" : "Quick Links"}
          </h3>
          <ul className="space-y-2">
            {sections.map(({ key, label }) => (
              <li key={key}>
                <a
                  href={`/${locale}#${key}`}
                  className="text-sm text-gray-400 hover:text-white transition-colors"
                >
                  {label}
                </a>
              </li>
            ))}
            <li>
              <a href={`/${locale}/${locale === "ar" ? "hadana-qariba-minni" : "daycare-near-me-jeddah"}`} className="text-sm text-gray-400 hover:text-white transition-colors">
                {locale === "ar" ? "حضانة قريبة مني" : "Daycare Near Me"}
              </a>
            </li>
            <li>
              <a
                href={parentPortalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
              >
                <LogIn size={14} />
                {t("parentPortal")}
              </a>
            </li>
            <li>
              <Link
                href="/wa/"
                className="text-sm text-gray-400 hover:text-white transition-colors"
              >
                {locale === "ar" ? "صفحة التواصل" : "Contact page"}
              </Link>
            </li>
          </ul>
        </div>

        {/* Contact */}
        <div>
          <h3 className="text-white font-semibold mb-4">
            {locale === "ar" ? "تواصل معنا" : "Contact"}
          </h3>
          <ul className="space-y-2 text-sm text-gray-400">
            <li className="flex items-start gap-2">
              <MapPin size={16} className="mt-0.5 shrink-0" />
              <span>{locale === "ar" ? siteFacts.address.ar : siteFacts.address.en}</span>
            </li>
            <li className="flex items-center gap-2">
              <Phone size={16} className="shrink-0" />
              <span>{siteFacts.contact.phoneDisplay}</span>
            </li>
            <li className="flex items-center gap-2">
              <Mail size={16} className="shrink-0" />
              <span>{siteFacts.contact.email}</span>
            </li>
          </ul>
          {/* Social */}
          <div className="flex gap-3 mt-5">
            {[
              { label: "Instagram", Icon: Instagram, href: siteFacts.contact.instagram },
              { label: "Facebook", Icon: Facebook, href: "https://www.facebook.com/p/Montessori-nursery-100063063920027/" },
              { label: "WhatsApp", Icon: MessageCircle, href: siteFacts.contact.whatsapp },
            ].map(({ label, Icon, href }) => (
              <a
                key={label}
                href={href}
                aria-label={label}
                className="w-9 h-9 rounded-lg bg-gray-800 hover:bg-primary-600 flex items-center justify-center transition-colors"
              >
                <Icon size={16} />
              </a>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom bar */}
      <div className="border-t border-gray-800 py-5">
        <div className="max-w-7xl mx-auto px-4 md:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-gray-500">
          <span>
            © {new Date().getFullYear()} {locale === "ar" ? siteFacts.name.ar : siteFacts.name.en}. {t("rights")}.
          </span>
          <div className="flex gap-4">
            <a href="#" className="hover:text-gray-300 transition-colors">
              {t("links.privacy")}
            </a>
            <a href="#" className="hover:text-gray-300 transition-colors">
              {t("links.terms")}
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
