import { X, CheckCircle2 } from 'lucide-react';

export default function BeforeAfter() {
  const before = [
    'Instagram DMs mixed with personal chats',
    'WhatsApp chats on your personal phone',
    'Website forms stuck in email inboxes',
    'Manual data entry into spreadsheets',
    'Missed follow-ups and forgotten leads',
    'Scattered information across apps',
    'No team visibility or assignment',
  ];

  const after = [
    'One workspace for every lead source',
    'Unified conversations by lead, not channel',
    'Automatic capture — no manual entry',
    'Team members assigned to specific leads',
    'Clear statuses: New → Qualifying → Won',
    'Full source tracking so you know what works',
    'Centralized follow-up that never forgets',
  ];

  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-white">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary tracking-tight">
            Stop managing leads like this.
          </h2>
        </div>

        <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">

          {/* Before */}
          <div className="bg-white border border-outline-variant rounded-xl overflow-hidden shadow-md">
            <div className="h-1.5 bg-red-400" />
            <div className="p-8">
              <h3 className="text-headline-sm font-semibold text-on-surface mb-6">Without Nextora</h3>
              <ul className="space-y-4">
                {before.map((item, i) => (
                  <li key={i} className="flex items-start gap-4 text-on-surface-variant text-body-sm leading-relaxed">
                    <div className="h-5 w-5 rounded-full bg-red-50 border border-red-200 flex items-center justify-center shrink-0 mt-0.5">
                      <X className="h-3 w-3 text-red-500" />
                    </div>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* After */}
          <div className="bg-on-background rounded-xl overflow-hidden shadow-xl relative">
            <div className="h-1.5 bg-secondary-fixed-dim" />
            <div className="p-8 relative z-10">
              <h3 className="text-headline-sm font-semibold text-white mb-6">With Nextora</h3>
              <ul className="space-y-4">
                {after.map((item, i) => (
                  <li key={i} className="flex items-start gap-4 text-white/70 text-body-sm leading-relaxed">
                    <CheckCircle2 className="h-5 w-5 text-secondary-fixed-dim shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
