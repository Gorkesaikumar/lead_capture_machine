import { Search } from 'lucide-react';

/** Product Preview — large realistic app UI mockup */
export default function ProductPreview() {
  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-white">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
            One workspace. Every lead.
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            A complete view of your leads, conversations, and pipeline — organized exactly how your team needs it.
          </p>
        </div>

        {/* App Frame */}
        <div className="rounded-2xl border border-outline-variant bg-surface-container shadow-2xl overflow-hidden">

          {/* Title bar */}
          <div className="flex items-center gap-2 px-4 py-3 bg-surface-container-high border-b border-outline-variant">
            <div className="w-3 h-3 rounded-full bg-red-400" />
            <div className="w-3 h-3 rounded-full bg-yellow-400" />
            <div className="w-3 h-3 rounded-full bg-green-400" />
            <div className="flex-1 mx-4">
              <div className="bg-white border border-outline-variant rounded-md px-3 py-1 text-body-sm text-on-surface-variant flex items-center gap-2 max-w-xs mx-auto">
                <span className="text-on-surface-variant/50">🔒</span>
                app.nextora.io/dashboard
              </div>
            </div>
          </div>

          <div className="flex h-[560px]">
            {/* Sidebar */}
            <div className="w-[200px] bg-on-background flex flex-col py-4 shrink-0">
              <div className="px-4 mb-6 flex items-center gap-2">
                <img src="/lead.png" alt="Nextora" className="h-14 w-auto object-contain bg-white rounded-md shrink-0" />
              </div>

              <nav className="flex flex-col gap-1 px-2">
                <SidebarItem label="Dashboard" active />
                <SidebarItem label="Leads" />
                <SidebarItem label="Inbox" badge="12" />
                <SidebarItem label="Channels" />
                <SidebarItem label="Analytics" />
                <SidebarItem label="Team" />
              </nav>
            </div>

            {/* Main content */}
            <div className="flex-1 bg-surface-container-low overflow-hidden">

              {/* Top bar */}
              <div className="flex items-center justify-between px-6 py-4 bg-white border-b border-outline-variant">
                <h1 className="font-bold text-on-surface text-headline-sm">Dashboard</h1>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 bg-surface-container border border-outline-variant rounded-lg px-3 py-1.5 text-body-sm text-on-surface-variant">
                    <Search className="h-3.5 w-3.5" />
                    Search leads...
                  </div>
                  <div className="h-8 w-8 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-body-sm">JD</div>
                </div>
              </div>

              <div className="p-6 overflow-y-auto h-full space-y-5">
                {/* KPI cards */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <KpiCard label="Total Leads" value="1,248" delta="+12%" />
                  <KpiCard label="New This Week" value="84" delta="+24%" accent />
                  <KpiCard label="Open Convos" value="342" delta="" />
                  <KpiCard label="Converted" value="412" delta="+21%" />
                </div>

                {/* Charts row */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  <div className="lg:col-span-2 bg-white rounded-xl border border-outline-variant p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="font-semibold text-on-surface text-body-sm">Leads Over Time</span>
                      <span className="text-label-sm text-on-surface-variant">Last 30 days</span>
                    </div>
                    {/* Fake sparkline */}
                    <svg viewBox="0 0 300 80" className="w-full h-16">
                      <polyline
                        points="0,60 40,45 80,50 120,30 160,35 200,20 240,25 280,10 300,8"
                        fill="none" stroke="#b80035" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
                      />
                      <polyline
                        points="0,60 40,45 80,50 120,30 160,35 200,20 240,25 280,10 300,8"
                        fill="url(#sparkGrad)" stroke="none"
                      />
                      <defs>
                        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0%" stopColor="#b80035" stopOpacity="0.15" />
                          <stop offset="100%" stopColor="#b80035" stopOpacity="0" />
                        </linearGradient>
                      </defs>
                    </svg>
                  </div>

                  <div className="bg-white rounded-xl border border-outline-variant p-4">
                    <div className="font-semibold text-on-surface text-body-sm mb-3">Leads by Source</div>
                    <div className="flex flex-col gap-2">
                      <SourceBar label="Instagram" pct={52} color="bg-primary" />
                      <SourceBar label="WhatsApp" pct={31} color="bg-green-500" />
                      <SourceBar label="Website"  pct={17} color="bg-blue-500" />
                    </div>
                  </div>
                </div>

                {/* Recent leads */}
                <div className="bg-white rounded-xl border border-outline-variant overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3 border-b border-outline-variant">
                    <span className="font-semibold text-on-surface text-body-sm">Recent Leads</span>
                    <span className="text-label-sm text-primary cursor-pointer hover:underline">View all →</span>
                  </div>
                  <div className="divide-y divide-outline-variant/30">
                    <LeadRow name="Sarah Jenkins"  source="IG"  status="Qualifying" time="2m ago" />
                    <LeadRow name="Michael Chang"  source="WA"  status="New"        time="1h ago" />
                    <LeadRow name="Elena Rodriguez" source="Web" status="Qualified"  time="4h ago" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ── sub-components ── */

function SidebarItem({ label, active, badge }: { label: string; active?: boolean; badge?: string }) {
  return (
    <div
      className={`flex items-center justify-between px-3 py-2 rounded-lg text-body-sm font-medium transition-colors cursor-pointer ${
        active
          ? 'bg-secondary-fixed-dim text-on-secondary-container font-semibold'
          : 'text-white/60 hover:text-white hover:bg-white/10'
      }`}
    >
      <span>{label}</span>
      {badge && <span className="bg-primary text-on-primary text-label-sm px-1.5 py-0.5 rounded-full">{badge}</span>}
    </div>
  );
}

function KpiCard({ label, value, delta, accent }: { label: string; value: string; delta: string; accent?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${accent ? 'bg-primary border-primary/20' : 'bg-white border-outline-variant'}`}>
      <div className={`text-body-sm font-medium mb-1 ${accent ? 'text-on-primary/80' : 'text-on-surface-variant'}`}>{label}</div>
      <div className={`text-headline-sm font-bold tracking-tight ${accent ? 'text-on-primary' : 'text-on-surface'}`}>{value}</div>
      {delta && (
        <div className={`text-label-sm font-semibold mt-1 ${accent ? 'text-on-primary/70' : 'text-green-600'}`}>{delta} vs last week</div>
      )}
    </div>
  );
}

function SourceBar({ label, pct, color }: { label: string; pct: number; color: string }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-label-sm text-on-surface-variant w-16 shrink-0">{label}</span>
      <div className="flex-1 bg-surface-container rounded-full h-2 overflow-hidden">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-label-sm text-on-surface-variant w-8 text-right shrink-0">{pct}%</span>
    </div>
  );
}

function LeadRow({ name, source, status, time }: { name: string; source: string; status: string; time: string }) {
  const statusColors: Record<string, string> = {
    New: 'bg-blue-50 text-blue-700',
    Qualifying: 'bg-yellow-50 text-yellow-700',
    Qualified: 'bg-green-50 text-green-700',
  };
  return (
    <div className="flex items-center justify-between px-4 py-3 hover:bg-surface-container-low transition-colors">
      <div className="flex items-center gap-3">
        <div className="h-8 w-8 rounded-full bg-primary-fixed flex items-center justify-center text-primary font-bold text-label-sm shrink-0">
          {name.split(' ').map(n => n[0]).join('')}
        </div>
        <div>
          <div className="text-body-sm font-semibold text-on-surface">{name}</div>
          <div className="text-label-sm text-on-surface-variant">via {source === 'IG' ? 'Instagram' : source === 'WA' ? 'WhatsApp' : 'Website'}</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className={`text-label-sm font-semibold px-2 py-0.5 rounded-full ${statusColors[status] ?? 'bg-surface-container text-on-surface-variant'}`}>
          {status}
        </span>
        <span className="text-label-sm text-on-surface-variant hidden sm:block">{time}</span>
      </div>
    </div>
  );
}
