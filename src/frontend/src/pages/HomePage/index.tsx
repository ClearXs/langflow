import { Link } from "react-router-dom";
import { CTAHomepage } from "@/components/homepage/cta";
import { FeaturesBentoGrid } from "@/components/homepage/features-bento-grid";
import { FeaturesCards } from "@/components/homepage/features-card";
import { HeroSection } from "@/components/homepage/hero-section";
import ExternalIntegrations from "@/components/homepage/integrations";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 text-gray-900 dark:from-black dark:to-gray-900 dark:text-white">
      <HeroSection />

      {/* Entry to Langflow Workspace */}
      <section className="py-12 px-4">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">Already using Langflow?</h2>
          <Link to="/flows">
            <Button size="lg" className="px-8 py-6 text-lg">
              Go to Langflow Workspace →
            </Button>
          </Link>
        </div>
      </section>

      <FeaturesCards />
      <FeaturesBentoGrid />
      <ExternalIntegrations />
      <CTAHomepage />
    </main>
  );
}
