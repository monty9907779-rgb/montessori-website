import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { NextIntlClientProvider } from "next-intl";
import { getMessages, getTranslations } from "next-intl/server";
import { routing } from "@/i18n/routing";
import "@/app/globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { StructuredData } from "@/components/StructuredData";

export async function generateStaticParams() {
  return routing.locales.map((locale) => ({ locale }));
}

// Metadata is now handled by src/lib/metadata.ts
export { generateMetadata } from "@/lib/metadata";

export async function generateViewport(): Promise<{ themeColor: string }> {
  return {
    themeColor: "#2d5016",
  };
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;

  if (!routing.locales.includes(locale as "ar" | "en")) {
    notFound();
  }

  const messages = await getMessages();
  const dir = locale === "ar" ? "rtl" : "ltr";

  return (
    <html lang={locale} dir={dir}>
      <head>
        <link rel="icon" href="/favicon.ico" sizes="32x32" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <link rel="manifest" href="/site.webmanifest" />
        <link
          href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body
        className={`min-h-screen bg-white text-gray-900 ${
          locale === "ar" ? "font-arabic" : "font-sans"
        }`}
        style={{ fontFamily: locale === "ar" ? "'Tajawal', sans-serif" : "'Inter', sans-serif" }}
      >
        <NextIntlClientProvider messages={messages}>
          <StructuredData locale={locale} />
          <Navbar />
          <main>{children}</main>
          <Footer />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
