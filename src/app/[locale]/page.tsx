import dynamic from 'next/dynamic';
import HeroSection from "@/components/sections/HeroSection";
import AboutSection from "@/components/sections/AboutSection";

// Lazy load below-the-fold sections
const ProgramsSection = dynamic(() => import("@/components/sections/ProgramsSection"));
const CurriculumSection = dynamic(() => import("@/components/sections/CurriculumSection"));
const MethodologySection = dynamic(() => import("@/components/sections/MethodologySection"));
const DailyLifeSection = dynamic(() => import("@/components/sections/DailyLifeSection"));
const GallerySection = dynamic(() => import("@/components/sections/GallerySection"));
const RolesSection = dynamic(() => import("@/components/sections/RolesSection"));
const ContactSection = dynamic(() => import("@/components/sections/ContactSection"));
import FollowUsSection from "@/components/sections/FollowUsSection";
import SeoLinksSection from "@/components/SeoLinksSection";

export default function HomePage() {
  return (
    <>
      <HeroSection />
      <AboutSection />
      <ProgramsSection />
      <CurriculumSection />
      <MethodologySection />
      <DailyLifeSection />
      <GallerySection />
      <RolesSection />
      <ContactSection />
      <SeoLinksSection />
      <FollowUsSection />
    </>
  );
}
