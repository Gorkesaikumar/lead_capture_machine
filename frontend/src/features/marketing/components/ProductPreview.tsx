import { Link } from 'react-router-dom';

export default function ProductPreview() {
  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-white">
      <div className="max-w-5xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">One workspace. Every lead.</h2>
          <p className="text-body-lg text-on-surface-variant">Your private workspace brings conversations, leads, and follow-ups together.</p>
        </div>
        <div className="grid gap-8 md:grid-cols-3 border-y border-outline-variant py-10">
          <div><h3 className="text-headline-sm font-semibold mb-3">Unified inbox</h3><p className="text-on-surface-variant">Receive customer messages from your connected Instagram and WhatsApp accounts.</p></div>
          <div><h3 className="text-headline-sm font-semibold mb-3">Lead pipeline</h3><p className="text-on-surface-variant">Review each inquiry, assign a team member, and track its status.</p></div>
          <div><h3 className="text-headline-sm font-semibold mb-3">Recorded activity</h3><p className="text-on-surface-variant">Follow saved lead events and open the related customer record.</p></div>
        </div>
        <p className="text-center mt-8 text-on-surface-variant">Customer records are private. <Link to="/login" className="font-semibold text-primary underline">Sign in to view your workspace.</Link></p>
      </div>
    </section>
  );
}
