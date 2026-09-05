import { ChevronDown } from 'lucide-react';

const FAQS = [
  {
    q: 'What is Nextora Lead Capture Machine?',
    a: 'Nextora is an omnichannel lead-capture workspace that pulls inquiries from Instagram, WhatsApp, and your website into a single organized dashboard — replacing scattered DMs and spreadsheets with one clear pipeline.',
  },
  {
    q: 'Which channels can I connect?',
    a: 'Currently you can connect your Instagram account, WhatsApp Business account, and create embeddable lead-capture forms for your website.',
  },
  {
    q: 'Can I capture leads from my website?',
    a: 'Yes. You can create a lead-capture form directly inside Nextora and embed it on your website. When someone fills it out, they appear instantly as a new lead in your workspace.',
  },
  {
    q: 'Can multiple team members manage leads?',
    a: 'Yes. You can invite team members, assign specific leads to specific people, and track progress across the whole team.',
  },
  {
    q: 'Can I manage conversations in one place?',
    a: 'Yes. Once a channel is connected, all messages route into your Nextora Inbox. You can reply from Nextora and the message is delivered to the customer on their original platform.',
  },
  {
    q: 'Can I track where leads came from?',
    a: 'Yes. Every lead is automatically tagged with its source — Instagram, WhatsApp, or Website — so you can analyze which channels drive the most value.',
  },
  {
    q: 'Is there a free plan?',
    a: 'Yes. You can get started for free to connect your channels and experience the unified inbox before upgrading for higher volume.',
  },
  {
    q: 'How do I get started?',
    a: 'Click "Get Started Free", create your account, and follow the 2-minute onboarding to connect your first channel.',
  },
];

export default function FAQSection() {
  return (
    <section id="faq" className="py-[100px] px-margin-mobile md:px-margin-desktop bg-white">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary tracking-tight">
            Frequently Asked Questions
          </h2>
        </div>

        <div className="max-w-3xl mx-auto space-y-4">
          {FAQS.map((faq, i) => (
            <details
              key={i}
              className="group bg-white border border-outline-variant rounded-xl shadow-sm [&_summary::-webkit-details-marker]:hidden overflow-hidden"
            >
              <summary className="flex items-center justify-between gap-4 cursor-pointer p-6 font-semibold text-on-surface text-body-md hover:bg-surface-container-low transition-colors">
                {faq.q}
                <ChevronDown className="h-5 w-5 text-on-surface-variant shrink-0 transition-transform duration-200 group-open:rotate-180" />
              </summary>
              <div className="px-6 pb-6 text-body-sm text-on-surface-variant leading-relaxed border-t border-outline-variant/30 pt-4">
                {faq.a}
              </div>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
