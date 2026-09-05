import { NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Camera,
  MessageCircle,
  Users,
  Radio,
  FileText,
  Zap,
  BarChart3,
  UserCog,
  Tag,
  PieChart,
  Settings,
  CreditCard,
  HelpCircle,
  Crown,
  Sparkles,
} from "lucide-react";
import { cn } from "@/utils/cn";
import { useInboxConversations } from "@/api/conversations.queries";

interface NavItemConfig {
  name: string;
  to: string;
  icon: any;
  exact?: boolean;
  badge?: string | number | null;
  badgeVariant?: "rose" | "purple";
  disabledReason?: string;
}

interface SidebarProps {
  className?: string;
  onNavigate?: () => void;
}

function NavItem({
  item,
  onNavigate,
}: {
  item: NavItemConfig;
  onNavigate?: () => void;
}) {
  const location = useLocation();

  if (item.disabledReason) return <div title={item.disabledReason} className="px-3.5 py-2.5 text-slate-400"><span className="flex items-center gap-3 text-sm"><item.icon className="h-4 w-4" />{item.name}</span><span className="text-[10px] block pl-7 mt-1">{item.disabledReason}</span></div>;

  let isActive = false;
  if (item.exact) {
    isActive = location.pathname === item.to;
  } else if (item.to === "/app/settings") {
    // Only active when strictly on /app/settings or /app/settings/organization
    isActive = location.pathname === "/app/settings" || location.pathname === "/app/settings/organization";
  } else {
    isActive = location.pathname === item.to || location.pathname.startsWith(item.to + "/");
  }

  return (
    <NavLink
      to={item.to}
      onClick={onNavigate}
      className={cn(
        "group relative flex items-center justify-between rounded-xl px-3.5 py-2.5 text-sm font-medium transition-all duration-150",
        isActive
          ? "bg-gradient-to-r from-rose-50 to-pink-50/80 text-rose-600 font-semibold border border-rose-100/70 shadow-sm"
          : "text-slate-600 hover:text-slate-900 hover:bg-slate-50/80"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <div className="flex items-center gap-3 min-w-0">
        <item.icon
          className={cn(
            "h-4.5 w-4.5 shrink-0 transition-colors",
            isActive ? "text-rose-600" : "text-slate-400 group-hover:text-slate-600"
          )}
        />
        <span className="truncate">{item.name}</span>
      </div>

      {item.badge != null && item.badge !== "" && item.badge !== 0 && (
        <span
          className={cn(
            "px-2 py-0.5 text-[11px] font-semibold rounded-full shrink-0 shadow-2xs",
            item.badgeVariant === "purple"
              ? "bg-purple-100/80 text-purple-700 border border-purple-200/50"
              : "bg-rose-100 text-rose-600 border border-rose-200/50"
          )}
        >
          {item.badge}
        </span>
      )}
    </NavLink>
  );
}

export default function Sidebar({ className, onNavigate }: SidebarProps) {
  // Fetch real-time unread conversations count
  const { data: unreadData } = useInboxConversations({ unread: true });
  const unreadCount = unreadData?.count ?? (Array.isArray(unreadData) ? unreadData.length : 0);

  /** Main navigation items */
  const primaryNav: NavItemConfig[] = [
    { name: "Dashboard",       to: "/app",                icon: LayoutDashboard, exact: true },
    { name: "Inbox",           to: "/app/conversations",   icon: MessageCircle,   badge: unreadCount > 0 ? unreadCount : null, badgeVariant: "rose" },
    { name: "Leads",           to: "/app/leads",           icon: Users },
    { name: "Customers",       to: "/app/customers",       icon: Users },
    { name: "Bookings",        to: "/app/bookings",        icon: FileText },
    { name: "Calendar",        to: "/app/calendar",        icon: LayoutDashboard },
    { name: "Services",        to: "/app/services",        icon: Camera },
    { name: "Availability",    to: "/app/availability",    icon: Settings },
    { name: "Channels",        to: "/app/settings/channels", icon: Radio },
    { name: "Forms",           to: "/app/settings/website",  icon: FileText },
    { name: "Automations",     to: "/app/automations",        icon: Zap },
    { name: "Lead keywords", to: "/app/triggers", icon: Zap },
    { name: "Analytics",       to: "/app/analytics",       icon: BarChart3 },
    { name: "Team",            to: "/app/settings/team",   icon: UserCog },
    { name: "Tags & Segments", to: "", icon: Tag, disabledReason: "Manage tags in a lead. Segments unavailable." },
    { name: "Reports", to: "", icon: PieChart, disabledReason: "Separate reports unavailable. Use Analytics." },
  ];

  /** Bottom secondary navigation */
  const secondaryNav: NavItemConfig[] = [
    { name: "Settings",        to: "/app/settings",       icon: Settings },
    { name: "Subscription",    to: "/app/settings/subscription", icon: CreditCard },
    { name: "Help & Support", to: "", icon: HelpCircle, disabledReason: "Support portal is not configured." },
  ];

  return (
    <aside
      className={cn(
        "flex flex-col h-full w-64 shrink-0 bg-white border-r border-slate-200/80 select-none shadow-xs",
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center px-5 shrink-0 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <img
            src="/lead.png"
            alt="Nextora Lead Capture Machine"
            className="h-14 w-auto object-contain shrink-0"
          />
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-1 scrollbar-thin scrollbar-thumb-slate-200">
        {primaryNav.map((item) => (
          <NavItem key={item.name} item={item} onNavigate={onNavigate} />
        ))}
      </nav>

      {/* Bottom Section */}
      <div className="p-3 space-y-3 shrink-0 border-t border-slate-100 bg-slate-50/40">
        {/* Secondary Links */}
        <div className="space-y-1">
          {secondaryNav.map((item) => (
            <NavItem key={item.name} item={item} onNavigate={onNavigate} />
          ))}
        </div>

        {/* Upgrade to Pro Card */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-rose-50/80 via-pink-50/50 to-orange-50/40 p-4 border border-rose-100/90 shadow-2xs">
          <div className="flex items-start gap-2.5">
            <div className="p-2 rounded-xl bg-gradient-to-br from-rose-500 to-pink-500 text-white shadow-xs shrink-0">
              <Crown className="h-4 w-4" />
            </div>
            <div>
              <h4 className="text-xs font-bold text-slate-900 flex items-center gap-1">
                Upgrade to Pro
                <Sparkles className="h-3 w-3 text-amber-500 fill-amber-500" />
              </h4>
              <p className="text-[11px] text-slate-500 leading-tight mt-0.5">
                Unlock advanced features and grow faster.
              </p>
            </div>
          </div>
          <NavLink
            to="/app/settings/subscription"
            onClick={onNavigate}
            className="mt-3 flex items-center justify-center w-full py-2 px-3 text-xs font-semibold text-white bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 rounded-xl shadow-xs transition-all active:scale-[0.98]"
          >
            Upgrade Now
          </NavLink>
        </div>
      </div>
    </aside>
  );
}
