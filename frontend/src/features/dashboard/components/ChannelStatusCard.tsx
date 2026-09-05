import { Link } from "react-router-dom";
import { MessageSquare, Globe, ArrowUpRight } from "lucide-react";
import { cn } from "@/utils/cn";

export interface ChannelStatusItem {
  id: string;
  name: string;
  type: "instagram" | "whatsapp" | "website";
  status: string;
  leadCount: number;
}

interface ChannelStatusCardProps {
  channels?: ChannelStatusItem[];
}

export function ChannelStatusCard({ channels = [] }: ChannelStatusCardProps) {
  const safeChannels = channels || [];

  return (
    <div className="rounded-2xl bg-white p-5 border border-slate-200/80 shadow-2xs flex flex-col justify-between h-full">
      {/* Card Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-slate-900">Channel Status</h3>
        <Link
          to="/app/settings/channels"
          className="inline-flex items-center gap-1 text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50/70 hover:bg-rose-100/70 px-2.5 py-1 rounded-lg transition-colors"
        >
          View All
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {/* Channel List */}
      <div className="space-y-3.5 flex-1 flex flex-col justify-around">
        {safeChannels.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">No channels configured.</p>
        ) : (
          safeChannels.map((channel) => (
            <div
              key={channel.id}
              className="flex items-center justify-between p-3 rounded-xl bg-slate-50/60 border border-slate-100 hover:border-slate-200 transition-colors"
            >
              <div className="flex items-center gap-3">
                {/* Channel Icon */}
                <div
                  className={cn(
                    "p-2.5 rounded-xl text-white shadow-2xs shrink-0 flex items-center justify-center",
                    channel.type === "instagram" &&
                      "bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600",
                    channel.type === "whatsapp" && "bg-emerald-500",
                    channel.type === "website" && "bg-amber-500"
                  )}
                >
                  {channel.type === "website" ? (
                    <Globe className="h-4 w-4" />
                  ) : (
                    <MessageSquare className="h-4 w-4" />
                  )}
                </div>

                {/* Name & Status */}
                <div>
                  <h4 className="text-xs font-bold text-slate-900">
                    {channel.name}
                  </h4>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span
                      className={cn(
                        "h-1.5 w-1.5 rounded-full",
                        channel.status === "CONNECTED" || channel.status === "ACTIVE"
                          ? "bg-emerald-500 animate-pulse"
                          : "bg-slate-300"
                      )}
                    />
                    <span className="text-[11px] font-medium text-slate-500">
                      {(channel.status || "UNKNOWN").toLowerCase().replaceAll("_", " ")}
                    </span>
                  </div>
                </div>
              </div>

              {/* Lead Count Badge */}
              <div
                className={cn(
                  "px-3 py-1 rounded-xl text-right shrink-0",
                  channel.type === "website"
                    ? "bg-amber-50 text-amber-700 border border-amber-100"
                    : "bg-emerald-50 text-emerald-700 border border-emerald-100"
                )}
              >
                <span className="text-xs font-extrabold block leading-tight">
                  {channel.leadCount ?? 0}
                </span>
                <span className="text-[10px] font-semibold text-slate-400 block leading-tight">
                  Leads
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
