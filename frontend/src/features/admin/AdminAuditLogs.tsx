import { ErrorState } from "@/components/common/states/ErrorState";
import { useAdminAuditLogs } from "@/api/admin.queries";
import { ShieldCheck, User, Calendar, Terminal } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function AdminAuditLogs() {
  const { data: logs = [], isLoading, isError, refetch } = useAdminAuditLogs();

  if (isError) return <ErrorState title="Unable to load auditlogs" message="Data is unavailable. Please retry." onRetry={refetch} />;

  if (isLoading) {
    return (
      <div className="py-12 text-center text-slate-500 text-sm font-medium">
        Loading Administrative Audit Trail...
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            Super Admin Audit Trail <ShieldCheck className="h-6 w-6 text-rose-600" />
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Immutable timeline of sensitive administrative actions, plan updates, account suspensions, and manual overrides.
          </p>
        </div>
      </div>

      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
        <CardHeader className="p-0 pb-6 border-b border-slate-100">
          <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <Terminal className="h-5 w-5 text-indigo-600" /> Audit Log Activity Stream
          </CardTitle>
          <CardDescription className="text-xs text-slate-500 font-medium mt-0.5">
            Chronological record of super admin actions
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0 pt-6">
          {logs.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500 font-medium">
              No administrative audit logs recorded yet.
            </div>
          ) : (
            <div className="space-y-4">
              {logs.map((log: any) => (
                <div
                  key={log.id}
                  className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2 hover:border-slate-300 transition-colors"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-200/80 pb-2">
                    <div className="flex items-center gap-2">
                      <Badge className="bg-rose-50 text-rose-700 border-rose-200 text-[10px] uppercase font-bold">
                        {log.action}
                      </Badge>
                      <span className="text-xs font-bold text-slate-900">
                        Target: {log.target_name || log.target_id || "N/A"} ({log.target_type})
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-[11px] text-slate-500 font-medium">
                      <span className="flex items-center gap-1">
                        <User className="h-3 w-3 text-slate-400" /> {log.admin_email}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3 text-slate-400" /> {new Date(log.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-xs">
                    {Object.keys(log.previous_state || {}).length > 0 && (
                      <div className="p-2.5 rounded-xl bg-white border border-slate-200/80">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">Previous State</span>
                        <pre className="text-[11px] text-rose-700 font-mono mt-1 overflow-x-auto">
                          {JSON.stringify(log.previous_state, null, 2)}
                        </pre>
                      </div>
                    )}

                    {Object.keys(log.new_state || {}).length > 0 && (
                      <div className="p-2.5 rounded-xl bg-white border border-slate-200/80">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">New State</span>
                        <pre className="text-[11px] text-emerald-700 font-mono mt-1 overflow-x-auto">
                          {JSON.stringify(log.new_state, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
