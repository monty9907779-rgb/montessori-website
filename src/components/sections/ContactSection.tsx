"use client";

import { useState } from "react";
import { useTranslations, useLocale } from "next-intl";
import { MapPin, Phone, Mail, Clock } from "lucide-react";

type FormState = {
  name: string;
  email: string;
  phone: string;
  childAge: string;
  program: string;
  message: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

const initialForm: FormState = {
  name: "",
  email: "",
  phone: "",
  childAge: "",
  program: "",
  message: "",
};

const programOptions = [
  { value: "infants",  labelEn: "Nido (Infants 3–18 mo)",    labelAr: "نيدو (رضع ٣–١٨ شهرًا)" },
  { value: "toddlers", labelEn: "Toddlers (18 mo – 3 yr)",   labelAr: "الأطفال الصغار (١٨ شهر – ٣ سنوات)" },
  { value: "casa",     labelEn: "Casa dei Bambini (3–6 yr)",  labelAr: "كاسا دي بامبيني (٣–٦ سنوات)" },
  { value: "prep",     labelEn: "School Preparation (5–6 yr)",labelAr: "التهيئة المدرسية (٥–٦ سنوات)" },
];

export default function ContactSection() {
  const t = useTranslations("contact");
  const locale = useLocale();
  const isAr = locale === "ar";

  const [form, setForm] = useState<FormState>(initialForm);
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const validate = (): boolean => {
    const newErrors: FormErrors = {};
    if (!form.name.trim())    newErrors.name    = isAr ? "الاسم مطلوب"          : "Name is required";
    if (!form.email.trim())   newErrors.email   = isAr ? "البريد الإلكتروني مطلوب" : "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
                              newErrors.email   = isAr ? "بريد إلكتروني غير صالح" : "Invalid email address";
    if (!form.phone.trim())   newErrors.phone   = isAr ? "رقم الهاتف مطلوب"     : "Phone is required";
    if (!form.program)        newErrors.program = isAr ? "يرجى اختيار البرنامج" : "Please select a program";
    if (!form.message.trim()) newErrors.message = isAr ? "الرسالة مطلوبة"       : "Message is required";
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
    if (errors[name as keyof FormState]) {
      setErrors((prev) => ({ ...prev, [name]: undefined }));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);

    try {
      const response = await fetch("/api/contact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await response.json();

      if (response.ok) {
        setSubmitted(true);
        setForm(initialForm);
        setErrors({});
      } else {
        console.error("Form submission error:", data.error);
        alert(t("errorMessage"));
      }
    } catch (error) {
      console.error("Network error:", error);
      alert(t("errorMessage"));
    } finally {
      setLoading(false);
    }
  };

  const inputBase =
    "w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:border-transparent transition-all";
  const inputFocus = "focus:ring-[#2d5016]";
  const errorClass = "border-red-400 focus:ring-red-400";

  return (
    <section id="contact" className="section-padding bg-white">
      <div className="max-w-7xl mx-auto">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-start">
          {/* ── Left: Info ── */}
          <div>
            {/* Badge */}
            <div className="flex mb-4">
              <span className="badge" style={{ background: "#f0f7e6", color: "#2d5016" }}>
                📍 {t("badge")}
              </span>
            </div>

            <h2 className="section-title text-gray-900 mb-4 animate-slide-up">
              {t("title")}
            </h2>
            <p className="text-gray-500 text-lg leading-relaxed mb-10 animate-fade-in">
              {t("subtitle")}
            </p>

            {/* Info Items */}
            <div className="space-y-5 mb-10">
              {/* Address */}
              <div className="flex gap-4 items-start">
                <div
                  className="shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center shadow-sm"
                  style={{ background: "#f0f7e6" }}
                >
                  <MapPin size={20} style={{ color: "#2d5016" }} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-0.5">
                    {isAr ? "العنوان" : "Address"}
                  </p>
                  <p className="text-gray-700 text-sm leading-relaxed">
                    {t("info.address")}
                  </p>
                </div>
              </div>

              {/* Phone */}
              <div className="flex gap-4 items-start">
                <div
                  className="shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center shadow-sm"
                  style={{ background: "#f0f7e6" }}
                >
                  <Phone size={20} style={{ color: "#2d5016" }} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-0.5">
                    {isAr ? "الهاتف" : "Phone"}
                  </p>
                  <a
                    href={`tel:${t("info.phone")}`}
                    className="text-sm font-medium hover:underline"
                    style={{ color: "#2d5016" }}
                  >
                    {t("info.phone")}
                  </a>
                </div>
              </div>

              {/* Email */}
              <div className="flex gap-4 items-start">
                <div
                  className="shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center shadow-sm"
                  style={{ background: "#f0f7e6" }}
                >
                  <Mail size={20} style={{ color: "#2d5016" }} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-0.5">
                    {isAr ? "البريد الإلكتروني" : "Email"}
                  </p>
                  <a
                    href={`mailto:${t("info.email")}`}
                    className="text-sm font-medium hover:underline"
                    style={{ color: "#2d5016" }}
                  >
                    {t("info.email")}
                  </a>
                </div>
              </div>

              {/* Hours */}
              <div className="flex gap-4 items-start">
                <div
                  className="shrink-0 w-11 h-11 rounded-2xl flex items-center justify-center shadow-sm"
                  style={{ background: "#f0f7e6" }}
                >
                  <Clock size={20} style={{ color: "#2d5016" }} />
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-0.5">
                    {isAr ? "ساعات العمل" : "Working Hours"}
                  </p>
                  <p className="text-gray-700 text-sm leading-relaxed">
                    {t("info.hours")}
                  </p>
                </div>
              </div>
            </div>

            {/* Map Placeholder */}
            <div
              className="rounded-3xl overflow-hidden border border-gray-100 shadow-sm flex flex-col items-center justify-center gap-3 py-10 px-6 text-center"
              style={{ background: "#f0f7e6", minHeight: "180px" }}
            >
              <span className="text-5xl">📍</span>
              <p className="font-bold text-base" style={{ color: "#2d5016" }}>
                {isAr ? "روضة كوكب الطفل الحر" : "Planet of the Free Child Nursery"}
              </p>
              <p className="text-gray-500 text-sm">
                {isAr ? "(بداية منتسوري سابقاً)" : "(formerly Bedaya Montessori)"}
              </p>
              <a
                href="https://www.google.com/maps/place/%D8%B1%D9%88%D8%B6%D8%A9+%D9%83%D9%88%D9%83%D8%A8+%D8%A7%D9%84%D8%B7%D9%81%D9%84+%D8%A7%D9%84%D8%AD%D8%B1%E2%80%AD/@21.5795281,39.194829,673m/data=!3m2!1e3!4b1!4m6!3m5!1s0x15c3d18ac84c1d4d:0xaee1671b468377fb!8m2!3d21.5795281!4d39.194829!16s%2Fg%2F11s619kg25"
                target="_blank"
                rel="noopener noreferrer"
                aria-label={isAr ? "افتح الموقع في خرائط جوجل" : "Open location in Google Maps"}
                className="mt-1 text-xs font-semibold px-4 py-2 rounded-full border transition-all hover:scale-105 min-h-[44px] flex items-center justify-center"
                style={{ borderColor: "#2d5016", color: "#2d5016" }}
              >
                {t("mapLink")}
              </a>
            </div>
          </div>

          {/* ── Right: Form ── */}
          <div
            className="rounded-3xl p-8 md:p-10 shadow-xl border border-gray-100"
            style={{ background: "#fafafa" }}
          >
            {submitted ? (
              /* Success State */
              <div className="flex flex-col items-center justify-center text-center py-12 gap-4">
                <div
                  className="w-20 h-20 rounded-full flex items-center justify-center text-4xl shadow-lg"
                  style={{ background: "linear-gradient(135deg, #2d5016, #5aa01e)" }}
                >
                  ✅
                </div>
                <h3 className="text-2xl font-black" style={{ color: "#2d5016" }}>
                  {isAr ? "تم الإرسال بنجاح!" : "Message Sent!"}
                </h3>
                <p className="text-gray-500 text-sm max-w-xs leading-relaxed">
                  {isAr
                    ? "شكرًا لتواصلك معنا. سيتواصل معك فريقنا في أقرب وقت."
                    : "Thank you for reaching out! Our team will get back to you shortly."}
                </p>
                <button
                  onClick={() => { setForm(initialForm); setSubmitted(false); }}
                  className="mt-4 px-6 py-3 rounded-xl text-sm font-semibold text-white transition-all hover:scale-105"
                  style={{ background: "#f5a623" }}
                >
                  {isAr ? "إرسال رسالة أخرى" : "Send Another Message"}
                </button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} noValidate>
                <h3 className="text-xl font-black text-gray-900 mb-6">
                  {isAr ? "أرسل لنا رسالة" : "Send Us a Message"}
                </h3>

                <div className="space-y-4">
                  {/* Name */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
                      {t("form.name")} <span className="text-red-400">*</span>
                    </label>
                    <input
                      type="text"
                      name="name"
                      value={form.name}
                      onChange={handleChange}
                      placeholder={isAr ? "الاسم الكامل" : "Full Name"}
                      className={`${inputBase} ${inputFocus} ${errors.name ? errorClass : ""}`}
                      autoComplete="name"
                      aria-required="true"
                      aria-invalid={!!errors.name}
                      aria-describedby={errors.name ? "name-error" : undefined}
                    />
                    {errors.name && <p id="name-error" className="mt-1 text-xs text-red-500" role="alert">{errors.name}</p>}
                  </div>

                  {/* Email + Phone Row */}
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
                        {t("form.email")} <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="email"
                        name="email"
                        value={form.email}
                        onChange={handleChange}
                        placeholder="you@example.com"
                        className={`${inputBase} ${inputFocus} ${errors.email ? errorClass : ""}`}
                        autoComplete="email"
                        aria-required="true"
                        aria-invalid={!!errors.email}
                        aria-describedby={errors.email ? "email-error" : undefined}
                      />
                      {errors.email && <p id="email-error" className="mt-1 text-xs text-red-500" role="alert">{errors.email}</p>}
                    </div>
                    <div>
                      <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
                        {t("form.phone")} <span className="text-red-400">*</span>
                      </label>
                      <input
                        type="tel"
                        name="phone"
                        value={form.phone}
                        onChange={handleChange}
                        placeholder="+966 5X XXX XXXX"
                        className={`${inputBase} ${inputFocus} ${errors.phone ? errorClass : ""}`}
                        autoComplete="tel"
                        inputMode="numeric"
                        aria-required="true"
                        aria-invalid={!!errors.phone}
                        aria-describedby={errors.phone ? "phone-error" : undefined}
                      />
                      {errors.phone && <p id="phone-error" className="mt-1 text-xs text-red-500" role="alert">{errors.phone}</p>}
                    </div>
                  </div>

                  {/* Child Age + Program Row */}
                  <div className="grid sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
                        {t("form.childAge")}
                      </label>
                      <input
                        type="number"
                        name="childAge"
                        value={form.childAge}
                        onChange={handleChange}
                        min={0}
                        max={6}
                        placeholder={isAr ? "بالأشهر أو السنوات" : "Age (months/years)"}
                        className={`${inputBase} ${inputFocus}`}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
                        {t("form.program")} <span className="text-red-400">*</span>
                      </label>
                      <select
                        name="program"
                        value={form.program}
                        onChange={handleChange}
                        className={`${inputBase} ${inputFocus} ${errors.program ? errorClass : ""}`}
                        aria-required="true"
                        aria-invalid={!!errors.program}
                        aria-describedby={errors.program ? "program-error" : undefined}
                      >
                        <option value="">{isAr ? "اختر البرنامج" : "Select Program"}</option>
                        {programOptions.map((opt) => (
                          <option key={opt.value} value={opt.value}>
                            {isAr ? opt.labelAr : opt.labelEn}
                          </option>
                        ))}
                      </select>
                      {errors.program && <p id="program-error" className="mt-1 text-xs text-red-500" role="alert">{errors.program}</p>}
                    </div>
                  </div>

                  {/* Message */}
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-widest text-gray-500 mb-1.5">
                      {t("form.message")} <span className="text-red-400">*</span>
                    </label>
                    <textarea
                      name="message"
                      value={form.message}
                      onChange={handleChange}
                      rows={4}
                      placeholder={isAr ? "اكتب رسالتك هنا..." : "Write your message here..."}
                      className={`${inputBase} ${inputFocus} resize-none ${errors.message ? errorClass : ""}`}
                      aria-required="true"
                      aria-invalid={!!errors.message}
                      aria-describedby={errors.message ? "message-error" : undefined}
                    />
                    {errors.message && <p id="message-error" className="mt-1 text-xs text-red-500" role="alert">{errors.message}</p>}
                  </div>

                  {/* Submit */}
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-4 rounded-2xl text-base font-bold text-white shadow-lg transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-70 disabled:cursor-not-allowed"
                    style={{ background: loading ? "#c07d10" : "#f5a623" }}
                  >
                    {loading
                      ? (isAr ? "جارٍ الإرسال..." : "Sending...")
                      : t("form.submit")}
                  </button>

                  <p className="text-center text-xs text-gray-400">
                    {isAr
                      ? "سنرد عليك خلال 24 ساعة."
                      : "We'll respond within 24 hours."}
                  </p>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
