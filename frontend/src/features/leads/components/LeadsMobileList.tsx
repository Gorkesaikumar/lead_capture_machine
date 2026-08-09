import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { formatDistanceToNow } from "date-fns";
import { ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function LeadsMobileList({ leads }: { leads: any[] }) {
  const navigate = useNavigate();

  return (
    <div className="md:hidden space-y-3">
      {leads.map((lead) => (
        <div 
          key={lead.id}
          onClick={() => navigate(`/leads/${lead.id}`)}
          className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm hover:border-gray-300 transition-colors cursor-pointer active:scale-[0.98]"
        >
          <div className="flex justify-between items-start mb-3">
            <div className="flex flex-col">
              <span className="font-medium text-slate-900">{lead.customer?.display_name || "Unknown"}</span>
              <span className="text-xs text-slate-500 mt-0.5">{lead.customer?.primary_phone || lead.customer?.email}</span>
            </div>
            <StatusBadge status={lead.status.toLowerCase()} />
          </div>
          
          <div className="flex items-center gap-2 mb-3">
            <SourceBadge source={lead.source_channel} />
            <span className="text-sm text-slate-600 truncate">{lead.service?.name || lead.summary || "General Inquiry"}</span>
          </div>
          
          <div className="flex justify-between items-center mt-2 pt-3 border-t border-gray-100">
            <span className="text-xs text-slate-500">{formatDistanceToNow(new Date(lead.created_at), { addSuffix: true })}</span>
            <ChevronRight className="h-4 w-4 text-slate-400" />
          </div>
        </div>
      ))}
    </div>
  );
}