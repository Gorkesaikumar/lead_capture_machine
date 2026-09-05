import { Link } from 'react-router-dom';
import { ArrowRight, Play } from 'lucide-react';

export default function FinalCTA() {
  return (
    <section className="py-[120px] px-margin-mobile md:px-margin-desktop bg-primary text-on-primary relative overflow-hidden">
      {/* Background dot pattern */}
      <div className="absolute inset-0 hero-pattern opacity-10 pointer-events-none" />

      <div className="relative z-10 text-center max-w-4xl mx-auto">
        <h2 className="text-display-lg-mobile md:text-display-lg font-bold tracking-tight mb-6 leading-[1.1]">
          Stop chasing leads across different platforms.
        </h2>
        <p className="text-body-lg text-on-primary/80 mb-10 max-w-2xl mx-auto leading-relaxed">
          Bring your Instagram, WhatsApp, and website leads into one place with Nextora.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-md">
          <Link to="/signup" className="w-full sm:w-auto">
            <button className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white text-primary px-10 py-4 rounded-lg font-bold text-body-md hover:bg-primary-fixed transition-colors shadow-xl">
              Start Capturing Leads
              <ArrowRight className="h-5 w-5" />
            </button>
          </Link>
          <a href="#how-it-works" className="w-full sm:w-auto">
            <button className="w-full sm:w-auto flex items-center justify-center gap-2 bg-transparent border-2 border-on-primary/30 text-on-primary px-10 py-4 rounded-lg font-semibold text-body-md hover:bg-on-primary/10 transition-colors">
              <Play className="h-5 w-5 fill-secondary-fixed-dim text-secondary-fixed-dim" />
              See How It Works
            </button>
          </a>
        </div>
      </div>
    </section>
  );
}
