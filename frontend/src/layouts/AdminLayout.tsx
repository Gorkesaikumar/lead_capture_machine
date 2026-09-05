import { useState } from "react";
import { Outlet, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  LayoutDashboard,
  Users,
  CreditCard,
  TrendingUp,
  BarChart3,
  ShieldCheck,
  Activity,
  LogOut,
  ArrowLeft,
  Menu,
  X,
  Sparkles,
} from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/ui/button";

interface NavItem {
  name: string;
  to: string;
  icon: any;
  exact?: boolean;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const adminNavSections: NavSection[] = [
  {
    title: "MAIN",
    items: [
      { name: "Overview", to: "/admin", icon: LayoutDashboard, exact: true },
    ],
  },
  {
    title: "MANAGEMENT",
    items: [
      { name: "Users", to: "/admin/users", icon: Users },
      { name: "Subscriptions", to: "/admin/subscriptions", icon: CreditCard },
      { name: "Revenue & Billing", to: "/admin/revenue", icon: TrendingUp },
    ],
  },
  {
    title: "TELEMETRY",
    items: [
      { name: "Analytics", to: "/admin/analytics", icon: BarChart3 },
      { name: "Audit Logs", to: "/admin/audit-logs", icon: ShieldCheck },
      { name: "System Overview", to: "/admin/system", icon: Activity },
    ],
  },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/admin/login");
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col md:flex-row font-sans">
      {/* Mobile Header Bar */}
      <div className="md:hidden flex items-center justify-between p-4 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2">
          <img src="/lead.png" alt="Nextora" className="h-12 w-auto object-contain shrink-0" />
          <span className="font-extrabold text-slate-900 text-base">Nextora Admin</span>
        </div>
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="p-2 text-slate-600 hover:text-slate-900"
        >
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {/* Admin Sidebar */}
      <aside
        className={cn(
          "w-60 bg-white border-r border-slate-200 flex flex-col shrink-0 transition-all duration-200 z-50 h-screen sticky top-0",
          mobileOpen ? "block fixed inset-y-0 left-0 shadow-2xl" : "hidden md:flex"
        )}
      >
        {/* Sidebar Brand Header */}
        <div className="h-16 px-5 flex items-center justify-between border-b border-slate-100 shrink-0">
          <div className="flex items-center gap-3">
            <img src="/lead.png" alt="Nextora" className="h-12 w-auto object-contain shrink-0" />
            <div>
              <h2 className="font-black text-slate-900 text-sm tracking-tight flex items-center gap-1">
                Nextora Admin
                <Sparkles className="h-3 w-3 text-amber-500 fill-amber-400" />
              </h2>
              <p className="text-[10px] text-rose-600 font-bold uppercase tracking-widest">
                Super Admin Panel
              </p>
            </div>
          </div>
        </div>

        {/* Scrollable Navigation Links */}
        <nav className="flex-1 px-3 py-4 space-y-6 overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-slate-200 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-slate-300">
          {adminNavSections.map((section) => (
            <div key={section.title} className="space-y-1">
              <div className="px-3 text-[10px] font-extrabold text-slate-400 uppercase tracking-widest">
                {section.title}
              </div>
              <div className="space-y-0.5 pt-1">
                {section.items.map((item) => {
                  const isActive = item.exact
                    ? location.pathname === item.to
                    : location.pathname.startsWith(item.to);

                  return (
                    <NavLink
                      key={item.name}
                      to={item.to}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        "flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition-all duration-150",
                        isActive
                          ? "bg-gradient-to-r from-rose-500/10 via-purple-500/10 to-indigo-500/10 text-rose-700 font-extrabold border border-rose-200 shadow-sm"
                          : "text-slate-600 hover:text-slate-900 hover:bg-slate-100/80"
                      )}
                    >
                      <item.icon
                        className={cn(
                          "h-4 w-4 shrink-0 transition-colors",
                          isActive ? "text-rose-600" : "text-slate-400"
                        )}
                      />
                      <span>{item.name}</span>
                    </NavLink>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Admin Footer Actions */}
        <div className="p-3 border-t border-slate-100 bg-slate-50/50 space-y-1.5 shrink-0">
          {user?.workspace && (
          <Button
            variant="ghost"
            onClick={() => navigate("/app")}
            className="w-full justify-start text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 h-9 rounded-xl px-3"
          >
            <ArrowLeft className="h-4 w-4 mr-2 text-slate-400" /> Back to App Workspace
          </Button>
          )}

          <Button
            variant="ghost"
            onClick={handleLogout}
            className="w-full justify-start text-xs font-medium text-rose-600 hover:text-rose-700 hover:bg-rose-50 h-9 rounded-xl px-3"
          >
            <LogOut className="h-4 w-4 mr-2" /> Logout Admin
          </Button>
        </div>
      </aside>

      {/* Main Admin View Area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-screen">
        {/* Top Navbar */}
        <header className="h-16 border-b border-slate-200 bg-white/80 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40">
          <div className="text-xs font-semibold text-slate-500 flex items-center gap-2">
            <span>Admin Control</span>
            <span>/</span>
            <span className="text-slate-900 font-bold capitalize">
              {location.pathname.replace("/admin", "").replace("/", "") || "Overview"}
            </span>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <div className="text-xs font-bold text-slate-900">
                {(user as any)?.full_name || user?.name || user?.email}
              </div>
              <div className="text-[10px] text-rose-600 font-bold uppercase tracking-wider">
                Super Admin
              </div>
            </div>
            <div className="h-9 w-9 bg-rose-50 border border-rose-200 rounded-xl flex items-center justify-center font-bold text-rose-600 text-xs shadow-sm">
              {((user as any)?.full_name || user?.name || user?.email || "A").charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto space-y-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
