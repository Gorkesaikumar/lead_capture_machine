import { ShieldCheck, Zap, Users, Globe } from 'lucide-react';

/** Trust section — product-level statements, no fake testimonials */
export default function TrustSection() {
  const statements = [
    { icon: <ShieldCheck className="h-6 w-6" />, label: 'Secure lead management', body: 'Your leads and conversations are stored securely and accessible only by your team.' },
    { icon: <Zap className="h-6 w-6" />, label: 'Reliable lead capture', body: 'Leads are captured automatically the moment a message or form is submitted — nothing slips through.' },
    { icon: <Users className="h-6 w-6" />, label: 'Team collaboration', body: 'Assign leads, add notes, and collaborate so your whole team stays aligned.' },
    { icon: <Globe className="h-6 w-6" />, label: 'Easy setup', body: 'Connect your channels in minutes. No technical skills required.' },
  ];

  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-white">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
            Built to be reliable.
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-xl mx-auto">
            Nextora is designed to be the dependable backbone of your lead capture process.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {statements.map((s) => (
            <div key={s.label} className="text-center p-6 rounded-xl border border-outline-variant bg-white hover:border-primary/30 transition-colors">
              <div className="h-12 w-12 rounded-full bg-surface-tint-red text-primary flex items-center justify-center mx-auto mb-4">
                {s.icon}
              </div>
              <h3 className="font-semibold text-on-surface text-body-md mb-2">{s.label}</h3>
              <p className="text-body-sm text-on-surface-variant leading-relaxed">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
