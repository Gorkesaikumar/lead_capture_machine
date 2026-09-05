import { formatDistanceToNow, format } from "date-fns";
import { MessageSquare, RefreshCw, UserCheck, AlertTriangle, Play, CheckCircle } from "lucide-react";

interface LeadActivity {
  id: string;
  activity_type: string;
  activity_type_display: string;
  actor_email?: string;
  description: string;
  created_at: string;
}

interface Props {
  activities: LeadActivity[];
}

export function LeadActivityLog({ activities }: Props) {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case "STATUS_CHANGE":
        return <RefreshCw className="h-4 w-4 text-blue-500" />;
      case "ASSIGNED":
        return <UserCheck className="h-4 w-4 text-green-500" />;
      case "MESSAGE_RECEIVED":
      case "MESSAGE_SENT":
        return <MessageSquare className="h-4 w-4 text-purple-500" />;
      case "CREATED":
        return <Play className="h-4 w-4 text-emerald-500" />;
      case "QUALIFIED":
        return <CheckCircle className="h-4 w-4 text-amber-500" />;
      default:
        return <AlertTriangle className="h-4 w-4 text-slate-400" />;
    }
  };

  if (!activities || activities.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-500 shadow-sm mt-6">
        No activity recorded for this lead yet.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm mt-6 overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
        <h3 className="text-sm font-semibold text-slate-800">Activity & Notes</h3>
      </div>
      <div className="p-5">
        <div className="relative border-l border-slate-200 ml-3 space-y-6 pb-4">
          {activities.map((activity) => (
            <div key={activity.id} className="relative pl-6">
              <div className="absolute -left-3.5 top-0 bg-white p-1 rounded-full border border-slate-200 shadow-sm">
                {getActivityIcon(activity.activity_type)}
              </div>
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-slate-900">
                    {activity.activity_type_display}
                  </p>
                  <p className="text-sm text-slate-600 mt-1 leading-relaxed">
                    {activity.description}
                  </p>
                  {activity.actor_email && (
                    <p className="text-xs text-slate-400 mt-2 flex items-center gap-1">
                      by {activity.actor_email}
                    </p>
                  )}
                </div>
                <div className="text-xs text-slate-400 whitespace-nowrap text-left sm:text-right">
                  <div>{formatDistanceToNow(new Date(activity.created_at), { addSuffix: true })}</div>
                  <div className="mt-0.5">{format(new Date(activity.created_at), "MMM d, h:mm a")}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
