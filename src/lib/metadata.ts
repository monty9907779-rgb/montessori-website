import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

type Props = {
  params: Promise<{ locale: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });

  const siteUrl = process.env.NEXT_PUBLIC_SITE_URL || "https://montessori-ksa.com";
  const title = t("title");
  const description = t("description");

  return {
    metadataBase: new URL(siteUrl),
    title: {
      default: title,
      template: `%s | ${title}`,
    },
    description,
    keywords: [
      "Montessori",
      "حضانة",
      "مونتيسوري",
      "تعليم الأطفال",
      "السعودية",
      "KSA",
      "early childhood education",
      "منهج مونتيسوري",
      "حضانة كوكب الطفل الحر",
      "Planet of the Free Child",
      "رياض أطفال",
      "kindergarten",
      "preschool Saudi Arabia",
    ],
    authors: [{ name: "Planet of the Free Child Nursery" }],
    creator: "Planet of the Free Child Nursery",
    publisher: "Planet of the Free Child Nursery",
    formatDetection: {
      email: false,
      address: false,
      telephone: false,
    },
    openGraph: {
      type: "website",
      locale: locale === "ar" ? "ar_SA" : "en_US",
      alternateLocale: locale === "ar" ? "en_US" : "ar_SA",
      url: siteUrl,
      title,
      description,
      siteName: title,
      images: [
        {
          url: `${siteUrl}/og-image.png`,
          width: 1200,
          height: 630,
          alt: title,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: [`${siteUrl}/og-image.png`],
    },
    robots: {
      index: true,
      follow: true,
      googleBot: {
        index: true,
        follow: true,
        "max-video-preview": -1,
        "max-image-preview": "large",
        "max-snippet": -1,
      },
    },
    verification: {
      google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION,
    },
    alternates: {
      canonical: siteUrl,
      languages: {
        "ar-SA": `${siteUrl}/ar`,
        "en-US": `${siteUrl}/en`,
      },
    },
  };
}
