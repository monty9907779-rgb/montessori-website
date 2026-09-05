import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { routing } from "@/i18n/routing";
import { seoArticles } from "@/lib/seo-page-data";

type Locale = "ar" | "en";

type RelatedLink = {
  href: string;
  label: string;
};

type PageConfig = {
  locale: Locale;
  slug: string;
  articleKey?: keyof typeof seoArticles;
  fallback?: {
    title: string;
    description: string;
    html: string;
    faq: { question: string; answer: string }[];
  };
  related: RelatedLink[];
};

const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://montessori-ksa.com";

const pageConfigs: PageConfig[] = [
  {
    locale: "ar",
    slug: "hadana-qariba-minni",
    articleKey: "hadana-qariba-minni.md",
    related: [
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
      { href: "/ar/what-is-montessori-method", label: "ما هو منهج مونتيسوري؟" },
    ],
  },
  {
    locale: "ar",
    slug: "kayfa-akhtar-hadana",
    articleKey: "kayfa-akhtar-hadana.md",
    related: [
      { href: "/ar/hadana-qariba-minni", label: "حضانة قريبة مني في جدة" },
      { href: "/ar/what-is-montessori-method", label: "ما هو منهج مونتيسوري؟" },
    ],
  },
  {
    locale: "ar",
    slug: "what-is-montessori-method",
    articleKey: "what-is-montessori-method-ar.md",
    related: [
      { href: "/ar/hadana-qariba-minni", label: "حضانة قريبة مني في جدة" },
      { href: "/ar/kayfa-akhtar-hadana", label: "كيف أختار حضانة لطفلي؟" },
    ],
  },
  {
    locale: "en",
    slug: "daycare-near-me-jeddah",
    articleKey: "daycare-near-me-jeddah.md",
    related: [
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/kindergarten-near-me-jeddah", label: "Kindergarten Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  {
    locale: "en",
    slug: "preschool-near-me-jeddah",
    articleKey: "preschool-near-me-jeddah.md",
    related: [
      { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
      { href: "/en/kindergarten-near-me-jeddah", label: "Kindergarten Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  {
    locale: "en",
    slug: "kindergarten-near-me-jeddah",
    articleKey: "kindergarten-near-me-jeddah.md",
    related: [
      { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/what-is-montessori-method", label: "What Is the Montessori Method?" },
    ],
  },
  {
    locale: "en",
    slug: "what-is-montessori-method",
    fallback: {
      title: "What Is the Montessori Method?",
      description:
        "Learn the principles of the Montessori method, the prepared environment, and how educators support independence in early childhood.",
      html: `
        <h2>What is the Montessori method?</h2>
        <p>The Montessori method is an early education approach that places the child at the center of learning. Children work in a prepared environment with hands-on materials, meaningful choice, and timely guidance from the educator.</p>
        <h2>Core principles</h2>
        <ul>
          <li>Respect for each child's pace</li>
          <li>Hands-on learning before abstract instruction</li>
          <li>Independence through practical life skills</li>
          <li>Concentration through uninterrupted work</li>
          <li>A calm, ordered classroom environment</li>
        </ul>
        <h2>The educator's role</h2>
        <p>The educator observes the child, gives a clear presentation of a material, and then allows time for practice and repetition. The goal is thoughtful guidance without taking away the child's initiative.</p>
        <h2>How to choose a Montessori nursery</h2>
        <p>Ask about staff training, the quality and sequence of materials, class size, uninterrupted work periods, progress tracking, and communication with families.</p>
      `,
      faq: [],
    },
    related: [
      { href: "/en/daycare-near-me-jeddah", label: "Daycare Near Me in Jeddah" },
      { href: "/en/preschool-near-me-jeddah", label: "Preschool Near Me in Jeddah" },
      { href: "/en/kindergarten-near-me-jeddah", label: "Kindergarten Near Me in Jeddah" },
    ],
  },
];

function getPageConfig(locale: string, slug: string) {
  return pageConfigs.find((page) => page.locale === locale && page.slug === slug);
}

function getArticle(config: PageConfig) {
  if (config.articleKey) return seoArticles[config.articleKey];
  return config.fallback;
}

export function generateStaticParams() {
  return pageConfigs.map(({ locale, slug }) => ({ locale, slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const config = getPageConfig(locale, slug);
  if (!config || !routing.locales.includes(locale as Locale)) return {};

  const article = getArticle(config);
  if (!article) return {};
  const url = `${siteUrl}/${locale}/${slug}`;

  return {
    title: article.title,
    description: article.description,
    alternates: { canonical: url },
    openGraph: {
      title: article.title,
      description: article.description,
      url,
      type: "article",
      images: [{ url: `${siteUrl}/og-image.png`, width: 1200, height: 630, alt: article.title }],
    },
    twitter: {
      card: "summary_large_image",
      title: article.title,
      description: article.description,
      images: [`${siteUrl}/og-image.png`],
    },
  };
}

export default async function SeoPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  const config = getPageConfig(locale, slug);
  if (!config || !routing.locales.includes(locale as Locale)) notFound();

  const article = getArticle(config);
  if (!article) notFound();
  const isAr = locale === "ar";
  const url = `${siteUrl}/${locale}/${slug}`;
  const schema = buildSchema(article, config, url);

  return (
    <main dir={isAr ? "rtl" : "ltr"} className="pt-28 pb-20">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }} />
      <article className="max-w-4xl mx-auto px-4 md:px-8">
        <p className="badge w-fit" style={{ background: "#e9f3dc", color: "#2d5016" }}>
          {isAr ? "دليل مونتيسوري وتعليم مبكر" : "Montessori & Early Education Guide"}
        </p>
        <h1 className="text-4xl md:text-5xl font-black text-gray-900 mt-5 mb-6 leading-tight">
          {article.title}
        </h1>
        <div
          className="seo-article"
          dangerouslySetInnerHTML={{ __html: article.html }}
        />
        <section className="mt-14 rounded-lg bg-[#f7faf3] p-6">
          <h2 className="text-xl font-bold text-[#2d5016] mb-4">{isAr ? "اقرأ أيضًا" : "Read Next"}</h2>
          <div className="flex flex-wrap gap-3">
            {config.related.map((item) => (
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

function buildSchema(
  article: { title: string; description: string; faq: readonly { question: string; answer: string }[] },
  config: PageConfig,
  url: string
) {
  const graph: Record<string, unknown>[] = [
    {
      "@type": "Article",
      headline: article.title,
      description: article.description,
      inLanguage: config.locale,
      author: { "@type": "Organization", name: "Planet of the Free Child Nursery" },
      publisher: {
        "@type": "Organization",
        name: "Planet of the Free Child Nursery",
        logo: { "@type": "ImageObject", url: `${siteUrl}/og-image.png` },
      },
      mainEntityOfPage: url,
      datePublished: "2026-09-03",
      dateModified: "2026-09-05",
    },
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        { "@type": "ListItem", position: 1, name: config.locale === "ar" ? "الرئيسية" : "Home", item: `${siteUrl}/${config.locale}` },
        { "@type": "ListItem", position: 2, name: article.title, item: url },
      ],
    },
  ];

  if (article.faq.length > 0) {
    graph.push({
      "@type": "FAQPage",
      mainEntity: article.faq.map((item) => ({
        "@type": "Question",
        name: item.question,
        acceptedAnswer: { "@type": "Answer", text: item.answer },
      })),
    });
  }

  return { "@context": "https://schema.org", "@graph": graph };
}
