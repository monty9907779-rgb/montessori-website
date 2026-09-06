"use client";

import { useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Clock3,
  Mail,
  MapPin,
  MessageCircle,
  Phone,
  Send,
  Sparkles,
} from "lucide-react";

type FormState = {
  name: string;
  phone: string;
  childAge: string;
  program: string;
  message: string;
};

const initialForm: FormState = {
  name: "",
  phone: "",
  childAge: "",
  program: "",
  message: "",
};

const infoItems = [
  { label: "العنوان", value: "روضة كوكب الطفل الحر، حي الفيصلية، جدة" },
  { label: "الدوام", value: "الأحد إلى الخميس، من ٧:٣٠ صباحًا حتى ٣:٠٠ مساءً" },
  { label: "العمر", value: "من عمر سنتين إلى ٥ سنوات" },
  { label: "البريد", value: "info@montessori-ksa.com" },
  { label: "واتساب", value: "+966 54 155 8173" },
];

const askPoints = [
  "هل يوجد مكان متاح الآن؟",
  "ما البرنامج المناسب لعمر طفلي؟",
  "كم الرسوم حسب عدد الأيام؟",
  "هل يمكن حجز زيارة تعريفية؟",
];

const faqItems = [
  {
    q: "هل هذه الصفحة مجرد زر واتساب؟",
    a: "لا، هي صفحة تواصل كاملة فيها معلومات أساسية، نموذج سريع، وأسئلة شائعة تساعدك قبل الإرسال.",
  },
  {
    q: "ما أفضل شيء أكتبه في الرسالة؟",
    a: "اكتبي اسمك، عمر الطفل، والبرنامج الذي تفكرين فيه. هكذا نرد عليكِ بسرعة وبشكل أدق.",
  },
  {
    q: "هل يمكن حجز زيارة من هنا؟",
    a: "نعم، يمكنكِ فتح واتساب مباشرة أو إرسال النموذج، ونرتب لكِ الزيارة المناسبة.",
  },
  {
    q: "هل الصفحة تستحق الفهرسة؟",
    a: "نعم، لأنها تعرض محتوى فعليًا وواضحًا بدل صفحة تحويل قصيرة بلا قيمة مستقلة.",
  },
];

function buildWhatsappUrl(form: FormState) {
  const lines = [
    "السلام عليكم، أود الاستفسار عن التسجيل في روضة كوكب الطفل الحر.",
    form.name ? `الاسم: ${form.name}` : "",
    form.phone ? `رقم الجوال: ${form.phone}` : "",
    form.childAge ? `عمر الطفل: ${form.childAge}` : "",
    form.program ? `البرنامج المناسب: ${form.program}` : "",
    form.message ? `الرسالة: ${form.message}` : "",
    "شكرًا لكم.",
  ].filter(Boolean);

  return `https://wa.me/966541558173?text=${encodeURIComponent(lines.join("\n"))}`;
}

