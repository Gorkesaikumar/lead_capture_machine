import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { formatDistanceToNow, format } from "date-fns";
import { useNavigate } from "react-router-dom";

export function CustomerHistoryPane({ history }: { history: any }) {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col gap-6">
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-slate-50 flex justify-between items-center">
          <h3 className="font-semibold text-slate-900">Recent Leads</h3>
          <span className="bg-blue-100 text-blue-700 text-xs font-bold px-2 py-0.5 rounded-full">
            {history.leads?.total_leads || 0}
          </span>
        </div>
        <div className="divide-y divide-gray-100">
          {history.leads?.recent_leads?.length > 0 ? (
            history.leads.recent_leads.map((lead: any) => (
              <div 
                key={lead.id} 
                className="p-4 hover:bg-slate-50 cursor-pointer transition-colors flex justify-between items-center"
                onClick={() => navigate(`/leads/${lead.id}`)}
              >
                <div>
                  <StatusBadge status={lead.status.toLowerCase()} />
                  <p className="text-sm text-slate-600 mt-2">{lead.service_requested || "General Inquiry"}</p>
                </div>
                <div className="text-right text-xs text-slate-500">
                  {lead.created_at ? format(new Date(lead.created_at), "MMM d, yyyy") : ""}
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-slate-500 text-sm">No leads found.</div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-slate-50 flex justify-between items-center">
          <h3 className="font-semibold text-slate-900">Recent Bookings</h3>
          <span className="bg-green-100 text-green-700 text-xs font-bold px-2 py-0.5 rounded-full">
            {history.bookings?.total_bookings || 0}
          </span>
        </div>
        <div className="divide-y divide-gray-100">
          {history.bookings?.recent_bookings?.length > 0 ? (
            history.bookings.recent_bookings.map((booking: any) => (
              <div key={booking.id} className="p-4 flex justify-between items-center">
                <div>
                  <StatusBadge status={booking.status.toLowerCase()} />
                  <p className="text-sm text-slate-600 mt-2 font-medium">
                    {booking.start_time ? format(new Date(booking.start_time), "MMMM d, h:mm a") : "Unscheduled"}
                  </p>
                </div>
                <div className="text-right text-xs text-slate-500">
                  Booked {booking.created_at ? formatDistanceToNow(new Date(booking.created_at), { addSuffix: true }) : ""}
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-slate-500 text-sm">No bookings found.</div>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-slate-50 flex justify-between items-center">
          <h3 className="font-semibold text-slate-900">Recent Conversations</h3>
          <span className="bg-purple-100 text-purple-700 text-xs font-bold px-2 py-0.5 rounded-full">
            {history.conversations?.total_conversations || 0}
          </span>
        </div>
        <div className="divide-y divide-gray-100">
          {history.conversations?.recent_conversations?.length > 0 ? (
            history.conversations.recent_conversations.map((conv: any) => (
              <div key={conv.id} className="p-4 flex justify-between items-center">
                <div>
                  <SourceBadge source={conv.channel} />
                </div>
                <div className="text-right text-xs text-slate-500">
                  Last msg {conv.last_message_at ? formatDistanceToNow(new Date(conv.last_message_at), { addSuffix: true }) : ""}
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-slate-500 text-sm">No conversations found.</div>
          )}
        </div>
      </div>
    </div>
  );
}