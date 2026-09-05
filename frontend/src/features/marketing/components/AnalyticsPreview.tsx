export default function AnalyticsPreview() {
  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">Understand your pipeline.</h2>
          <p className="text-body-lg text-on-surface-variant">Explore your workspace's saved leads and bookings over the period you choose.</p>
        </div>
        <dl className="grid gap-8 sm:grid-cols-2">
          <div><dt className="font-semibold text-headline-sm mb-2">Lead volume</dt><dd>Count recorded inquiries by date and source channel.</dd></div>
          <div><dt className="font-semibold text-headline-sm mb-2">Conversion rate</dt><dd>See the proportion of leads marked as converted in your selected cohort.</dd></div>
          <div><dt className="font-semibold text-headline-sm mb-2">Booking trends</dt><dd>Compare completed and cancelled bookings from your database.</dd></div>
          <div><dt className="font-semibold text-headline-sm mb-2">Channel status</dt><dd>Check your saved connection status and whether website forms are active.</dd></div>
        </dl>
      </div>
    </section>
  );
}
