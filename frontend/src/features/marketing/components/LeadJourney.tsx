export default function LeadJourney() {
  const steps = [
    { label: 'Customer discovers your business', type: 'neutral' },
    { label: 'Sends an Instagram message', type: 'neutral' },
    { label: 'Nextora captures the interaction', type: 'brand' },
    { label: 'Lead created automatically', type: 'neutral' },
    { label: 'Team member assigned', type: 'neutral' },
    { label: 'Conversation replied to in Nextora', type: 'neutral' },
    { label: 'Lead status updated to Qualified', type: 'neutral' },
    { label: 'Customer successfully converted', type: 'highlight' },
  ];

  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-white">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
            See a lead flow in action.
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            From the first message to a closed deal — every step is captured in Nextora.
          </p>
        </div>

        <div className="max-w-2xl mx-auto flex flex-col gap-4">
          {steps.map((step, i) => (
            <div
              key={i}
              className={`flex items-center gap-5 p-5 rounded-xl border transition-all ${
                step.type === 'highlight'
                  ? 'bg-primary border-primary shadow-lg scale-[1.02]'
                  : step.type === 'brand'
                  ? 'bg-surface-tint-red border-outline-variant shadow-sm'
                  : 'bg-white border-outline-variant shadow-sm hover:border-primary/30'
              }`}
            >
              <div
                className={`h-10 w-10 rounded-full shrink-0 flex items-center justify-center font-bold text-body-sm ${
                  step.type === 'highlight'
                    ? 'bg-white text-primary'
                    : step.type === 'brand'
                    ? 'bg-primary text-on-primary'
                    : 'bg-surface-container text-on-surface-variant border border-outline-variant'
                }`}
              >
                {i + 1}
              </div>
              <span
                className={`font-medium text-body-md ${
                  step.type === 'highlight'
                    ? 'text-on-primary font-bold'
                    : 'text-on-surface'
                }`}
              >
                {step.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
