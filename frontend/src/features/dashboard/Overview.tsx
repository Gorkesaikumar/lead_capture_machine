import { useState } from "react";
import { isAxiosError } from "axios";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardSummary } from "@/api/analytics.queries";
import { useCurrentSubscription } from "@/api/subscriptions.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Users, UserPlus, MessageSquare, Target, Calendar, ChevronDown, Zap, AlertTriangle, ArrowRight } from "lucide-react";
import { DashboardKpiCard } from "./components/DashboardKpiCard";
import { LeadsTimeseriesChart } from "./components/LeadsTimeseriesChart";
import { ChannelStatusCard } from "./components/ChannelStatusCard";
import { RecentLeadsTable } from "./components/RecentLeadsTable";
import { ActivityFeedCard } from "./components/ActivityFeedCard";
import { Button } from "@/components/ui/button";

export default function Overview() {
  const { user } = useAuth();
  const [preset, setPreset] = useState("this_month");

  // Fetch Subscription & Quota status
  const { data: subData, isError: isSubscriptionError } = useCurrentSubscription();

  // Fetch Dashboard Summary
  const {
    data: summary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
    error: summaryError,
    refetch: refetchSummary,
  } = useDashboardSummary(preset);

  const isLoading = isSummaryLoading;

  if (isSummaryError) {
    const status = isAxiosError(summaryError) ? summaryError.response?.status : undefined;
    const message = status === 403
      ? "You no longer have access to this workspace. Ask your workspace owner to check your membership."
      : status && status >= 500
      ? "Dashboard data is temporarily unavailable. Please try again shortly."
      : "We couldn't retrieve the latest operational metrics. Please try again.";
    return (
      <PageContainer>
        <ErrorState
          title="Failed to load dashboard"
          message={message}
          onRetry={refetchSummary}
        />
      </PageContainer>
    );
  }

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  const userName = user?.full_name || user?.name || user?.email;

  const totalLeadsCount = subData?.usage?.total_leads_count;
  const leadLimit = subData?.plan?.lead_limit;
  const usagePct = subData?.usage?.usage_percentage ?? 0;
  const leadsRemaining = subData?.usage?.leads_remaining;

  const isWarning = usagePct >= 80 && usagePct < 100;
  const isCritical = usagePct >= 100;


  return (
    <PageContainer>
      <div className="space-y-6 pb-6">
        {/* Quota Banner Alert on Dashboard */}
        {isSubscriptionError && <p className="text-sm text-slate-500">Plan usage is temporarily unavailable.</p>}
        {!isSubscriptionError && subData?.plan && subData?.usage && (
          <div
            className={`p-4 rounded-2xl border shadow-2xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all ${
              isCritical
                ? "bg-rose-50 border-rose-200 text-rose-950"
                : isWarning
                ? "bg-amber-50 border-amber-200 text-amber-950"
                : "bg-white border-slate-200/80 text-slate-900"
            }`}
          >
            <div className="flex items-center gap-3 flex-1">
              <div
                className={`h-9 w-9 rounded-xl flex items-center justify-center shrink-0 ${
                  isCritical ? "bg-rose-500 text-white" : isWarning ? "bg-amber-500 text-white" : "bg-rose-50 text-rose-600"
                }`}
              >
                {isCritical || isWarning ? <AlertTriangle className="h-5 w-5" /> : <Zap className="h-5 w-5" />}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
                    {subData.plan.name} Plan Usage
                  </span>
                  <span className="text-xs font-bold text-slate-700">
                    ({totalLeadsCount} / {leadLimit} Combined Leads)
                  </span>
                </div>
                {/* Embedded Progress Bar */}
                <div className="h-2 w-full max-w-md bg-slate-100 rounded-full overflow-hidden mt-1.5 border border-slate-200/50">
                  <div
                    className={`h-full rounded-full transition-all ${
                      isCritical ? "bg-rose-500" : isWarning ? "bg-amber-500" : "bg-rose-500"
                    }`}
                    style={{ width: `${usagePct}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <span className={`text-xs font-bold ${isCritical ? "text-rose-600" : "text-slate-600"}`}>
                {leadsRemaining} Leads Remaining
              </span>
              <a href="/app/settings/subscription">
                <Button size="sm" className="bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs rounded-xl shadow-2xs">
                  Upgrade Plan <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              </a>
            </div>
          </div>
        )}

        {/* Dashboard Header: Greeting & Date Range Picker */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-2">
              {getGreeting()}, {userName} <span className="animate-bounce">👋</span>
            </h1>
            <p className="text-xs sm:text-sm font-medium text-slate-500 mt-1">
              Leads and activity for the selected period. Open conversations and channel status are current.
            </p>
          </div>

          {/* Date Range Selector Dropdown */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="relative inline-flex items-center">
              <Calendar className="absolute left-3.5 h-4 w-4 text-slate-400 pointer-events-none" />
              <select
                aria-label="Dashboard date range"
                value={preset}
                onChange={(e) => setPreset(e.target.value)}
                className="pl-10 pr-9 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-xs font-bold shadow-2xs hover:border-slate-300 transition-colors focus:outline-none focus:ring-2 focus:ring-rose-500/20 cursor-pointer appearance-none"
              >
                <option value="this_month">This Month</option>
                <option value="30d">Last 30 Days</option>
                <option value="7d">Last 7 Days</option>
                <option value="today">Today</option>
              </select>
              <ChevronDown className="absolute right-3 h-4 w-4 text-slate-400 pointer-events-none" />
            </div>
          </div>
        </div>

        {summary?.generated_at && <p className="text-xs text-slate-500">Updated {new Date(summary.generated_at).toLocaleTimeString(undefined, { timeZone: summary.timezone })} · {summary.timezone} · Refreshes every 30 seconds</p>}

        {isLoading ? (
          <LoadingSkeleton rows={4} />
        ) : summary ? (
          <div className="space-y-6">
            {/* Top KPI Cards Grid (4 Columns) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <DashboardKpiCard
                title="Total Leads"
                value={summary.leads?.total_leads ?? 0}
                icon={Users}
                colorScheme="pink"
              />
              <DashboardKpiCard
                title="New Leads Today"
                value={summary.leads?.new_leads_today ?? 0}
                icon={UserPlus}
                colorScheme="green"
              />
              <DashboardKpiCard
                title="Open Conversations"
                value={summary.leads?.open_conversations ?? 0}
                icon={MessageSquare}
                colorScheme="orange"
              />
              <DashboardKpiCard
                title="Conversion Rate"
                value={`${summary.leads?.lead_to_booking_conversion_rate ?? 0}%`}
                icon={Target}
                colorScheme="purple"
              />
            </div>

            {/* Row 2: Leads Overview Chart (2 Cols) & Channel Status (1 Col) */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2">
                <LeadsTimeseriesChart data={summary?.leads_timeseries || []} />
              </div>
              <div className="lg:col-span-1">
                <ChannelStatusCard channels={summary?.channels || []} />
              </div>
            </div>

            {/* Row 3: Recent Leads (1 Col) & Activity Feed (1 Col) */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="lg:col-span-1">
                <RecentLeadsTable leads={summary?.recent_leads || []} />
              </div>
              <div className="lg:col-span-1">
                <ActivityFeedCard activities={summary?.activities || []} />
              </div>
            </div>
          </div>
        ) : <ErrorState title="Dashboard unavailable" message="No dashboard response was received." onRetry={refetchSummary} />}
      </div>
    </PageContainer>
  );
}
