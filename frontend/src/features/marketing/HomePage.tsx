import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ProblemSection from './components/ProblemSection';
import LeadCaptureVisual from './components/LeadCaptureVisual';
import HowItWorks from './components/HowItWorks';
import ProductPreview from './components/ProductPreview';
import FeatureSection from './components/FeatureSection';
import BeforeAfter from './components/BeforeAfter';
import AudienceSection from './components/AudienceSection';
import LeadJourney from './components/LeadJourney';
import AnalyticsPreview from './components/AnalyticsPreview';
import TrustSection from './components/TrustSection';
import PricingSection from './components/PricingSection';
import FAQSection from './components/FAQSection';
import FinalCTA from './components/FinalCTA';
import Footer from './components/Footer';

/**
 * Nextora Lead Capture Machine — Public Homepage
 *
 * Design system: Geist font, primary #b80035 red, secondary #f9bd22 yellow,
 * warm neutral surface-tint-yellow backgrounds, per DESIGN.md + code.html reference.
 */
export default function HomePage() {
  return (
    <div className="min-h-screen bg-background font-sans text-on-background overflow-x-hidden scroll-smooth selection:bg-primary-fixed selection:text-primary">
      <Navbar />
      <main>
        {/* 1. Hero — yellow bg, dot pattern, product mockup */}
        <Hero />

        {/* 2. Problem — why channels fail separately */}
        <ProblemSection />

        {/* 3. One Machine Visual — funnel flow */}
        <LeadCaptureVisual />

        {/* 4. How It Works — 4 numbered steps */}
        <HowItWorks />

        {/* 5. Product Preview — realistic dashboard mockup */}
        <ProductPreview />

        {/* 6. Features — asymmetric grid */}
        <FeatureSection />

        {/* 7. Before vs After */}
        <BeforeAfter />

        {/* 8. Who Is It For */}
        <AudienceSection />

        {/* 9. Lead Journey */}
        <LeadJourney />

        {/* 10. Analytics Preview */}
        <AnalyticsPreview />

        {/* 11. Trust */}
        <TrustSection />

        {/* 12. Pricing */}
        <PricingSection />

        {/* 13. FAQ */}
        <FAQSection />

        {/* 14. Final CTA */}
        <FinalCTA />
      </main>
      <Footer />
    </div>
  );
}
