import { Link } from 'react-router-dom';
import { ArrowRight, CheckCircle2, Play } from 'lucide-react';

/** Hero section — matches reference image exactly:
 *  - Warm yellow-tinted background (surface-tint-yellow)
 *  - Radial dot pattern overlay
 *  - Centered text: eyebrow chip → h1 in primary red → body → CTAs → trust line
 *  - Below: glass-panel product mockup (sources → arrows → unified inbox)
 */
export default function Hero() {
  return (
    <section className="relative bg-surface-tint-yellow pt-[140px] pb-[100px] px-margin-mobile md:px-margin-desktop overflow-hidden border-b border-outline-variant/20">
      {/* Dot pattern background */}
      <div className="absolute inset-0 hero-pattern opacity-40 z-0 pointer-events-none" />

      {/* ── Centered hero copy ────────────────────────────────── */}
      <div className="relative z-10 text-center max-w-4xl mx-auto space-y-6">

        {/* Eyebrow */}
        <span className="inline-block px-4 py-1.5 bg-primary-fixed text-on-primary-fixed-variant rounded-full text-label-md font-semibold tracking-wider shadow-sm">
          THE LEAD CAPTURE MACHINE
        </span>

        {/* Headline */}
        <h1 className="text-display-lg-mobile md:text-display-lg font-bold text-primary leading-[1.1] tracking-tight">
          Your leads are everywhere. <br />
          <span className="text-gradient">Bring them into one machine.</span>
        </h1>

        {/* Supporting copy */}
        <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto leading-relaxed">
          Connect Instagram, WhatsApp, and websites into one workspace to capture, organize, respond to, and track leads effortlessly.
        </p>

        {/* CTAs */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-md pt-2">
          <Link to="/signup" className="w-full sm:w-auto">
            <button className="w-full sm:w-auto flex items-center justify-center gap-2 bg-primary text-on-primary px-8 py-4 rounded-lg text-body-md font-semibold hover:bg-primary-container transition-colors shadow-md">
              Get Started Free
              <ArrowRight className="h-5 w-5" />
            </button>
          </Link>
          <a href="#how-it-works" className="w-full sm:w-auto">
            <button className="w-full sm:w-auto flex items-center justify-center gap-2 bg-white border border-outline-variant text-on-surface px-8 py-4 rounded-lg text-body-md font-semibold hover:bg-surface-container-low transition-colors shadow-sm">
              <Play className="h-5 w-5 text-secondary-fixed-dim fill-secondary-fixed-dim" />
              See How It Works
            </button>
          </a>
        </div>

        {/* Trust line */}
        <div className="flex flex-wrap items-center justify-center gap-x-lg gap-y-2 text-body-sm text-on-surface-variant pt-2">
          <span className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-secondary-fixed-dim" />
            No credit card required
          </span>
          <span className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-secondary-fixed-dim" />
            Setup in minutes
          </span>
          <span className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-secondary-fixed-dim" />
            Free plan available
          </span>
        </div>
      </div>

      {/* ── Product Mockup Visualization ──────────────────────── */}
      <div className="relative z-10 mt-[80px] max-w-5xl mx-auto glass-panel rounded-xl p-4 sm:p-6 lg:p-8 shadow-2xl">
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_2.5rem_minmax(0,2fr)] gap-6 items-stretch">

          {/* Left: Source Cards */}
          <div className="grid min-w-0 grid-cols-1 sm:grid-cols-3 lg:grid-cols-1 gap-3 sm:gap-4">
            <SourceCard
              icon={<InstagramIcon />}
              label="Instagram"
              sub="3 New DMs"
            />
            <SourceCard
              icon={<WhatsAppIcon />}
              label="WhatsApp"
              sub="5 New Msgs"
            />
            <SourceCard
              icon={<WebIcon />}
              label="Website"
              sub="2 Form Fills"
            />
          </div>

          {/* Center: Arrows */}
          <div className="hidden lg:flex flex-col gap-[60px] items-center justify-center text-primary/40">
            <ArrowIcon />
            <ArrowIcon />
            <ArrowIcon />
          </div>

          {/* Right: Unified Inbox */}
          <div className="min-w-0 bg-surface-container rounded-xl border border-outline-variant overflow-hidden shadow-md">
            {/* Header */}
            <div className="bg-white border-b border-outline-variant p-4 sm:p-6 flex flex-wrap gap-3 items-center justify-between">
              <div className="flex items-center gap-2 font-semibold text-primary text-lg sm:text-headline-sm">
                <InboxIcon />
                Unified Inbox
              </div>
              <span className="bg-secondary-fixed-dim text-on-secondary-container px-3 py-1 rounded-md text-label-md whitespace-nowrap shadow-sm">
                10 New Leads
              </span>
            </div>
            {/* Leads */}
            <div className="p-3 sm:p-6 flex flex-col gap-sm bg-surface-container-low">
              <InboxRow name="Sarah Jenkins" preview='"Interested in pricing..."' channel="IG" />
              <InboxRow name="Mike Torres"   preview='"Do you offer services in..."' channel="WA" />
              <InboxRow name="Emma Collins"  preview="Form Submitted" channel="Web" muted />
            </div>
          </div>

        </div>
      </div>
    </section>
  );
}

