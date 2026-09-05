/** How It Works — matches reference exactly:
 *  - Yellow background (surface-tint-yellow)
 *  - h2 in primary red, centered
 *  - 4 numbered circles connected by a line
 *  - Circle 01 filled red, 02 white/red border, 03 white/yellow, 04 filled yellow
 */
export default function HowItWorks() {
  const steps = [
    {
      num: '01',
      label: 'CONNECT',
      body: 'Link your IG, WhatsApp, and Website in clicks.',
      circleClass: 'bg-primary text-on-primary border-surface-tint-yellow',
    },
    {
      num: '02',
      label: 'CAPTURE',
      body: 'Every message and form fill auto-populates as a lead.',
      circleClass: 'bg-white text-primary border-outline-variant',
    },
    {
      num: '03',
      label: 'ORGANIZE',
      body: 'Assign team members and add context tags.',
      circleClass: 'bg-white text-secondary-fixed-dim border-outline-variant',
    },
    {
      num: '04',
      label: 'CONVERT',
      body: 'Reply instantly from one unified inbox.',
      circleClass: 'bg-secondary-fixed-dim text-on-secondary-container border-surface-tint-yellow',
    },
  ];

  return (
    <section
      id="how-it-works"
      className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30"
    >
      <div className="max-w-8xl mx-auto">
        <div className="text-center mb-[80px]">
          <h2 className="text-headline-md font-semibold text-primary tracking-tight">
            From conversation to customer in four steps.
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-lg relative">
          {/* Connecting line — desktop only */}
          <div className="hidden md:block absolute top-8 left-[10%] right-[10%] h-1 bg-outline-variant/40 z-0 rounded-full" />

          {steps.map((step) => (
            <div key={step.num} className="relative z-10 text-center flex flex-col items-center">
              <div
                className={`w-16 h-16 rounded-full ${step.circleClass} font-bold text-xl flex items-center justify-center mx-auto mb-md shadow-md border-4 shrink-0`}
              >
                {step.num}
              </div>
              <h3 className="text-label-md font-bold text-on-surface mb-sm uppercase tracking-widest">
                {step.label}
              </h3>
              <p className="text-body-sm text-on-surface-variant px-4 leading-relaxed">
                {step.body}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
