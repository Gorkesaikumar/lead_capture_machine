import { formatDistanceToNow, parseISO } from "date-fns";
import { Link } from "react-router-dom";
import { MessageSquare, Globe, UserPlus, ArrowUpRight } from "lucide-react";
import { cn } from "@/utils/cn";

export interface ActivityItem {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  created_at: string;
  lead_id: string;
}

interface ActivityFeedCardProps {
  activities?: ActivityItem[];
}

export function ActivityFeedCard({ activities = [] }: ActivityFeedCardProps) {
  const safeActivities = Array.isArray(activities) ? activities : [];

  const formatActivityTime = (dateStr?: string) => {
    if (!dateStr) return "Just now";
    try {
      return formatDistanceToNow(parseISO(dateStr), { addSuffix: true });
    } catch {
      return "Just now";
    }
  };

  return (
    <div className="rounded-2xl bg-white p-5 border border-slate-200/80 shadow-2xs flex flex-col justify-between h-full">
      {/* Card Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-slate-900">Activity Feed</h3>
        <Link
          to="/app/leads"
          className="inline-flex items-center gap-1 text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50/70 hover:bg-rose-100/70 px-2.5 py-1 rounded-lg transition-colors"
        >
          View All
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {/* Activity Items */}
      <div className="space-y-3 flex-1 flex flex-col justify-around">
        {safeActivities.length === 0 && <p className="text-sm text-slate-500 py-6">No recorded lead activity in this period.</p>}
        {safeActivities.map((item) => (
          <div
            key={item.id}
            className="flex items-start justify-between p-2.5 rounded-xl hover:bg-slate-50/80 transition-colors border border-transparent hover:border-slate-100"
          >
            <div className="flex items-center gap-3">
              {/* Type Icon */}
              <div
                className={cn(
                  "p-2 rounded-xl text-white shadow-2xs shrink-0 flex items-center justify-center mt-0.5",
                  item.type === "whatsapp" && "bg-emerald-500",
                  item.type === "instagram" &&
                    "bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600",
                  item.type === "website" && "bg-amber-500",
                  item.type === "team" && "bg-indigo-500"
                )}
              >
                {item.type === "website" ? (
                  <Globe className="h-3.5 w-3.5" />
                ) : item.type === "team" ? (
                  <UserPlus className="h-3.5 w-3.5" />
                ) : (
                  <MessageSquare className="h-3.5 w-3.5" />
                )}
              </div>

              {/* Title & Subtitle */}
              <div>
                <h4 className="text-xs font-bold text-slate-900 leading-tight">
                  <Link to={`/app/leads/${item.lead_id}`}>{item.title}</Link>
                </h4>
                <p className="text-[11px] font-medium text-slate-500 leading-tight mt-0.5">
                  {item.subtitle}
                </p>
              </div>
            </div>

            {/* Time Ago */}
            <span className="text-[11px] font-semibold text-slate-400 shrink-0 mt-0.5">
              {formatActivityTime(item.created_at)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
