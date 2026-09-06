import type { Metadata } from "next";
import WhatsappContactPage from "@/components/WhatsappContactPage";

export const metadata: Metadata = {
  metadataBase: new URL("https://montessori-ksa.com"),
  title: "تواصل معنا | روضة كوكب الطفل الحر بجدة",
  description:
    "صفحة التواصل الرسمية لروضة كوكب الطفل الحر في جدة: معلومات الموقع والدوام والرسوم، ونموذج يجهز رسالة واتساب جاهزة.",
  alternates: {
    canonical: "https://montessori-ksa.com/wa/",
  },
  openGraph: {
    type: "website",
    url: "https://montessori-ksa.com/wa/",
    title: "تواصل معنا | روضة كوكب الطفل الحر بجدة",
    description:
      "صفحة تواصل رسمية فيها كل وسائل الاتصال ومعلومات الزيارة والرسوم والأسئلة الشائعة.",
    images: [
      {
        url: "https://montessori-ksa.com/logo.png",
        width: 512,
        height: 512,
        alt: "روضة كوكب الطفل الحر",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "تواصل معنا | روضة كوكب الطفل الحر بجدة",
    description:
      "صفحة تواصل رسمية فيها كل وسائل الاتصال ومعلومات الزيارة والرسوم والأسئلة الشائعة.",
    images: ["https://montessori-ksa.com/logo.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
};

export default function WaPage() {
  return <WhatsappContactPage />;
}
