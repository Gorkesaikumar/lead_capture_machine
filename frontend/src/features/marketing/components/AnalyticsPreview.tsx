import { TrendingUp, ArrowUpRight } from 'lucide-react';

export default function AnalyticsPreview() {
  return (
    <section className="py-[100px] px-margin-mobile md:px-margin-desktop bg-surface-tint-yellow border-y border-outline-variant/30">
      <div className="max-w-8xl mx-auto">

        <div className="text-center mb-[60px]">
          <h2 className="text-headline-md font-semibold text-primary mb-4 tracking-tight">
            Understand your pipeline.
          </h2>
          <p className="text-body-lg text-on-surface-variant max-w-2xl mx-auto">
            Nextora shows you exactly where your leads come from and how they convert — no spreadsheets required.
          </p>
        </div>

        <div className="max-w-5xl mx-auto bg-white rounded-2xl border border-outline-variant shadow-xl overflow-hidden">

          {/* Header */}
          <div className="flex items-center justify-between px-8 py-5 border-b border-outline-variant">
            <h3 className="text-headline-sm font-semibold text-on-surface">Lead Performance</h3>
            <div className="flex items-center gap-2 text-body-sm font-semibold text-green-700 bg-green-50 border border-green-100 px-3 py-1.5 rounded-full">
              <TrendingUp className="h-4 w-4" />
              +24% this month
            </div>
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-2 md:grid-cols-4 divide-x divide-outline-variant/40">
            <Metric label="Total Leads" value="1,248" delta="+12%" />
            <Metric label="New Leads" value="84" delta="+24%" />
            <Metric label="Qualified" value="890" delta="+8%" />
            <Metric label="Converted" value="412" delta="+21%" accent />
          </div>

          {/* Source bars */}
          <div className="px-8 py-6 border-t border-outline-variant">
            <div className="text-label-md font-bold text-on-surface uppercase tracking-wider mb-4">Leads by Source</div>
            <div className="flex flex-col sm:flex-row gap-3 h-auto sm:h-10">
              <div className="sm:flex-[52] bg-primary/10 text-primary font-bold rounded-lg flex items-center justify-center py-2 text-body-sm">
                Instagram (52%)
              </div>
              <div className="sm:flex-[31] bg-green-100 text-green-700 font-bold rounded-lg flex items-center justify-center py-2 text-body-sm">
                WhatsApp (31%)
              </div>
              <div className="sm:flex-[17] bg-blue-50 text-blue-700 font-bold rounded-lg flex items-center justify-center py-2 text-body-sm">
                Website (17%)
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value, delta, accent }: { label: string; value: string; delta: string; accent?: boolean }) {
  return (
    <div className="px-6 py-5">
      <div className="text-body-sm text-on-surface-variant mb-1">{label}</div>
      <div className={`text-headline-sm font-bold tracking-tight ${accent ? 'text-primary' : 'text-on-surface'}`}>{value}</div>
      <div className="text-label-sm text-green-600 font-semibold flex items-center gap-0.5 mt-1">
        <ArrowUpRight className="h-3 w-3" />
        {delta}
      </div>
    </div>
  );
}
