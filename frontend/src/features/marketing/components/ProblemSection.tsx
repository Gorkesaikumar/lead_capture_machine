/** Problem Section — matches reference:
 *  - White background
 *  - h2 in primary red, centered
 *  - 3 white bordered cards with icon + headline + body
 */
export default function ProblemSection() {
  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop max-w-8xl mx-auto">

      <div className="text-center mb-[60px]">
        <h2 className="text-headline-md font-semibold text-primary max-w-3xl mx-auto leading-[1.2] tracking-tight">
          Your customers don't care which channel they came from. Why should you?
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-lg">
        <ProblemCard
          icon={<InstagramIcon />}
          iconBg="bg-surface-tint-red"
          title="Instagram"
          body="DMs buried in primary/general folders. Missed opportunities that cost you customers."
        />
        <ProblemCard
          icon={<WhatsAppIcon />}
          iconBg="bg-surface-tint-yellow"
          iconColor="text-secondary-fixed-dim"
          title="WhatsApp"
          body="Hard to track business versus personal. No team visibility, no shared context."
        />
        <ProblemCard
          icon={<WebIcon />}
          iconBg="bg-surface-tint-red"
          title="Website"
          body="Leads isolated in forms or spreadsheets. Slow follow-ups that lose warm prospects."
        />
      </div>
    </section>
  );
}

function ProblemCard({
  icon, iconBg, iconColor = "text-primary", title, body
}: {
  icon: React.ReactNode;
  iconBg: string;
  iconColor?: string;
  title: string;
  body: string;
}) {
  return (
    <div className="bg-white border border-outline-variant p-[40px] rounded-xl shadow-md text-center hover:border-primary/30 transition-colors group">
      <div className={`w-16 h-16 rounded-full ${iconBg} mx-auto mb-md flex items-center justify-center ${iconColor}`}>
        {icon}
      </div>
      <h3 className="text-headline-sm font-semibold text-on-surface mb-sm">{title}</h3>
      <p className="text-body-sm text-on-surface-variant leading-relaxed">{body}</p>
    </div>
  );
}

function InstagramIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-8 w-8">
      <rect x="2" y="2" width="20" height="20" rx="5" ry="5" />
      <circle cx="12" cy="12" r="4" />
      <circle cx="17.5" cy="6.5" r="1.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function WhatsAppIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-8 w-8">
      <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z" />
    </svg>
  );
}

function WebIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="h-8 w-8">
      <circle cx="12" cy="12" r="10" />
      <line x1="2" y1="12" x2="22" y2="12" />
      <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
    </svg>
  );
}
