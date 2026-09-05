import { ArrowDown, UserCheck, MessageSquare, Target } from 'lucide-react';

/** Lead Capture Machine visual — funnel flow showing 3 sources → Nextora → outputs */
export default function LeadCaptureVisual() {
  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
            One machine. Every lead source.
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            Every channel. One workspace. Zero leads slipping through the cracks.
          </p>
        </div>

        <div className="flex flex-col items-center gap-6 max-w-2xl mx-auto">

          {/* Sources row */}
          <div className="flex flex-col sm:flex-row gap-4 w-full">
            <SourceBadge emoji="📸" label="Instagram" sub="New DM" color="bg-white border-outline-variant" />
            <SourceBadge emoji="💬" label="WhatsApp" sub="New conversation" color="bg-white border-outline-variant" />
            <SourceBadge emoji="🌐" label="Website" sub="New lead" color="bg-white border-outline-variant" />
          </div>

          <ArrowDown className="h-6 w-6 text-primary/40" />

          {/* Core hub */}
          <div className="bg-white border-2 border-primary/20 rounded-2xl p-8 text-center shadow-xl w-full max-w-xs relative">
            <div className="absolute -top-4 left-1/2 -translate-x-1/2">
              <span className="bg-secondary-fixed-dim text-on-secondary-container px-4 py-1 rounded-full text-label-md font-bold shadow-sm">
                NEXTORA
              </span>
            </div>
            <div className="flex items-center justify-center mx-auto mt-2 mb-4">
              <img src="/lead.png" alt="Nextora" className="h-16 w-auto object-contain drop-shadow-[0_2px_12px_rgba(123,47,255,0.4)]" />
            </div>
            <h3 className="font-bold text-on-surface text-headline-sm tracking-tight">Lead Capture Machine</h3>
            <p className="text-body-sm text-on-surface-variant mt-2">All channels. One workspace.</p>
          </div>

          <ArrowDown className="h-6 w-6 text-primary/40" />

          {/* Outputs */}
          <div className="flex flex-col sm:flex-row gap-4 w-full">
            <OutputBadge icon={<UserCheck className="h-5 w-5 text-primary" />} label="Lead Created" />
            <OutputBadge icon={<MessageSquare className="h-5 w-5 text-green-600" />} label="Conversation Unified" />
            <OutputBadge
              icon={<Target className="h-5 w-5 text-on-secondary-container" />}
              label="Follow-up & Convert"
              accent
            />
          </div>
        </div>
      </div>
    </section>
  );
}

function SourceBadge({ emoji, label, sub, color }: { emoji: string; label: string; sub: string; color: string }) {
  return (
    <div className={`flex items-center gap-3 ${color} border rounded-xl px-5 py-4 shadow-sm flex-1 hover:-translate-y-0.5 transition-transform`}>
      <span className="text-2xl">{emoji}</span>
      <div>
        <div className="font-semibold text-on-surface text-body-sm">{label}</div>
        <div className="text-label-sm text-on-surface-variant">{sub}</div>
      </div>
    </div>
  );
}

function OutputBadge({ icon, label, accent }: { icon: React.ReactNode; label: string; accent?: boolean }) {
  return (
    <div
      className={`flex items-center justify-center gap-3 rounded-xl px-5 py-4 flex-1 font-semibold text-body-sm shadow-sm ${
        accent
          ? 'bg-secondary-fixed-dim text-on-secondary-container shadow-md'
          : 'bg-white border border-outline-variant text-on-surface'
      }`}
    >
      {icon}
      {label}
    </div>
  );
}
