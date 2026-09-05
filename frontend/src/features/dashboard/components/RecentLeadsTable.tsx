import { useNavigate, Link } from "react-router-dom";
import { formatDistanceToNow, parseISO, isValid } from "date-fns";
import { MoreHorizontal, ArrowUpRight } from "lucide-react";
import { cn } from "@/utils/cn";

interface Lead {
  id: string;
  name: string;
  source: string;
  status: string;
  assigned_to_name?: string;
  created_at: string;
  email?: string;
  notes?: string;
}

const SAMPLE_LEADS: Lead[] = [
  {
    id: "lead-1",
    name: "Sarah Jenkins",
    source: "Instagram",
    status: "New",
    notes: "Interested in pricing",
    created_at: new Date(Date.now() - 2 * 60 * 1000).toISOString(),
  },
  {
    id: "lead-2",
    name: "Rohan Mehta",
    source: "WhatsApp",
    status: "Contacted",
    notes: "Looking for demo",
    created_at: new Date(Date.now() - 15 * 60 * 1000).toISOString(),
  },
  {
    id: "lead-3",
    name: "Priya Kapoor",
    source: "Website",
    status: "Qualified",
    notes: "Contact form submission",
    created_at: new Date(Date.now() - 32 * 60 * 1000).toISOString(),
  },
];

export function RecentLeadsTable({ leads }: { leads: Lead[] }) {
  const navigate = useNavigate();
  const displayLeads = leads && leads.length > 0 ? leads.slice(0, 5) : SAMPLE_LEADS;

  const getInitials = (name: string) => {
    if (!name) return "L";
    const parts = name.trim().split(" ");
    return parts.length >= 2
      ? `${parts[0][0]}${parts[1][0]}`.toUpperCase()
      : name.slice(0, 2).toUpperCase();
  };

  const getAvatarColor = (idx: number) => {
    const colors = [
      "bg-rose-100 text-rose-700 border-rose-200",
      "bg-purple-100 text-purple-700 border-purple-200",
      "bg-emerald-100 text-emerald-700 border-emerald-200",
      "bg-blue-100 text-blue-700 border-blue-200",
      "bg-amber-100 text-amber-700 border-amber-200",
    ];
    return colors[idx % colors.length];
  };

  const getSourceBadge = (source: string) => {
    const src = (source || "").toLowerCase();
    if (src.includes("insta")) {
      return (
        <span className="bg-rose-100/90 text-rose-600 border border-rose-200/60 font-semibold px-2.5 py-0.5 rounded-full text-[11px]">
          Instagram
        </span>
      );
    }
    if (src.includes("whats")) {
      return (
        <span className="bg-emerald-100/90 text-emerald-700 border border-emerald-200/60 font-semibold px-2.5 py-0.5 rounded-full text-[11px]">
          WhatsApp
        </span>
      );
    }
    return (
      <span className="bg-amber-100/90 text-amber-700 border border-amber-200/60 font-semibold px-2.5 py-0.5 rounded-full text-[11px]">
        Website
      </span>
    );
  };

  const formatTime = (dateStr: string) => {
    try {
      const parsed = parseISO(dateStr);
      if (isValid(parsed)) {
        return formatDistanceToNow(parsed, { addSuffix: true })
          .replace("about ", "")
          .replace(" ago", " ago");
      }
    } catch {
      // ignore
    }
    return "just now";
  };

  return (
    <div className="rounded-2xl bg-white p-5 border border-slate-200/80 shadow-2xs flex flex-col justify-between h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-base font-bold text-slate-900">Recent Leads</h3>
        <Link
          to="/app/leads"
          className="inline-flex items-center gap-1 text-xs font-bold text-rose-600 hover:text-rose-700 bg-rose-50/70 hover:bg-rose-100/70 px-2.5 py-1 rounded-lg transition-colors"
        >
          View All
          <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>

      {/* Leads List */}
      <div className="space-y-3 flex-1 flex flex-col justify-around">
        {displayLeads.map((lead, idx) => (
          <div
            key={lead.id}
            onClick={() => navigate(`/app/leads/${lead.id}`)}
            className="group flex items-center justify-between p-2.5 rounded-xl hover:bg-slate-50/80 transition-colors border border-transparent hover:border-slate-100 cursor-pointer"
          >
            {/* Avatar & Lead Details */}
            <div className="flex items-center gap-3 min-w-0">
              <div
                className={cn(
                  "h-9 w-9 rounded-full border font-bold text-xs flex items-center justify-center shrink-0 shadow-2xs",
                  getAvatarColor(idx)
                )}
              >
                {getInitials(lead.name)}
              </div>

              <div className="min-w-0">
                <h4 className="text-xs font-bold text-slate-900 group-hover:text-rose-600 transition-colors truncate">
                  {lead.name}
                </h4>
                <p className="text-[11px] font-medium text-slate-500 truncate max-w-[160px] sm:max-w-[200px]">
                  {lead.notes || lead.email || "New lead inquiry"}
                </p>
              </div>
            </div>

            {/* Source, Time & Action */}
            <div className="flex items-center gap-3 shrink-0">
              {getSourceBadge(lead.source)}

              <span className="text-[11px] font-semibold text-slate-400 hidden sm:inline">
                {formatTime(lead.created_at)}
              </span>

              <button
                onClick={(e) => {
                  e.stopPropagation();
                  navigate(`/app/leads/${lead.id}`);
                }}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors"
                title="More Options"
              >
                <MoreHorizontal className="h-4 w-4" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
