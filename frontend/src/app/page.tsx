"use client";

import Navbar from "@/components/Navbar";
import HeroSection from "@/components/HeroSection";
import FeaturesSection from "@/components/FeaturesSection";
import ImpactSection from "@/components/ImpactSection";
import HowItWorksSection from "@/components/HowItWorksSection";
import FooterCTA from "@/components/FooterCTA";

export default function Home() {
  return (
    <main>
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <ImpactSection />
      <HowItWorksSection />
      <FooterCTA />
    </main>
  );
}