/* ── Sub-components ──────────────────────────────────────────────── */

function SourceCard({ icon, label, sub }: { icon: React.ReactNode; label: string; sub: string }) {
  return (
    <div className="bg-surface p-4 rounded-lg border border-outline-variant flex sm:flex-col lg:flex-row items-center sm:items-start lg:items-center gap-3 shadow-sm w-full min-w-0 hover:-translate-y-0.5 transition-transform duration-200">
      <div className="shrink-0">{icon}</div>
      <div className="min-w-0 break-words">
        <div className="font-semibold text-on-surface text-body-md">{label}</div>
        <div className="text-body-sm text-on-surface-variant">{sub}</div>
      </div>
    </div>
  );
}

function InboxRow({ name, preview, channel, muted }: { name: string; preview: string; channel: string; muted?: boolean }) {
  return (
    <div className={`bg-white p-3 sm:p-6 rounded-lg border border-outline-variant flex gap-2 justify-between items-center hover:shadow-md cursor-pointer transition-all ${muted ? 'opacity-60' : ''}`}>
      <div className="flex min-w-0 flex-1 items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-primary-fixed flex items-center justify-center shrink-0">
          <span className="text-primary font-bold text-body-sm">{name.split(' ').map(n => n[0]).join('')}</span>
        </div>
        <div className="min-w-0 break-words">
          <div className="font-semibold text-on-surface text-body-md">{name}</div>
          <div className="text-body-sm text-on-surface-variant">{preview}</div>
        </div>
      </div>
      <span className="text-label-sm text-outline px-2 py-1 bg-surface-container rounded-md font-bold shrink-0">
        {channel}
      </span>
    </div>
  );
}

function ArrowIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-10 w-10 text-primary/40">
      <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function InboxIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6">
      <polyline points="22 12 16 12 14 15 10 15 8 12 2 12" />
      <path d="M5.45 5.11L2 12v6a2 2 0 002 2h16a2 2 0 002-2v-6l-3.45-6.89A2 2 0 0016.76 4H7.24a2 2 0 00-1.79 1.11z" />
    </svg>
  );
}

function InstagramIcon() {
  return (
    <div className="w-12 h-12 rounded-full bg-gradient-to-tr from-secondary-fixed-dim via-primary to-purple-500 flex items-center justify-center text-white shrink-0">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6">
        <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
        <circle cx="12" cy="12" r="4" />
        <circle cx="17.5" cy="6.5" r="1.5" fill="currentColor" stroke="none" />
      </svg>
    </div>
  );
}

function WhatsAppIcon() {
  return (
    <div className="w-12 h-12 rounded-full bg-green-500 flex items-center justify-center text-white shrink-0">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6">
        <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
      </svg>
    </div>
  );
}

function WebIcon() {
  return (
    <div className="w-12 h-12 rounded-full bg-blue-500 flex items-center justify-center text-white shrink-0">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-6 w-6">
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
      </svg>
    </div>
  );
}
