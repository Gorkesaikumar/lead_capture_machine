import { Inbox, Users, Zap, UserCheck, MessageSquare, Globe, Filter, BarChart3 } from 'lucide-react';

/** Features section — asymmetric grid */
export default function FeatureSection() {
  return (
    <section id="features" className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30">
      <div className="max-w-8xl mx-auto">

        <div className="mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
            Everything you need to stop losing leads.
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-xl">
            Nextora brings your channels, team, and conversations into one organized workspace.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

          {/* Priority card — spans 2 cols */}
          <div className="bg-white p-8 rounded-xl border border-outline-variant shadow-md md:col-span-2">
            <div className="h-12 w-12 rounded-xl bg-surface-tint-red text-primary flex items-center justify-center mb-6">
              <Inbox className="h-6 w-6" />
            </div>
            <h3 className="text-headline-sm font-semibold text-on-surface mb-3">Unified Inbox</h3>
            <p className="text-body-md text-on-surface-variant leading-relaxed max-w-lg">
              Stop switching between Instagram DMs, WhatsApp messages, and email for website leads. See every conversation from all channels in one clean interface — organized by lead, not by platform.
            </p>
          </div>

          <div className="bg-white p-8 rounded-xl border border-outline-variant shadow-md">
            <div className="h-12 w-12 rounded-xl bg-surface-tint-yellow text-secondary-fixed-dim flex items-center justify-center mb-6">
              <Users className="h-6 w-6" />
            </div>
            <h3 className="text-headline-sm font-semibold text-on-surface mb-3">Lead Management</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Every chat maps to a lead profile with status, tags, source, notes, and full conversation history.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <div className="h-10 w-10 rounded-lg bg-surface-tint-red text-primary flex items-center justify-center mb-4">
              <Zap className="h-5 w-5" />
            </div>
            <h3 className="text-body-md font-semibold text-on-surface mb-2">Automatic Capture</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Inquiries become leads instantly. No manual data entry, no missed messages.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <div className="h-10 w-10 rounded-lg bg-surface-tint-yellow text-secondary-fixed-dim flex items-center justify-center mb-4">
              <UserCheck className="h-5 w-5" />
            </div>
            <h3 className="text-body-md font-semibold text-on-surface mb-2">Lead Assignment</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Assign leads to team members so everyone knows who they're responsible for.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <div className="h-10 w-10 rounded-lg bg-surface-tint-red text-primary flex items-center justify-center mb-4">
              <MessageSquare className="h-5 w-5" />
            </div>
            <h3 className="text-body-md font-semibold text-on-surface mb-2">Conversation History</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Full context of every interaction preserved, even if a lead goes quiet for months.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <div className="h-10 w-10 rounded-lg bg-surface-tint-yellow text-secondary-fixed-dim flex items-center justify-center mb-4">
              <Globe className="h-5 w-5" />
            </div>
            <h3 className="text-body-md font-semibold text-on-surface mb-2">Website Forms</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Embed lead capture forms on your website that feed directly into Nextora.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm">
            <div className="h-10 w-10 rounded-lg bg-surface-tint-red text-primary flex items-center justify-center mb-4">
              <Filter className="h-5 w-5" />
            </div>
            <h3 className="text-body-md font-semibold text-on-surface mb-2">Source Tracking</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Know exactly where every lead came from so you can focus on what works.
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl border border-outline-variant shadow-sm md:col-span-2 lg:col-span-1">
            <div className="h-10 w-10 rounded-lg bg-surface-tint-yellow text-secondary-fixed-dim flex items-center justify-center mb-4">
              <BarChart3 className="h-5 w-5" />
            </div>
            <h3 className="text-body-md font-semibold text-on-surface mb-2">Analytics</h3>
            <p className="text-body-sm text-on-surface-variant leading-relaxed">
              Understand your lead flow, team performance, and conversion rates with clear metrics.
            </p>
          </div>

        </div>
      </div>
    </section>
  );
}
