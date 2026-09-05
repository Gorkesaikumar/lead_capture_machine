import { ErrorState } from "@/components/common/states/ErrorState";
import { useState } from "react";
import {
  useAdminUserDetail,
  useAdminUserAction,
} from "@/api/admin.queries";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  User as UserIcon,
  Building2,
  CreditCard,
  Zap,
  History,
  ShieldAlert,
  Calendar,
  RefreshCw,
} from "lucide-react";

interface AdminUserDetailModalProps {
  userId: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function AdminUserDetailModal({
  userId,
  isOpen,
  onClose,
}: AdminUserDetailModalProps) {
  const { data, isLoading, isError, refetch } = useAdminUserDetail(userId || undefined);
  const actionMutation = useAdminUserAction();

  const [confirmAction, setConfirmAction] = useState<string | null>(null);
  const [selectedPlanCode, setSelectedPlanCode] = useState("starter");

  if (!isOpen || !userId) return null;
  if (isError) return <Dialog open={isOpen} onOpenChange={onClose}><DialogContent><DialogHeader><DialogTitle>User data unavailable</DialogTitle></DialogHeader><ErrorState title="Could not load user" message="Please retry to view saved account information." onRetry={refetch} /></DialogContent></Dialog>;

  const user = data?.user;
  const org = data?.organization;
  const sub = data?.subscription;
  const usage = data?.usage;
  const payments = data?.payment_history || [];

  const handleAction = async (actionType: string, payload: any = {}) => {
    try {
      const res = await actionMutation.mutateAsync({
        userId,
        action: actionType,
        ...payload,
      });
      toast.success(res.message || "Action executed successfully.");
      setConfirmAction(null);
      refetch();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to execute administrative action.");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl bg-white border-slate-200 text-slate-900 max-h-[90vh] overflow-y-auto p-6 sm:p-8 rounded-3xl shadow-2xl">
        <DialogHeader className="border-b border-slate-100 pb-4 flex flex-row items-center justify-between">
          <div>
            <DialogTitle className="text-xl font-extrabold flex items-center gap-2 text-slate-900">
              <UserIcon className="h-5 w-5 text-rose-600" />
              {user?.full_name || user?.email}
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500 mt-1 font-medium">
              User ID: {user?.id} • Registered: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
            </DialogDescription>
          </div>
          <Badge
            className={`capitalize font-bold px-3 py-1 ${
              user?.is_active
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-rose-50 text-rose-700 border-rose-200"
            }`}
          >
            {isLoading ? "Loading account" : user?.is_active ? "Active Account" : "Suspended"}
          </Badge>
        </DialogHeader>

        {isLoading ? (
          <div className="py-12 text-center text-slate-500 text-sm font-medium">
            Loading user telemetry & billing details...
          </div>
        ) : (
          <div className="space-y-6 pt-4">
            {/* Confirmation Overlay for Sensitive Actions */}
            {confirmAction && (
              <div className="p-4 rounded-2xl bg-rose-50 border-2 border-rose-200 space-y-3 animate-in fade-in">
                <div className="flex items-center gap-2 text-rose-700 font-bold text-sm">
                  <ShieldAlert className="h-5 w-5" />
                  Confirm Administrative Action: <span className="uppercase">{confirmAction}</span>
                </div>
                <p className="text-xs text-slate-700 font-medium">
                  {confirmAction === "suspend"
                    ? "This action will block the user from logging in or capturing leads."
                    : confirmAction === "reactivate"
                    ? "This action will restore access for the user and their workspace."
                    : confirmAction === "reset_usage"
                    ? "This action will reset current monthly lead counters to 0."
                    : "Are you sure you want to proceed with this administrative update?"}
                </p>

                {confirmAction === "change_plan" && (
                  <div className="flex items-center gap-3">
                    <label className="text-xs font-semibold text-slate-700">Select Target Plan:</label>
                    <select
                      value={selectedPlanCode}
                      onChange={(e) => setSelectedPlanCode(e.target.value)}
                      className="bg-white border border-slate-300 text-xs font-bold text-slate-900 rounded-lg p-2"
                    >
                      <option value="free">Free</option>
                      <option value="starter">Starter</option>
                      <option value="creator">Creator</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-2">
                  <Button size="sm" variant="ghost" onClick={() => setConfirmAction(null)} className="text-xs font-semibold">
                    Cancel
                  </Button>
                  <Button
                    size="sm"
                    className="bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs"
                    onClick={() => {
                      if (confirmAction === "change_plan") {
                        handleAction("change_plan", { plan_code: selectedPlanCode });
                      } else {
                        handleAction(confirmAction);
                      }
                    }}
                  >
                    Execute {confirmAction.replace("_", " ")}
                  </Button>
                </div>
              </div>
            )}

            {/* Profile & Organization Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <UserIcon className="h-3.5 w-3.5 text-slate-400" /> Account Profile
                </div>
                <div className="text-sm font-bold text-slate-900">{user?.full_name || "N/A"}</div>
                <div className="text-xs text-slate-600 font-medium">{user?.email}</div>
                <div className="text-[11px] text-slate-400">
                  Last Login: {user?.last_login ? new Date(user.last_login).toLocaleString() : "Never"}
                </div>
              </div>

              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                  <Building2 className="h-3.5 w-3.5 text-slate-400" /> Organization / Workspace
                </div>
                <div className="text-sm font-bold text-slate-900">{org?.name || "None"}</div>
                <div className="text-xs text-slate-500 font-medium">Slug: {org?.slug || "N/A"}</div>
                <div className="text-[11px] text-slate-400">
                  Team Members: {org?.members?.length ?? "Unavailable"} registered
                </div>
              </div>
            </div>

            {/* Subscription & Usage Status */}
            <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-4">
              <div className="flex justify-between items-center border-b border-slate-200 pb-3">
                <div className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5 text-indigo-600" />
                  <span className="text-sm font-extrabold text-slate-900">
                    {sub?.plan_name || "Free"} Subscription
                  </span>
                </div>
                <Badge className="bg-indigo-50 text-indigo-700 border-indigo-200 capitalize font-bold">
                  Status: {sub?.status || "active"}
                </Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 font-medium">Charged Amount:</span>
                  <div className="font-bold text-slate-900 mt-0.5">
                    {sub?.billing_currency === "INR" ? "₹" : "$"}{sub?.charged_amount || "0.00"} / mo
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 font-medium">Billing Cycle:</span>
                  <div className="font-bold text-slate-900 mt-0.5">Monthly</div>
                </div>
                <div>
                  <span className="text-slate-500 font-medium">Current Period End:</span>
                  <div className="font-bold text-slate-900 mt-0.5">
                    {sub?.period_end ? new Date(sub.period_end).toLocaleDateString() : "N/A"}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500 font-medium">Cancel at period end:</span>
                  <div className="font-bold text-slate-900 mt-0.5">
                    {sub ? (sub.cancel_at_period_end ? "Yes" : "No") : "Unavailable"}
                  </div>
                </div>
              </div>

              {/* Usage Progress Bar */}
              <div className="space-y-2 pt-2 border-t border-slate-200">
                <div className="flex justify-between text-xs font-bold">
                  <span className="text-slate-700 flex items-center gap-1">
                    <Zap className="h-3.5 w-3.5 text-amber-500" /> Combined Lead Quota
                  </span>
                  <span className="text-slate-900">
                    {usage?.total_used || 0} / {usage?.lead_limit ?? "Unavailable"} Leads ({usage?.usage_percentage || 0}%)
                  </span>
                </div>
                <div className="h-3 w-full bg-slate-200/80 rounded-full overflow-hidden p-0.5 border border-slate-200">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-rose-500 via-purple-600 to-indigo-600 transition-all"
                    style={{ width: `${Math.min(100, usage?.usage_percentage || 0)}%` }}
                  />
                </div>
                <div className="grid grid-cols-3 text-[11px] text-slate-500 text-center pt-1 font-medium">
                  <span>Instagram: {usage?.instagram_count || 0}</span>
                  <span>WhatsApp: {usage?.whatsapp_count || 0}</span>
                  <span>Website: {usage?.website_count || 0}</span>
                </div>
              </div>
            </div>

            {/* Payment History */}
            <div className="space-y-3">
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <History className="h-4 w-4 text-emerald-600" /> Verified Payment Ledger
              </h4>
              {payments.length === 0 ? (
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-500 text-center font-medium">
                  No billing transactions recorded.
                </div>
              ) : (
                <div className="border border-slate-200 rounded-xl overflow-hidden">
                  <table className="w-full text-xs text-left text-slate-700">
                    <thead className="bg-slate-50 text-slate-500 font-extrabold uppercase tracking-wider border-b border-slate-200">
                      <tr>
                        <th className="p-3">Txn ID</th>
                        <th className="p-3">Amount</th>
                        <th className="p-3">Status</th>
                        <th className="p-3">Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 bg-white">
                      {payments.map((tx: any) => (
                        <tr key={tx.id}>
                          <td className="p-3 font-mono text-slate-900 font-semibold">{tx.transaction_id}</td>
                          <td className="p-3 font-bold text-emerald-700">
                            {tx.currency} {tx.amount}
                          </td>
                          <td className="p-3">
                            <Badge className="bg-emerald-50 text-emerald-700 border-emerald-200 text-[10px] capitalize font-bold">
                              {tx.status}
                            </Badge>
                          </td>
                          <td className="p-3 text-slate-500 font-medium">{new Date(tx.created_at).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Super Admin Action Controls */}
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-rose-600">
                Super Admin Actions
              </h4>
              <div className="flex flex-wrap gap-2">
                {user?.is_active ? (
                  <Button
                    size="sm"
                    onClick={() => setConfirmAction("suspend")}
                    className="bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 text-xs font-bold"
                  >
                    Suspend Account
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    onClick={() => setConfirmAction("reactivate")}
                    className="bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 text-xs font-bold"
                  >
                    Reactivate Account
                  </Button>
                )}

                <Button
                  size="sm"
                  onClick={() => setConfirmAction("change_plan")}
                  className="bg-white hover:bg-slate-100 text-slate-900 border border-slate-200 text-xs font-bold"
                >
                  Change Subscription Plan
                </Button>

                <Button
                  size="sm"
                  onClick={() => setConfirmAction("extend_period")}
                  className="bg-white hover:bg-slate-100 text-slate-900 border border-slate-200 text-xs font-bold"
                >
                  <Calendar className="h-3.5 w-3.5 mr-1" /> Extend +30 Days
                </Button>

                <Button
                  size="sm"
                  onClick={() => setConfirmAction("reset_usage")}
                  className="bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200 text-xs font-bold"
                >
                  <RefreshCw className="h-3.5 w-3.5 mr-1" /> Reset Lead Quota
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
