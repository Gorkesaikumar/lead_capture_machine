import { ErrorState } from "@/components/common/states/ErrorState";
import { useAdminSystem } from "@/api/admin.queries";
import { Activity, Info } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export default function AdminSystemOverview() {
  const { data, isLoading, isError, refetch } = useAdminSystem();

  if (isError) return <ErrorState title="Unable to load systemoverview" message="Data is unavailable. Please retry." onRetry={refetch} />;

  if (isLoading) {
    return (
      <div className="py-12 text-center text-slate-500 text-sm font-medium">
        Loading System Telemetry...
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            System & Workspace Telemetry <Activity className="h-6 w-6 text-rose-600" />
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Global system statistics, multi-tenant workspace counts, and infrastructure health.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Registered Users</span>
          <div className="text-3xl font-black text-slate-900 mt-2">{data?.total_users || 0}</div>
          <div className="text-xs text-emerald-600 font-semibold mt-1">
            {data?.active_users || 0} Active • {data?.suspended_users || 0} Suspended
          </div>
        </Card>

        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Workspaces</span>
          <div className="text-3xl font-black text-indigo-600 mt-2">{data?.total_workspaces || 0}</div>
          <div className="text-xs text-slate-500 font-medium mt-1">Multi-tenant Organizations</div>
        </Card>

        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Leads Captured</span>
          <div className="text-3xl font-black text-rose-600 mt-2">{data?.total_leads_captured || 0}</div>
          <div className="text-xs text-slate-500 font-medium mt-1">All Channels Combined</div>
        </Card>

        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">System Status</span>
          <div className="text-xl font-black text-slate-600 mt-2 flex items-center gap-2">
            <Info className="h-7 w-7 text-slate-500" /> Not monitored
          </div>
          <div className="text-xs text-slate-500 font-medium mt-1">Infrastructure health is not measured by this dashboard.</div>
        </Card>
      </div>

      {/* Activity Feed */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
        <CardHeader className="p-0 pb-5 border-b border-slate-100 flex justify-between items-center">
          <div>
            <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <Activity className="h-5 w-5 text-rose-600" /> System Activity Log
            </CardTitle>
            <CardDescription className="text-xs text-slate-500 font-medium mt-0.5">
              Real-time feed of events across the platform
            </CardDescription>
          </div>
        </CardHeader>

        <CardContent className="p-0 pt-5">
          <div className="space-y-3">
            {(data?.recent_activity || []).map((act: any) => (
              <div
                key={act.id}
                className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 flex items-center justify-between gap-4"
              >
                <div>
                  <h4 className="text-xs font-bold text-slate-900">{act.title}</h4>
                  <p className="text-xs text-slate-500 mt-0.5 font-medium">{act.description}</p>
                </div>
                <span className="text-[10px] text-slate-400 font-semibold shrink-0">
                  {new Date(act.timestamp).toLocaleString()}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
