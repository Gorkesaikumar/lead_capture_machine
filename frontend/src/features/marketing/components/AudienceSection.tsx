export default function AudienceSection() {
  const personas = [
    {
      emoji: '📸',
      title: 'Creators',
      body: 'Turn Instagram DMs and inquiries into organized leads — not endless scroll.',
    },
    {
      emoji: '🏢',
      title: 'Agencies',
      body: 'Manage inbound client leads across channels and assign them to your team seamlessly.',
    },
    {
      emoji: '🎓',
      title: 'Coaches & Consultants',
      body: 'Capture high-value prospects from social media and your website in one place.',
    },
    {
      emoji: '🏪',
      title: 'Local Businesses',
      body: 'Centralize WhatsApp messages, website forms, and Instagram DMs into one inbox.',
    },
    {
      emoji: '⚙️',
      title: 'Service Businesses',
      body: 'Stop losing potential customers in messy chat histories. Organize every opportunity.',
    },
  ];

  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary tracking-tight">
            Built for businesses that live on conversations.
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {personas.map((p) => (
            <div
              key={p.title}
              className="bg-white border border-outline-variant rounded-xl p-8 shadow-sm hover:border-primary/30 hover:shadow-md transition-all group"
            >
              <div className="text-3xl mb-4">{p.emoji}</div>
              <h3 className="text-body-md font-bold text-on-surface mb-2">{p.title}</h3>
              <p className="text-body-sm text-on-surface-variant leading-relaxed">{p.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