export default function WhatsappContactPage() {
  const [form, setForm] = useState<FormState>(initialForm);

  const introBullets = useMemo(
    () => [
      "معلومات الموقع والدوام والاتصال في مكان واحد.",
      "نموذج جاهز يرسل تفاصيلك دفعة واحدة.",
      "أسئلة شائعة تساعدك قبل الزيارة أو التسجيل.",
    ],
    []
  );

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    window.open(buildWhatsappUrl(form), "_blank", "noopener,noreferrer");
  };

  return (
    <main className="min-h-screen bg-[linear-gradient(180deg,#f3f7e8_0%,#fffaf0_34%,#eef5df_100%)] text-gray-900">
      <header className="border-b border-[#d9e5c7] bg-[#f8fbf2]/95 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 md:px-8">
          <Link href="/ar" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-[linear-gradient(135deg,#2d5016,#5aa01e)] text-white shadow-sm">
              <span className="text-lg font-black">ك</span>
            </div>
            <div className="leading-tight">
              <div className="font-bold text-[#184e3e]">روضة كوكب الطفل الحر</div>
              <div className="text-xs text-[#6a7d5a]">صفحة التواصل الرسمية</div>
            </div>
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/ar#contact"
              className="hidden rounded-full border border-[#cfd9b7] bg-white/80 px-4 py-2 text-sm font-semibold text-[#184e3e] transition-all hover:border-[#a8c27d] hover:bg-[#f2f8e6] md:inline-flex"
            >
              تواصل الموقع
            </Link>
            <Link
              href="/blog/"
              className="rounded-full bg-[#2d5016] px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all hover:-translate-y-0.5 hover:bg-[#214011]"
            >
              المدوّنة
            </Link>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-10 md:px-8 md:py-14">
        <div className="grid gap-6 lg:grid-cols-[1.2fr_.8fr]">
          <article className="rounded-3xl border border-[#dfe8c8] bg-white/95 p-6 shadow-[0_20px_60px_rgba(45,80,22,.08)] md:p-8">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d7e4bb] bg-[#f0f7e6] px-4 py-2 text-sm font-semibold text-[#2d5016]">
              <Sparkles size={16} />
              صفحة تواصل حقيقية
            </div>
            <h1 className="text-3xl font-black leading-tight text-[#184e3e] md:text-5xl">
              تواصلي معنا في جدة بسهولة وبدون تعقيد
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-8 text-[#56614e] md:text-lg">
              هذه الصفحة مخصّصة للأهالي الذين يريدون عنوانًا واضحًا، معلومات سريعة، وطريقة
              سهلة لإرسال سؤال مرتب عن التسجيل أو الزيارة أو الرسوم.
            </p>

            <ul className="mt-6 grid gap-3 text-sm text-gray-700 md:grid-cols-3">
              {introBullets.map((item) => (
                <li
                  key={item}
                  className="rounded-2xl border border-[#dfe7c7] bg-[linear-gradient(180deg,#fbfdf5_0%,#f0f7e6_100%)] px-4 py-4 leading-7 shadow-sm"
                >
                  {item}
                </li>
              ))}
            </ul>

            <div className="mt-6 flex flex-wrap gap-3">
              <a
                href="https://wa.me/966541558173"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-11 items-center gap-2 rounded-full bg-[#25D366] px-5 py-3 text-sm font-bold text-white shadow-[0_12px_30px_rgba(37,211,102,.28)] transition-transform hover:scale-[1.01]"
              >
                <MessageCircle size={18} />
                افتحي واتساب الآن
              </a>
              <a
                href="mailto:info@montessori-ksa.com"
                className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[#ccd7b4] bg-white px-5 py-3 text-sm font-bold text-[#184e3e] transition-all hover:-translate-y-0.5 hover:bg-[#f8fbf1]"
              >
                <Mail size={18} />
                أرسلي بريدًا
              </a>
              <a
                href="https://www.google.com/maps/place/%D8%B1%D9%88%D8%B6%D8%A9+%D9%83%D9%88%D9%83%D8%A8+%D8%A7%D9%84%D8%B7%D9%81%D9%84+%D8%A7%D9%84%D8%AD%D8%B1%E2%80%AD/@21.5795281,39.194829,673m/data=!3m2!1e3!4b1!4m6!3m5!1s0x15c3d18ac84c1d4d:0xaee1671b468377fb!8m2!3d21.5795281!4d39.194829!16s%2Fg%2F11s619kg25"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex min-h-11 items-center gap-2 rounded-full border border-[#ccd7b4] bg-white px-5 py-3 text-sm font-bold text-[#184e3e] transition-all hover:-translate-y-0.5 hover:bg-[#f8fbf1]"
              >
                <MapPin size={18} />
                الموقع على الخريطة
              </a>
            </div>

            <div className="mt-8 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-[#dfe7c7] bg-[linear-gradient(180deg,#fcfbf5_0%,#f2f8e7_100%)] p-5 shadow-sm">
                <h2 className="flex items-center gap-2 text-lg font-bold text-[#184e3e]">
                  <Phone size={18} />
                  بيانات الاتصال
                </h2>
                <ul className="mt-4 space-y-3 text-sm text-gray-700">
                  {infoItems.map((item) => (
                    <li key={item.label} className="flex gap-3">
                      <span className="w-20 shrink-0 font-semibold text-gray-500">
                        {item.label}
                      </span>
                      <span className="leading-7">{item.value}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-2xl border border-[#e7dab8] bg-[linear-gradient(180deg,#fffdf5_0%,#f8efd9_100%)] p-5 shadow-sm">
                <h2 className="flex items-center gap-2 text-lg font-bold text-[#184e3e]">
                  <Clock3 size={18} />
                  ما الذي نسأل عنه عادة؟
                </h2>
                <ul className="mt-4 space-y-2 text-sm text-gray-700">
                  {askPoints.map((item) => (
                    <li key={item} className="flex items-start gap-2 leading-7">
                      <span className="mt-2 h-1.5 w-1.5 rounded-full bg-[#2d5016]" />
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </article>

          <aside className="rounded-3xl border border-[#dfe8c8] bg-[linear-gradient(180deg,#fffdf7_0%,#f7fbe9_100%)] p-6 shadow-[0_20px_60px_rgba(45,80,22,.08)] md:p-8">
            <h2 className="text-2xl font-black text-[#184e3e]">أرسلي رسالتك مرة واحدة</h2>
            <p className="mt-3 text-sm leading-7 text-[#56614e]">
              املئي النموذج، وسنجهّز لكِ رسالة واتساب واضحة فيها الاسم والعمر والبرنامج
              المطلوب، حتى يكون الرد أسرع وأدق.
            </p>

            <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-gray-700">الاسم الكامل</span>
                <input
                  value={form.name}
                  onChange={(e) => setForm((prev) => ({ ...prev, name: e.target.value }))}
                  className="w-full rounded-2xl border border-[#d6dfb9] bg-white px-4 py-3 text-sm outline-none transition focus:border-[#9ebf92] focus:ring-4 focus:ring-[#2d5016]/10"
                  placeholder="اكتبي اسمك"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-gray-700">رقم الجوال</span>
                <input
                  value={form.phone}
                  onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))}
                  className="w-full rounded-2xl border border-[#d6dfb9] bg-white px-4 py-3 text-sm outline-none transition focus:border-[#9ebf92] focus:ring-4 focus:ring-[#2d5016]/10"
                  placeholder="05xxxxxxxx"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-gray-700">عمر الطفل</span>
                <input
                  value={form.childAge}
                  onChange={(e) => setForm((prev) => ({ ...prev, childAge: e.target.value }))}
                  className="w-full rounded-2xl border border-[#d6dfb9] bg-white px-4 py-3 text-sm outline-none transition focus:border-[#9ebf92] focus:ring-4 focus:ring-[#2d5016]/10"
                  placeholder="مثال: سنتان ونصف"
                />
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-gray-700">البرنامج المناسب</span>
                <select
                  value={form.program}
                  onChange={(e) => setForm((prev) => ({ ...prev, program: e.target.value }))}
                  className="w-full rounded-2xl border border-[#d6dfb9] bg-white px-4 py-3 text-sm outline-none transition focus:border-[#9ebf92] focus:ring-4 focus:ring-[#2d5016]/10"
                >
                  <option value="">اختاري البرنامج</option>
                  <option value="الحضانة / Nido">الحضانة / Nido</option>
                  <option value="الأطفال الصغار">الأطفال الصغار</option>
                  <option value="الروضة">الروضة</option>
                  <option value="التهيئة المدرسية">التهيئة المدرسية</option>
                </select>
              </label>

              <label className="block">
                <span className="mb-2 block text-sm font-semibold text-gray-700">رسالتك</span>
                <textarea
                  value={form.message}
                  onChange={(e) => setForm((prev) => ({ ...prev, message: e.target.value }))}
                  className="min-h-36 w-full rounded-2xl border border-[#d6dfb9] bg-white px-4 py-3 text-sm outline-none transition focus:border-[#9ebf92] focus:ring-4 focus:ring-[#2d5016]/10"
                  placeholder="أخبرينا عن سؤالك: الرسوم، الزيارة، التوفر، أو أي تفاصيل أخرى"
                />
              </label>

              <button
                type="submit"
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl bg-[linear-gradient(135deg,#184e3e,#2d5016)] px-5 py-4 text-sm font-bold text-white shadow-[0_14px_30px_rgba(24,78,62,.24)] transition hover:brightness-105"
              >
                <Send size={18} />
                إرسال عبر واتساب
              </button>
            </form>

            <div className="mt-6 rounded-2xl border border-[#dfe7c7] bg-[linear-gradient(180deg,#fcfbf6_0%,#f0f7e6_100%)] p-5">
              <p className="text-sm font-semibold text-[#184e3e]">معلومة سريعة</p>
              <p className="mt-2 text-sm leading-7 text-[#56614e]">
                عندما ترسلين الاسم والعمر والبرنامج، نقدر نرد عليكِ بتفاصيل أدق وأسرع.
              </p>
            </div>
          </aside>
        </div>

        <section className="mt-6 rounded-3xl border border-[#dfe8c8] bg-[linear-gradient(180deg,#fffdf9_0%,#f7fbe9_100%)] p-6 shadow-[0_20px_50px_rgba(45,80,22,.06)] md:p-8">
          <h2 className="text-2xl font-black text-[#184e3e]">أسئلة شائعة</h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {faqItems.map((item) => (
              <details
                key={item.q}
                className="rounded-2xl border border-[#dbe6c1] bg-white/90 p-5 shadow-sm"
              >
                <summary className="cursor-pointer list-none text-base font-bold text-[#184e3e]">
                  {item.q}
                </summary>
                <p className="mt-3 text-sm leading-7 text-[#56614e]">{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="mt-6 rounded-3xl border border-[#dfe7c7] bg-[linear-gradient(135deg,#ffffff_0%,#f6faea_100%)] p-6 shadow-[0_16px_40px_rgba(45,80,22,.06)] md:p-8">
          <h2 className="text-2xl font-black text-[#184e3e]">متى أستخدم هذه الصفحة؟</h2>
          <p className="mt-3 max-w-4xl text-base leading-8 text-[#56614e]">
            استخدميها عندما تريدين إجابة منظّمة بدل رسالة عشوائية. الصفحة مفيدة لو كنتِ
            تقارنين بين البرامج، أو تريدين التأكد من العنوان والدوام، أو ترغبين في إرسال
            سؤالك مع عمر الطفل والبرنامج المناسب من أول مرة.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/ar"
              className="inline-flex items-center gap-2 rounded-full bg-[#2d5016] px-5 py-3 text-sm font-bold text-white shadow-sm transition hover:-translate-y-0.5"
            >
              العودة للرئيسية
              <ArrowUpRight size={16} />
            </Link>
            <Link
              href="/blog/"
              className="inline-flex items-center gap-2 rounded-full border border-[#d2ddb8] bg-white px-5 py-3 text-sm font-bold text-[#184e3e] transition hover:-translate-y-0.5 hover:bg-[#f8fbf1]"
            >
              تصفح المدونة
            </Link>
            <a
              href="https://wa.me/966541558173"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-full border border-[#25D366]/30 bg-[#eafaf0] px-5 py-3 text-sm font-bold text-[#185f36] transition hover:-translate-y-0.5"
            >
              افتحي محادثة واتساب
            </a>
          </div>
        </section>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@graph": [
              {
                "@type": "LocalBusiness",
                name: "روضة كوكب الطفل الحر",
                url: "https://montessori-ksa.com/wa/",
                telephone: "+966541558173",
                email: "info@montessori-ksa.com",
                address: {
                  "@type": "PostalAddress",
                  streetAddress: "حي الفيصلية",
                  addressLocality: "جدة",
                  addressCountry: "SA",
                },
                openingHours: ["Su-Th 07:30-15:00"],
              },
              {
                "@type": "FAQPage",
                mainEntity: faqItems.map((item) => ({
                  "@type": "Question",
                  name: item.q,
                  acceptedAnswer: {
                    "@type": "Answer",
                    text: item.a,
                  },
                })),
              },
            ],
          }),
        }}
      />
    </main>
  );
}
