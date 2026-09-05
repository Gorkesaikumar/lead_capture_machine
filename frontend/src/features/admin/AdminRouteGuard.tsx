import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { ShieldAlert, ArrowLeft, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function AdminRouteGuard() {
  const { user, isLoading } = useAuth();
  const isAuthenticated = Boolean(user);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-700">
        <div className="flex items-center gap-3 text-sm font-semibold">
          <div className="h-4 w-4 rounded-full border-2 border-rose-600 border-t-transparent animate-spin" />
          Verifying Admin Credentials...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  // Check backend permissions: superuser or staff status
  const isSuperAdmin = Boolean(
    (user as any)?.is_superuser || (user as any)?.is_staff
  );

  if (!isSuperAdmin) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 text-slate-900">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-3xl p-8 shadow-xl text-center space-y-6 animate-in fade-in">
          <div className="h-16 w-16 bg-rose-50 border border-rose-200 rounded-2xl flex items-center justify-center mx-auto text-rose-600 shadow-inner">
            <ShieldAlert className="h-8 w-8" />
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center justify-center gap-2">
              <Lock className="h-5 w-5 text-rose-600" /> Access Denied
            </h1>
            <p className="text-sm text-slate-600 leading-relaxed font-medium">
              You do not have Super Admin permissions to access the Nextora Control Panel. This module is restricted exclusively to authorized system administrators.
            </p>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 text-xs text-slate-600 text-left space-y-1">
            <p><span className="font-bold text-slate-900">Account:</span> {user?.email}</p>
            <p><span className="font-bold text-slate-900">Role:</span> Workspace Member</p>
            <p><span className="font-bold text-slate-900">Status:</span> Unauthorized for Super Admin Panel</p>
          </div>

          <Button
            onClick={() => (window.location.href = "/app")}
            className="w-full bg-gradient-to-r from-rose-500 via-purple-600 to-indigo-600 hover:from-rose-600 hover:to-indigo-700 text-white font-bold h-11 rounded-xl shadow-lg shadow-purple-500/20"
          >
            <ArrowLeft className="h-4 w-4 mr-2" /> Return to Application Workspace
          </Button>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
