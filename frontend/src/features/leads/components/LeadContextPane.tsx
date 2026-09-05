import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { formatDistanceToNow } from "date-fns";
import { Mail, Phone, UserCircle, User } from "lucide-react";

interface Props {
  lead: any;
}

export function LeadContextPane({ lead }: Props) {
  const customer = lead.customer;
  const initials = customer?.display_name
    ? customer.display_name.substring(0, 2).toUpperCase()
    : "CU";

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Customer Detail Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-xs font-semibold text-slate-400 mb-4 uppercase tracking-wider">
          Contact Information
        </h3>

        <div className="flex items-center gap-3 mb-5">
          <Avatar className="h-12 w-12 border-2 border-slate-100">
            <AvatarFallback className="bg-gradient-to-br from-slate-100 to-slate-200 text-slate-600 font-semibold text-sm">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              {customer?.display_name || "Unknown Customer"}
            </h2>
            <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
              <UserCircle className="h-3 w-3" />
              Customer
            </p>
          </div>
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Phone className="h-4 w-4 text-slate-400 shrink-0" />
            <span className="truncate">
              {customer?.primary_phone || (
                <span className="text-slate-400 italic">No phone</span>
              )}
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Mail className="h-4 w-4 text-slate-400 shrink-0" />
            <span className="truncate">
              {customer?.email || (
                <span className="text-slate-400 italic">No email</span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* Lead Context Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-xs font-semibold text-slate-400 mb-4 uppercase tracking-wider">
          Lead Information
        </h3>
        <div className="space-y-3">
          <div className="flex justify-between items-center pb-3 border-b border-slate-100">
            <span className="text-xs text-slate-500">Status</span>
            <StatusBadge status={lead.status} />
          </div>
          <div className="flex justify-between items-center pb-3 border-b border-slate-100">
            <span className="text-xs text-slate-500">Channel</span>
            <SourceBadge source={lead.source_channel} />
          </div>
          <div className="flex justify-between items-center pb-3 border-b border-slate-100">
            <span className="text-xs text-slate-500">Assigned To</span>
            <div className="flex items-center gap-1.5 text-slate-700 font-medium text-xs">
              <User className="h-3.5 w-3.5 text-slate-400" />
              {lead.assigned_staff?.full_name || "Unassigned"}
            </div>
          </div>
          <div className="flex justify-between items-start pb-3 border-b border-slate-100">
            <span className="text-xs text-slate-500 mt-0.5">Requirement</span>
            <span className="text-xs font-medium text-slate-700 text-right max-w-[140px]">
              {lead.trigger_service_name ||
                lead.trigger_phrase ||
                lead.service?.name ||
                "General Inquiry"}
            </span>
          </div>
          <div className="flex justify-between items-center pb-3 border-slate-100">
            <span className="text-xs text-slate-500">Received</span>
            <span className="text-xs font-medium text-slate-700">
              {formatDistanceToNow(new Date(lead.created_at), {
                addSuffix: true,
              })}
            </span>
          </div>
          {lead.tags && lead.tags.length > 0 && (
            <div className="flex flex-col gap-2 pt-3 border-t border-slate-100">
              <span className="text-xs text-slate-500">Tags</span>
              <div className="flex flex-wrap gap-1.5">
                {lead.tags.map((tag: string) => (
                  <span
                    key={tag}
                    className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
