import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';

export default function PricingSection() {
  return (
    <section id="pricing" className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30">
      <div className="max-w-8xl mx-auto text-center">
        <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
          Simple plans built to grow with your business.
        </h2>
        <p className="text-body-lg text-on-surface-variant mb-10 max-w-xl mx-auto leading-relaxed">
          Connect all your channels, unify your leads, and start converting from day one.
        </p>
        <Link to="/signup">
          <button className="inline-flex items-center gap-2 bg-primary text-on-primary px-10 py-4 rounded-lg text-body-md font-semibold hover:bg-primary-container transition-colors shadow-md">
            View Pricing
            <ArrowRight className="h-5 w-5" />
          </button>
        </Link>
      </div>
    </section>
  );
}
