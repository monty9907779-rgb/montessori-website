import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";

type PageCopy = {
  title: string;
  description: string;
  intro: string;
  sections: { heading: string; body: string }[];
  faq: { question: string; answer: string }[];
  related: { href: string; label: string }[];
};

const pages: Record<string, PageCopy> = {
  "hadana-qariba-minni": {
    title: "حضانة قريبة مني في جدة",
    description: "دليل عملي للعثور على حضانة آمنة وقريبة في جدة، مع معلومات عن البرامج المونتيسورية والتواصل مع حضانة كوكب الطفل الحر.",
    intro: "إذا كنت تبحث عن حضانة قريبة منك في جدة، فالقرب مهم، لكنه ليس المعيار الوحيد. ابدأ بالموقع، ثم تحقق من السلامة، خبرة الفريق، البرنامج اليومي، وطريقة تواصل الحضانة مع الأسرة.",
    sections: [
      { heading: "ماذا تتحقق منه قبل التسجيل؟", body: "اسأل عن الترخيص، نسبة المعلمات إلى الأطفال، إجراءات الاستلام والانصراف، النظافة، المساحات الداخلية والخارجية، وآلية التعامل مع الحالات الصحية والطوارئ." },
      { heading: "حضانة مونتيسوري في جدة", body: "تقدم حضانة كوكب الطفل الحر بيئة تعليمية للأطفال من 3 أشهر إلى 6 سنوات في جدة، مع برامج للرضع، والأطفال الصغار، وبيت الأطفال، والتهيئة المدرسية." },
      { heading: "احجز زيارة", body: "أفضل طريقة للمقارنة هي زيارة المكان في وقت العمل، وملاحظة تفاعل المعلمات مع الأطفال، وطلب شرح واضح للروتين اليومي والرسوم والأماكن المتاحة." },
    ],
    faq: [
      { question: "هل الحضانة القريبة أفضل دائمًا؟", answer: "القرب يسهل الروتين اليومي والطوارئ، لكنه يجب أن يأتي مع بيئة آمنة وفريق مؤهل وبرنامج مناسب لعمر الطفل." },
      { question: "ما الأعمار التي تستقبلها الحضانة؟", answer: "تستقبل البرامج الأطفال من عمر 3 أشهر حتى 6 سنوات، حسب البرنامج والطاقة الاستيعابية المتاحة." },
    ],
    related: [
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
      { href: "/ar/what-is-montessori-method", label: "ما هو منهج مونتيسوري؟" },
    ],
  },
  "daycare-near-me-jeddah": {
    title: "Daycare Near Me in Jeddah",
    description: "A practical guide to finding safe, convenient daycare near you in Jeddah and learning about Montessori childcare programs.",
    intro: "When searching for daycare near you in Jeddah, location is only the first filter. Compare safety routines, staff qualifications, age groups, daily communication, and the learning environment before enrolling.",
    sections: [
      { heading: "What to check before enrollment", body: "Ask about licensing, child-to-educator ratios, arrival and pickup procedures, hygiene, outdoor time, meals, and how the nursery handles illness and emergencies." },
      { heading: "Montessori childcare in Jeddah", body: "Planet of the Free Child Nursery offers programs for children from 3 months to 6 years in Jeddah, including infant care, toddlers, Children's House, and school preparation." },
      { heading: "Book a visit", body: "A visit during operating hours helps you assess the atmosphere, observe educator-child interactions, and receive clear information about schedules, fees, and availability." },
    ],
    faq: [
      { question: "Is the closest daycare always the best choice?", answer: "Proximity makes daily routines easier, but safety, qualified educators, and a suitable program should guide the final decision." },
      { question: "What ages are accepted?", answer: "Programs are available for children from 3 months to 6 years, subject to the selected program and availability." },
    ],
    related: [
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  "preschool-near-me-jeddah": {
    title: "Preschool Near Me in Jeddah",
    description: "Compare preschool options in Jeddah and discover a bilingual Montessori environment for early learning and independence.",
    intro: "A strong preschool gives children time to build language, movement, concentration, independence, and social confidence. In Jeddah, families can compare location and convenience with the quality of the prepared environment.",
    sections: [
      { heading: "What makes a preschool supportive?", body: "Look for calm classrooms, accessible materials, a predictable rhythm, purposeful activities, outdoor movement, and educators who observe each child instead of using one pace for everyone." },
      { heading: "Ages and programs", body: "Planet of the Free Child serves children from 3 months to 6 years with bilingual Arabic-English exposure and Montessori-inspired developmental programs." },
      { heading: "From preschool to school readiness", body: "Children develop practical skills, communication, early literacy, numeracy, and cooperation through hands-on work rather than worksheets alone." },
    ],
    faq: [
      { question: "What age does preschool usually start?", answer: "Preschool commonly begins around age 2 or 3, but the right start depends on the child's readiness and the program offered." },
      { question: "Is Montessori suitable for preschool children?", answer: "Montessori is designed around children's developmental needs and uses hands-on materials, choice within limits, and progressive independence." },
    ],
    related: [
      { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
      { href: "/en/kindergarten-near-me-jeddah", label: "Kindergarten Near Me in Jeddah" },
    ],
  },
  "kindergarten-near-me-jeddah": {
    title: "Kindergarten Near Me in Jeddah",
    description: "Find a kindergarten near you in Jeddah and compare Montessori kindergarten preparation, bilingual learning, and family communication.",
    intro: "Choosing a kindergarten in Jeddah means looking beyond a convenient address. Families should compare the learning approach, classroom environment, school-readiness goals, and how educators share progress.",
    sections: [
      { heading: "A balanced kindergarten environment", body: "Children need a balance of focused work, movement, practical life, language, mathematics, creative expression, and opportunities to cooperate with peers." },
      { heading: "Montessori preparation", body: "A Montessori classroom supports concentration, orderly movement, independence, early literacy, numeracy, and responsibility through carefully sequenced materials." },
      { heading: "Questions for your visit", body: "Ask how the classroom supports different abilities, how progress is documented, what the daily schedule looks like, and how parents can communicate with the team." },
    ],
    faq: [
      { question: "How do I compare kindergartens?", answer: "Visit more than one setting and compare safety, educators, classroom practice, communication, schedule, fees, and the child's response to the environment." },
      { question: "Does Montessori prepare children for primary school?", answer: "A well-run Montessori program builds academic foundations alongside independence, communication, self-regulation, and social readiness." },
    ],
    related: [
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  "what-is-montessori-method": {
    title: "ما هو منهج مونتيسوري؟",
    description: "تعرف على مبادئ منهج مونتيسوري، دور البيئة المعدة، ودور المعلمة في دعم استقلال الطفل والتعلم المبكر.",
    intro: "منهج مونتيسوري هو نهج في التعليم المبكر يضع الطفل في قلب عملية التعلم. يتعلم الطفل من خلال بيئة معدة، ومواد حسية، واختيار منظم، وتدخل هادف من المعلمة في الوقت المناسب.",
    sections: [
      { heading: "المبادئ الأساسية", body: "يركز المنهج على احترام إيقاع الطفل، التعلم العملي، تنمية التركيز، الاستقلالية، الحركة الهادفة، والفصل المختلط الأعمار عندما تسمح البيئة بذلك." },
      { heading: "دور المعلمة", body: "المعلمة تلاحظ الطفل وتقدم عرضًا واضحًا للمادة، ثم تمنحه وقتًا للعمل والتكرار. الهدف ليس ترك الطفل بلا توجيه، بل تقديم التوجيه المناسب دون إلغاء مبادرته." },
      { heading: "كيف يختار الأهل حضانة مونتيسوري؟", body: "اسأل عن تدريب الفريق، طبيعة المواد، حجم الفصل، وقت العمل المستقل، طريقة متابعة التقدم، وكيف تتواصل الحضانة مع الأسرة." },
    ],
    faq: [
      { question: "هل مونتيسوري يعني اللعب طوال اليوم؟", answer: "يتضمن التعلم حركة واستكشافًا، لكنه يعتمد أيضًا على أعمال مقصودة ومواد مرتبة تساعد الطفل على بناء مهارات محددة." },
      { question: "هل يوجد تعليم عربي وإنجليزي؟", answer: "تقدم حضانة كوكب الطفل الحر بيئة ثنائية اللغة العربية والإنجليزية ضمن برامجها التعليمية." },
    ],
    related: [
      { href: "/ar/hadana-qariba-minni", label: "حضانة قريبة مني في جدة" },
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
    ],
  },
};

const englishMontessoriPage: PageCopy = {
  title: "What Is the Montessori Method?",
  description: "Learn the principles of the Montessori method, the prepared environment, and how educators support independence in early childhood.",
  intro: "The Montessori method is an approach to early education that places the child at the center of learning. Children work in a prepared environment with hands-on materials, meaningful choice, and timely guidance from the educator.",
  sections: [
    { heading: "Core principles", body: "The method respects each child's pace and emphasizes hands-on learning, concentration, independence, purposeful movement, and mixed-age communities when the setting supports them." },
    { heading: "The educator's role", body: "The educator observes the child, gives a clear presentation of a material, and then allows time for practice and repetition. The goal is thoughtful guidance without taking away the child's initiative." },
    { heading: "How to choose a Montessori nursery", body: "Ask about staff training, the quality and sequence of materials, class size, uninterrupted work periods, progress tracking, and communication with families." },
  ],
  faq: [
    { question: "Does Montessori mean children play all day?", answer: "Children move and explore, but the environment also includes purposeful work with materials designed to develop specific skills." },
    { question: "Is Arabic and English learning available?", answer: "Planet of the Free Child Nursery offers Arabic-English bilingual exposure within its educational programs." },
  ],
  related: [
    { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
    { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
  ],
};

export function generateStaticParams() {
  return routing.locales.flatMap((locale) =>
    Object.keys(pages).map((slug) => ({ locale, slug }))
  );
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const page = locale === "en" && slug === "what-is-montessori-method"
    ? englishMontessoriPage
    : pages[slug];
  if (!page || !routing.locales.includes(locale as "ar" | "en")) return {};
  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://montessori-ksa.com";
  return {
    title: page.title,
    description: page.description,
    alternates: {
      canonical: `${siteUrl}/${locale}/${slug}`,
    },
    openGraph: { title: page.title, description: page.description, url: `${siteUrl}/${locale}/${slug}`, type: "article" },
  };
}

export default async function SeoPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const page = locale === "en" && slug === "what-is-montessori-method"
    ? englishMontessoriPage
    : pages[slug];
  if (!page || !routing.locales.includes(locale as "ar" | "en")) notFound();
  const isAr = locale === "ar";
  const schema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: page.title,
    description: page.description,
    inLanguage: locale,
    author: { "@type": "Organization", name: "Planet of the Free Child Nursery" },
    publisher: { "@type": "Organization", name: "Planet of the Free Child Nursery" },
    mainEntityOfPage: `https://montessori-ksa.com/${locale}/${slug}`,
    ...(page.faq.length > 0
      ? { mainEntity: { "@type": "FAQPage", mainEntity: page.faq.map((item) => ({ "@type": "Question", name: item.question, acceptedAnswer: { "@type": "Answer", text: item.answer } })) } }
      : {}),
  };

  return (
    <main dir={isAr ? "rtl" : "ltr"} className="pt-28 pb-20">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      <article className="max-w-4xl mx-auto px-4 md:px-8">
        <p className="badge w-fit" style={{ background: "#e9f3dc", color: "#2d5016" }}>
          {isAr ? "دليل مونتيسوري وتعليم مبكر" : "Montessori & Early Education Guide"}
        </p>
        <h1 className="text-4xl md:text-5xl font-black text-gray-900 mt-5 mb-6">{page.title}</h1>
        <p className="text-xl leading-relaxed text-gray-600 mb-12">{page.intro}</p>
        <div className="space-y-10">
          {page.sections.map((section) => (
            <section key={section.heading}>
              <h2 className="text-2xl font-bold text-[#2d5016] mb-3">{section.heading}</h2>
              <p className="text-gray-700 leading-8">{section.body}</p>
            </section>
          ))}
        </div>
        <section className="mt-14 border-t border-gray-200 pt-10">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">{isAr ? "أسئلة شائعة" : "Frequently Asked Questions"}</h2>
          <div className="space-y-6">
            {page.faq.map((item) => (
              <div key={item.question}>
                <h3 className="font-bold text-gray-900 mb-2">{item.question}</h3>
                <p className="text-gray-600 leading-7">{item.answer}</p>
              </div>
            ))}
          </div>
        </section>
        <section className="mt-14 rounded-lg bg-[#f7faf3] p-6">
          <h2 className="text-xl font-bold text-[#2d5016] mb-4">{isAr ? "اقرأ أيضًا" : "Read Next"}</h2>
          <div className="flex flex-wrap gap-3">
            {page.related.map((item) => (
              <Link key={item.href} href={item.href} className="text-[#2d5016] underline underline-offset-4">
                {item.label}
              </Link>
            ))}
            <Link href={`/${locale}#contact`} className="text-[#2d5016] underline underline-offset-4">
              {isAr ? "تواصل مع الحضانة" : "Contact the nursery"}
            </Link>
          </div>
        </section>
      </article>
    </main>
  );
}
