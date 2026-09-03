import { useTranslations, useLocale } from "next-intl";

type RoleKey = "director" | "lead_teacher" | "assistant" | "specialist" | "coordinator" | "admin";

const roleEmojis: Record<RoleKey, string> = {
  director: "👩‍💼",
  lead_teacher: "👩‍🏫",
  assistant: "🤝",
  specialist: "🎓",
  coordinator: "📋",
  admin: "💼",
};

const roleGradients: Record<RoleKey, string> = {
  director:    "linear-gradient(135deg, #2d5016 0%, #3d6b20 100%)",
  lead_teacher:"linear-gradient(135deg, #3d6b20 0%, #5aa01e 100%)",
  assistant:   "linear-gradient(135deg, #5aa01e 0%, #73bf27 100%)",
  specialist:  "linear-gradient(135deg, #f5a623 0%, #c07d10 100%)",
  coordinator: "linear-gradient(135deg, #2d5016 0%, #5aa01e 100%)",
  admin:       "linear-gradient(135deg, #c07d10 0%, #f5a623 100%)",
};

const roleKeys: RoleKey[] = ["director", "lead_teacher", "assistant", "specialist", "coordinator", "admin"];

export default function RolesSection() {
  const t = useTranslations("roles");
  const locale = useLocale();
  const isAr = locale === "ar";

  return (
    <section id="team" className="section-padding bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Badge */}
        <div className="flex justify-center mb-4">
          <span className="badge" style={{ background: "#f0f7e6", color: "#2d5016" }}>
            🌿 {t("badge")}
          </span>
        </div>

        {/* Title */}
        <h2 className="section-title text-center text-gray-900 mb-4 animate-slide-up">
          {t("title")}
        </h2>

        {/* Subtitle */}
        <p className="text-center text-gray-500 text-lg max-w-2xl mx-auto mb-14 animate-fade-in">
          {t("subtitle")}
        </p>

        {/* Team Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
          {roleKeys.map((key) => (
            <div
              key={key}
              className="card-hover bg-white rounded-3xl p-8 border border-gray-100 shadow-sm flex flex-col items-center text-center"
            >
              {/* Avatar */}
              <div
                className="w-20 h-20 rounded-full flex items-center justify-center text-4xl shadow-lg mb-5"
                style={{ background: roleGradients[key] }}
                aria-hidden="true"
              >
                {roleEmojis[key]}
              </div>

              {/* Name / Title */}
              <h3
                className="text-xl font-bold mb-1"
                style={{ color: "#2d5016" }}
              >
                {t(`items.${key}.title`)}
              </h3>

              {/* Decorative divider */}
              <div className="flex items-center gap-2 my-3">
                <span className="block w-8 h-0.5 rounded-full" style={{ background: "#f5a623" }} />
                <span className="text-xs" style={{ color: "#f5a623" }}>✦</span>
                <span className="block w-8 h-0.5 rounded-full" style={{ background: "#f5a623" }} />
              </div>

              {/* Description */}
              <p
                className="text-gray-500 text-sm leading-relaxed"
                dir={isAr ? "rtl" : "ltr"}
              >
                {t(`items.${key}.desc`)}
              </p>
            </div>
          ))}
        </div>

        {/* We Are Hiring Banner */}
        <div
          className="mt-16 rounded-3xl px-8 py-10 flex flex-col md:flex-row items-center justify-between gap-6 shadow-lg"
          style={{
            background: "linear-gradient(135deg, #2d5016 0%, #3d6b20 60%, #5aa01e 100%)",
          }}
        >
          <div className="text-center md:text-start">
            <p className="text-green-200 text-sm font-medium uppercase tracking-widest mb-2">
              Join Our Team
            </p>
            <h3 className="text-2xl md:text-3xl font-black text-white">
              We&apos;re Hiring Passionate Educators 🌱
            </h3>
            <p className="text-green-100 mt-2 text-sm max-w-md">
              If you love children and believe in the Montessori philosophy, we&apos;d love to meet you.
              Reach out and be part of our growing family in Jeddah.
            </p>
          </div>
          <a
            href="#contact"
            className="shrink-0 px-8 py-4 rounded-2xl text-base font-bold text-white shadow-2xl transition-all hover:scale-105 active:scale-95 whitespace-nowrap"
            style={{ background: "#f5a623" }}
          >
            Apply Now →
          </a>
        </div>
      </div>
    </section>
  );
}
