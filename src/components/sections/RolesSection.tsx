import { useTranslations, useLocale } from "next-intl";
import { UserCog, GraduationCap, Handshake, Award, ClipboardList, Briefcase } from "lucide-react";

type RoleKey = "director" | "lead_teacher" | "assistant" | "specialist" | "coordinator" | "admin";

const roleIcons: Record<RoleKey, typeof UserCog> = {
  director: UserCog,
  lead_teacher: GraduationCap,
  assistant: Handshake,
  specialist: Award,
  coordinator: ClipboardList,
  admin: Briefcase,
};

const roleKeys: RoleKey[] = ["director", "lead_teacher", "assistant", "specialist", "coordinator", "admin"];

export default function RolesSection() {
  const t = useTranslations("roles");
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <section id="team" className="section-padding bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-center mb-4">
          <span className="badge surface-warm text-primary-600">{t("badge")}</span>
        </div>

        <h2 className="section-title mt-4 text-center text-gray-900">{t("title")}</h2>
        <p className="text-center text-gray-500 text-lg max-w-2xl mx-auto mb-14 mt-4">
          {t("subtitle")}
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {roleKeys.map((key) => {
            const Icon = roleIcons[key];
            return (
              <div
                key={key}
                className="card-hover flex items-start gap-4 rounded-2xl border border-gray-100 bg-white p-6 shadow-sm"
              >
                <div className="icon-tile icon-tile--lg">
                  <Icon size={24} />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-primary-600">
                    {t(`items.${key}.title`)}
                  </h3>
                  <p
                    className="mt-1 text-gray-500 text-sm leading-relaxed"
                    dir={isAr ? "rtl" : "ltr"}
                  >
                    {t(`items.${key}.desc`)}
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        <div className="surface-forest mt-16 flex flex-col items-center justify-between gap-6 rounded-3xl px-8 py-10 shadow-lg md:flex-row">
          <div className="text-center md:text-start">
            <p className="text-white/70 text-sm font-medium uppercase tracking-widest mb-2">
              {t("hiring.eyebrow")}
            </p>
            <h3 className="text-2xl md:text-3xl font-black text-white">
              {t("hiring.title")}
            </h3>
            <p className="text-white/80 mt-2 text-sm max-w-md">{t("hiring.body")}</p>
          </div>
          <a href="#contact" className="pill-btn pill-btn--primary shrink-0 whitespace-nowrap">
            {t("hiring.cta")}
          </a>
        </div>
      </div>
    </section>
  );
}
