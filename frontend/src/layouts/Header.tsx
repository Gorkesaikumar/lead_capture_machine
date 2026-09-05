import { useTeamMembers } from "@/api/team.queries";
import { useInboxConversations } from "@/api/conversations.queries";
import { Menu, LogOut, ChevronRight, Bell, UserPlus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/contexts/AuthContext";
import { useRealtime } from "@/contexts/RealtimeContext";
import { useLocation, useNavigate } from "react-router-dom";
import { cn } from "@/utils/cn";

/** Map path prefixes to human-readable page names */
const PAGE_TITLES: Record<string, string> = {
  "/app":               "Dashboard",
  "/app/conversations": "Inbox",
  "/app/leads":         "Leads",
  "/app/channels":      "Channels",
  "/app/analytics":     "Analytics",
  "/app/team":          "Team",
  "/app/customers":     "Customers",
  "/app/settings":      "Settings",
  "/app/subscription":  "Subscription",
  "/app/bookings":      "Bookings",
  "/app/calendar":      "Calendar",
  "/app/availability":  "Availability",
  "/app/services":      "Services",
  "/app/triggers":      "Lead Triggers",
  "/app/automations": "DM Automation",
};

function usePageTitle(): string {
  const { pathname } = useLocation();
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname];
  const match = Object.keys(PAGE_TITLES)
    .filter((k) => k !== "/app" && pathname.startsWith(k))
    .sort((a, b) => b.length - a.length)[0];
  return match ? PAGE_TITLES[match] : "Dashboard";
}

function RealtimeIndicator() {
  const { status } = useRealtime();

  const isConnected    = status === "CONNECTED";
  const isConnecting   = status === "CONNECTING" || status === "RECONNECTING";
  const isDisconnected = status === "DISCONNECTED";

  return (
    <div
      className={cn(
        "hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border",
        isConnected    && "bg-emerald-50 border-emerald-200 text-emerald-700",
        isConnecting   && "bg-amber-50 border-amber-200 text-amber-700",
        isDisconnected && "bg-slate-50 border-slate-200 text-slate-500"
      )}
      title={`WebSocket: ${status}`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {(isConnected || isConnecting) && (
          <span
            className={cn(
              "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
              isConnected  && "bg-emerald-400",
              isConnecting && "bg-amber-400"
            )}
          />
        )}
        <span
          className={cn(
            "relative inline-flex h-1.5 w-1.5 rounded-full",
            isConnected    && "bg-emerald-500",
            isConnecting   && "bg-amber-500",
            isDisconnected && "bg-slate-400"
          )}
        />
      </span>
      {isConnected    && "Live"}
      {isConnecting   && "Connecting"}
      {isDisconnected && "Offline"}
    </div>
  );
}

export default function Header({
  toggleMobileNav,
}: {
  toggleMobileNav: () => void;
}) {
  const { user, logout } = useAuth();
  const { data: team = [] } = useTeamMembers();
  const { data: unread } = useInboxConversations({ unread: true });
  const unreadCount = unread?.count || 0;
  const displayName = user?.full_name || user?.name || user?.email || "Account";
  const pageTitle = usePageTitle();
  const navigate = useNavigate();

  const initials = displayName.split(" ").map((w: string) => w[0]).join("").slice(0, 2).toUpperCase();
  const userRole = team.find(member => member.user.id === user?.id)?.role || "Studio account";

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white px-4 md:px-6 shadow-2xs">
      {/* Left: Mobile Toggle & Breadcrumb */}
      <div className="flex items-center gap-3 min-w-0">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden shrink-0 text-slate-600 hover:text-slate-900 hover:bg-slate-100 h-9 w-9 rounded-xl"
          onClick={toggleMobileNav}
        >
          <Menu className="h-5 w-5" />
          <span className="sr-only">Open menu</span>
        </Button>

        {/* Desktop Breadcrumb */}
        <div className="hidden md:flex items-center gap-2 text-sm">
          <span className="font-semibold text-slate-900">Nextora</span>
          <ChevronRight className="h-4 w-4 text-slate-400" />
          <span className="font-medium text-slate-500">{pageTitle}</span>
        </div>

        {/* Mobile Page Title */}
        <span className="md:hidden text-base font-semibold text-slate-900 truncate">
          {pageTitle}
        </span>
      </div>

      {/* Right Actions: Invite Team, Notifications, User Menu */}
      <div className="flex items-center gap-3 shrink-0">
        <RealtimeIndicator />

        {/* Invite Team Action */}
        <button
          onClick={() => navigate("/app/settings/team")}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-600 bg-rose-50/60 hover:bg-rose-100/70 border border-rose-200/70 rounded-xl transition-all shadow-2xs active:scale-[0.98]"
        >
          <UserPlus className="h-3.5 w-3.5" />
          <span>Invite Team</span>
        </button>

        {/* Notification Bell */}
        <button
          className="relative p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100/80 transition-colors"
          title="Open unread conversations"
          onClick={() => navigate("/app/conversations")}
        >
          <Bell className="h-4.5 w-4.5 text-slate-600" />
          {unreadCount > 0 && <span className="absolute top-1.5 right-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-rose-500 text-[10px] font-bold text-white shadow-2xs">{unreadCount}</span>}
        </button>

        <div className="h-4 w-px bg-slate-200 mx-0.5 hidden sm:block" />

        {/* User Profile Menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2.5 p-1 rounded-xl hover:bg-slate-50 transition-colors group">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-rose-100 to-pink-100 border border-rose-200/80 text-rose-700 font-bold text-xs flex items-center justify-center shadow-2xs">
                {initials}
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="text-xs font-semibold text-slate-900 leading-tight group-hover:text-rose-600 transition-colors">
                  {displayName}
                </span>
                <span className="text-[10px] text-slate-500 leading-tight">
                  {userRole}
                </span>
              </div>
            </button>
          </DropdownMenuTrigger>

          <DropdownMenuContent align="end" className="w-56 bg-white rounded-2xl shadow-lg border border-slate-100 p-1.5">
            <DropdownMenuLabel className="font-normal px-2 py-2">
              <div className="flex flex-col gap-0.5">
                <p className="text-xs font-semibold text-slate-900">
                  {displayName}
                </p>
                <p className="text-[11px] text-slate-500 truncate">
                  {user?.email}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="my-1 bg-slate-100" />
            <DropdownMenuItem
              onClick={() => navigate("/app/settings/organization")}
              className="text-xs rounded-xl px-2.5 py-2 text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              Account Settings
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={() => navigate("/app/settings/subscription")}
              className="text-xs rounded-xl px-2.5 py-2 text-slate-700 hover:bg-slate-50 cursor-pointer"
            >
              Subscription Plan
            </DropdownMenuItem>
            <DropdownMenuSeparator className="my-1 bg-slate-100" />
            <DropdownMenuItem
              onClick={() => logout()}
              className="text-xs rounded-xl px-2.5 py-2 text-rose-600 hover:bg-rose-50 hover:text-rose-700 cursor-pointer font-medium"
            >
              <LogOut className="mr-2 h-4 w-4" />
              <span>Sign out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}