import { formatCurrencyTotals } from "@/utils/money";
import { useState } from "react";
import {
  useAdminKPIs,
  useAdminAnalytics,
  useAdminSystem,
} from "@/api/admin.queries";
import {
  Users,
  CreditCard,
  DollarSign,
  TrendingUp,
  Activity,
  Zap,
  CheckCircle2,
  Sparkles,
  PieChart as PieIcon,
  BarChart3,
  Camera,
  MessageCircle,
  Globe,
  Crown,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/common/states/ErrorState";

export default function AdminDashboard() {
  const [timeframe, setTimeframe] = useState("30d");

  const { data: kpis, isLoading: isKpisLoading, isError: isKpisError, refetch: refetchKpis } = useAdminKPIs();
  const { data: analytics, isLoading: isAnalyticsLoading, isError: isAnalyticsError, refetch: refetchAnalytics } = useAdminAnalytics(timeframe);
  const { data: systemData, isLoading: isSystemLoading, isError: isSystemError, refetch: refetchSystem } = useAdminSystem();

  if (isKpisError || isAnalyticsError || isSystemError) {
    return <ErrorState title="Failed to load admin dashboard" message="Dashboard data is temporarily unavailable. Please try again shortly." onRetry={() => { refetchKpis(); refetchAnalytics(); refetchSystem(); }} />;
  }

  if (isKpisLoading || isAnalyticsLoading || isSystemLoading) {
    return (
      <div className="py-12 flex items-center justify-center text-slate-500 text-sm font-medium">
        <div className="h-5 w-5 rounded-full border-2 border-rose-600 border-t-transparent animate-spin mr-3" />
        Loading Admin Dashboard Telemetry...
      </div>
    );
  }

  const kpiList = [
    {
      title: "Total Registered Users",
      value: kpis?.total_users ?? 0,
      subtext: kpis?.user_growth_pct == null ? "No previous-period baseline" : `${kpis.user_growth_pct}% growth vs prev period`,
      icon: Users,
      color: "text-blue-600",
      bg: "bg-blue-50 border-blue-100",
    },
    {
      title: "Free Plan Users",
      value: kpis?.free_plan_users ?? 0,
      subtext: `${kpis?.free_plan_pct ?? 0}% of total userbase`,
      icon: CheckCircle2,
      color: "text-emerald-600",
      bg: "bg-emerald-50 border-emerald-100",
    },
    {
      title: "Active Starter Users",
      value: kpis?.starter_users ?? 0,
      subtext: "Active subscriptions in this tier",
      icon: CreditCard,
      color: "text-indigo-600",
      bg: "bg-indigo-50 border-indigo-100",
    },
    {
      title: "Active Creator Users",
      value: kpis?.creator_users ?? 0,
      subtext: "Active subscriptions in this tier",
      icon: Crown,
      color: "text-pink-600",
      bg: "bg-pink-50 border-pink-100",
    },
    {
      title: "Active Enterprise Users",
      value: kpis?.enterprise_users ?? 0,
      subtext: "Active subscriptions in this tier",
      icon: Sparkles,
      color: "text-purple-600",
      bg: "bg-purple-50 border-purple-100",
    },
    {
      title: "Monthly Plan Value (USD catalog)",
      value: `$${Number(kpis?.mrr_usd || 0).toLocaleString("en-US", { minimumFractionDigits: 2 })}`,
      subtext: "Current plan prices; excludes add-ons and discounts",
      icon: DollarSign,
      color: "text-emerald-600",
      bg: "bg-emerald-50 border-emerald-100",
    },
    {
      title: "Total Revenue Collected",
      value: formatCurrencyTotals(kpis?.revenue_by_currency),
      subtext: "Sum of successful transactions",
      icon: TrendingUp,
      color: "text-amber-600",
      bg: "bg-amber-50 border-amber-100",
    },
    {
      title: "Paid Subscribers",
      value: kpis?.active_subscriptions ?? 0,
      subtext: `${kpis?.conversion_rate ?? 0}% overall conversion rate`,
      icon: Activity,
      color: "text-rose-600",
      bg: "bg-rose-50 border-rose-100",
    },
  ];

  return (
    <div className="space-y-8 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            Super Admin Overview <Sparkles className="h-5 w-5 text-amber-500 fill-amber-400" />
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Real-time business health, revenue telemetry, user growth, and lead capture statistics.
          </p>
        </div>

        {/* Timeframe selector */}
        <div className="flex items-center gap-1 bg-white p-1 rounded-xl border border-slate-200 shadow-sm self-start sm:self-auto">
          {["7d", "30d", "3m", "6m", "1y"].map((t) => (
            <button
              key={t}
              onClick={() => setTimeframe(t)}
              className={`px-3 py-1 text-xs font-extrabold rounded-lg transition-all ${
                timeframe === t
                  ? "bg-rose-600 text-white shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {t.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {kpiList.map((kpi, idx) => (
          <Card key={idx} className="bg-white border-slate-200/80 shadow-sm rounded-2xl overflow-hidden relative hover:border-slate-300 transition-colors">
            <CardHeader className="p-5 pb-2 flex flex-row items-center justify-between">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{kpi.title}</span>
              <div className={`p-2 rounded-xl border ${kpi.bg} ${kpi.color}`}>
                <kpi.icon className="h-4 w-4" />
              </div>
            </CardHeader>
            <CardContent className="p-5 pt-0">
              <div className="text-2xl font-black text-slate-900 tracking-tight mt-1">{kpi.value}</div>
              <p className="text-[11px] text-slate-500 mt-1 font-medium">{kpi.subtext}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Analytics & Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User & Revenue Growth Trends */}
        <Card className="lg:col-span-2 bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
          <CardHeader className="p-0 pb-6 border-b border-slate-100 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-rose-600" /> User & Revenue Growth ({timeframe.toUpperCase()})
              </CardTitle>
              <CardDescription className="text-xs text-slate-500 mt-0.5 font-medium">
                New registration volume and daily revenue generation
              </CardDescription>
            </div>
          </CardHeader>

          <CardContent className="p-0 pt-6 space-y-6">
            <div className="space-y-4">
              <div className="flex justify-between items-center text-xs font-bold text-slate-600">
                <span>Registrations Trend</span>
                <span className="text-slate-900 font-extrabold">{analytics?.user_growth?.length || 0} active days</span>
              </div>
              <div className="h-36 flex items-end gap-1.5 pt-4 border-b border-slate-100 pb-2 overflow-x-auto">
                {(analytics?.user_growth || []).slice(-15).map((point: any, i: number) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 group">
                    <div
                      className="w-full bg-gradient-to-t from-rose-500 to-pink-500 rounded-t-sm transition-all group-hover:brightness-110"
                      style={{ height: `${Math.max(12, point.count * 20)}px` }}
                    />
                    <span className="text-[9px] text-slate-400 font-semibold">{point.date.slice(5)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <div className="flex justify-between items-center text-xs font-bold text-slate-600">
                <span>Recorded revenue by date and currency</span>
                <span className="text-emerald-600 font-extrabold">{formatCurrencyTotals(kpis?.revenue_by_currency)}</span>
              </div>
              <div className="h-36 overflow-auto space-y-2 text-xs">
                {!analytics?.revenue_growth?.length && <p className="text-slate-500">No payments in this period.</p>}
                {(analytics?.revenue_growth || []).slice(-15).map((point: any) => (
                  <div key={`${point.date}-${point.currency}`} className="flex justify-between gap-4"><span>{point.date}</span><span>{point.currency} {point.amount}</span></div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Subscription Plan Distribution Donut */}
        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <CardHeader className="p-0 pb-5 border-b border-slate-100">
              <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
                <PieIcon className="h-5 w-5 text-indigo-600" /> Plan Distribution
              </CardTitle>
              <CardDescription className="text-xs text-slate-500 mt-0.5 font-medium">
                Active subscription breakdown
              </CardDescription>
            </CardHeader>

            <CardContent className="p-0 pt-6 space-y-4">
              {(analytics?.subscription_distribution || []).map((item: any) => (
                <div key={item.plan_code} className="space-y-1.5">
                  <div className="flex justify-between text-xs font-bold">
                    <span className="text-slate-900 capitalize">{item.plan_name} Plan</span>
                    <span className="text-slate-500">
                      {item.count} subscriptions ({item.percentage}%)
                    </span>
                  </div>
                  <div className="h-2.5 w-full bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200">
                    <div
                      className={`h-full rounded-full transition-all ${
                        item.plan_code === "free"
                          ? "bg-slate-400"
                          : item.plan_code === "starter"
                          ? "bg-indigo-600"
                          : item.plan_code === "creator"
                          ? "bg-pink-600"
                          : "bg-purple-600"
                      }`}
                      style={{ width: `${Math.max(0, Math.min(100, item.percentage))}%` }}
                    />
                  </div>
                </div>
              ))}
            </CardContent>
          </div>

          <div className="mt-6 pt-4 border-t border-slate-100">
            <Button
              onClick={() => (window.location.href = "/admin/subscriptions")}
              className="w-full bg-slate-100 hover:bg-slate-200 text-xs font-bold text-slate-900 h-10 rounded-xl"
            >
              Manage Subscription Plans →
            </Button>
          </div>
        </Card>
      </div>

      {/* Lead Usage & Channel Analytics */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
        <CardHeader className="p-0 pb-6 border-b border-slate-100 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Zap className="h-5 w-5 text-amber-500" /> Platform Lead Telemetry
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5 font-medium">
              Combined lead capture across Instagram, WhatsApp, and Website forms
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="p-0 pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-pink-100 text-pink-600 border border-pink-200 shrink-0">
                <Camera className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-black text-slate-900">
                  {analytics?.lead_analytics?.channel_breakdown?.instagram || 0}
                </div>
                <div className="text-xs font-semibold text-slate-500">Instagram DM Leads</div>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-emerald-100 text-emerald-600 border border-emerald-200 shrink-0">
                <MessageCircle className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-black text-slate-900">
                  {analytics?.lead_analytics?.channel_breakdown?.whatsapp || 0}
                </div>
                <div className="text-xs font-semibold text-slate-500">WhatsApp Inquiries</div>
              </div>
            </div>

            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center gap-4">
              <div className="p-3 rounded-xl bg-blue-100 text-blue-600 border border-blue-200 shrink-0">
                <Globe className="h-6 w-6" />
              </div>
              <div>
                <div className="text-2xl font-black text-slate-900">
                  {analytics?.lead_analytics?.channel_breakdown?.website || 0}
                </div>
                <div className="text-xs font-semibold text-slate-500">Website Submissions</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity Feed */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
        <CardHeader className="p-0 pb-5 border-b border-slate-100 flex justify-between items-center">
          <div>
            <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Activity className="h-5 w-5 text-rose-600" /> System Activity Stream
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 mt-0.5 font-medium">
              Live audit events, payments, and registrations
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="p-0 pt-5">
          <div className="space-y-3">
            {(systemData?.recent_activity || []).map((act: any) => (
              <div
                key={act.id}
                className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`h-2.5 w-2.5 rounded-full shrink-0 ${
                      act.type === "registration"
                        ? "bg-blue-500"
                        : act.type === "payment"
                        ? "bg-emerald-500"
                        : "bg-amber-500"
                    }`}
                  />
                  <div>
                    <h4 className="text-xs font-bold text-slate-900">{act.title}</h4>
                    <p className="text-xs text-slate-500">{act.description}</p>
                  </div>
                </div>
                <span className="text-[10px] text-slate-400 font-semibold shrink-0">
                  {new Date(act.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
