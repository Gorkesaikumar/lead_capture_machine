import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { Mail, Phone, Calendar, AtSign } from "lucide-react";
import { format } from "date-fns";

export function CustomerProfilePane({ customer }: { customer: any }) {
  const initials = customer?.display_name ? customer.display_name.substring(0, 2).toUpperCase() : "CU";

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <div className="flex items-center gap-4 mb-6">
          <Avatar className="h-16 w-16 border border-slate-100 shadow-sm">
            <AvatarFallback className="bg-slate-100 text-slate-600 text-lg font-semibold">{initials}</AvatarFallback>
          </Avatar>
          <div>
            <h2 className="text-xl font-bold text-slate-900">{customer?.display_name || "Unknown"}</h2>
            <div className="flex gap-2 mt-2">
              {customer?.identities?.map((id: any) => (
                <SourceBadge key={id.id} source={id.channel} />
              ))}
            </div>
          </div>
        </div>

        <div className="space-y-4">
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Phone className="h-4 w-4 text-slate-400" />
            {customer?.primary_phone || "No phone provided"}
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Mail className="h-4 w-4 text-slate-400" />
            {customer?.email || "No email provided"}
          </div>
          <div className="flex items-center gap-3 text-sm text-slate-600">
            <Calendar className="h-4 w-4 text-slate-400" />
            First seen {customer?.first_seen_at ? format(new Date(customer.first_seen_at), "MMM d, yyyy") : "Unknown"}
          </div>
        </div>
      </div>

      {customer?.identities?.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 uppercase tracking-wider">Known Identities</h3>
          <div className="space-y-4">
            {customer.identities.map((id: any) => (
              <div key={id.id} className="flex justify-between items-center pb-3 border-b border-gray-100 last:border-0 last:pb-0">
                <div className="flex items-center gap-2">
                  <SourceBadge source={id.channel} />
                </div>
                <div className="flex items-center gap-1 text-sm text-slate-700 font-medium">
                  <AtSign className="h-3 w-3 text-slate-400" />
                  {id.username || id.external_user_id}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {customer?.notes && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 mb-3 uppercase tracking-wider">Internal Notes</h3>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{customer.notes}</p>
        </div>
      )}
    </div>
  );
}