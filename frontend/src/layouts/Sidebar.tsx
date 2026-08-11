import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  UserSquare2,
  Calendar,
  BookOpen,
  Clock,
  Camera,
  Zap,
  Webhook,
  LineChart,
} from "lucide-react";
import { cn } from "@/utils/cn";

const navGroups = [
  {
    title: "Overview",
    items: [
      { name: "Overview", to: "/", icon: LayoutDashboard },
    ]
  },
  {
    title: "CRM",
    items: [
      { name: "Leads", to: "/leads", icon: Users },
      { name: "Conversations", to: "/conversations", icon: MessageSquare },
      { name: "Customers", to: "/customers", icon: UserSquare2 },
    ]
  },
  {
    title: "Bookings",
    items: [
      { name: "Calendar", to: "/calendar", icon: Calendar },
      { name: "All Bookings", to: "/bookings", icon: BookOpen },
      { name: "Availability", to: "/availability", icon: Clock },
    ]
  },
  {
    title: "Studio",
    items: [
      { name: "Services & Packages", to: "/services", icon: Camera },
    ]
  },
  {
    title: "Automation",
    items: [
      { name: "Lead Triggers", to: "/triggers", icon: Zap },
      { name: "Integrations", to: "/integrations", icon: Webhook },
    ]
  },
  {
    title: "Insights",
    items: [
      { name: "Analytics", to: "/analytics", icon: LineChart },
      { name: "Design Showcase", to: "/design-system", icon: Zap },
    ]
  }
];

export default function Sidebar({ className }: { className?: string }) {
  return (
    <div className={cn("flex flex-col h-full bg-white border-r border-gray-200 w-64 shrink-0", className)}>
      <div className="flex h-14 items-center border-b border-gray-100 px-6 shrink-0">
        <span className="font-semibold text-lg tracking-tight text-slate-900">Studio Admin</span>
      </div>
      <div className="flex-1 overflow-y-auto py-6 px-4 space-y-6">
        {navGroups.map((group) => (
          <div key={group.title}>
            <h4 className="mb-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              {group.title}
            </h4>
            <nav className="grid gap-1">
              {group.items.map((item) => (
                <NavLink
                  key={item.name}
                  to={item.to}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all",
                      isActive
                        ? "bg-slate-900 text-white shadow-sm"
                        : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    )
                  }
                >
                  <item.icon className={cn("h-4 w-4", "opacity-80")} />
                  {item.name}
                </NavLink>
              ))}
            </nav>
          </div>
        ))}
      </div>
    </div>
  );
}






