import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { apiClient } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Loader2, User, Phone, Mail, Hash, ShieldAlert, ExternalLink, Activity } from "lucide-react";
import { format } from "date-fns";
import { useUpdateConversationStatus } from "@/api/conversations.queries";

interface Props {
  conversationId: string;
}

export function InboxLeadPanel({ conversationId }: Props) {
  const { data: conv, isLoading } = useQuery({
    queryKey: ["conversations", "detail", conversationId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/conversations/${conversationId}/`);
      return data;
    },
    enabled: !!conversationId,
  });

  const { mutate: updateStatus, isPending } = useUpdateConversationStatus(conversationId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
      </div>
    );
  }

  if (!conv) return null;

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Header */}
      <div className="p-6 border-b border-slate-200 bg-white">
        <div className="flex items-center gap-4 mb-4">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 font-semibold text-lg border border-slate-200 shadow-sm">
            {conv.customer?.display_name?.charAt(0) || <User />}
          </div>
          <div>
            <h2 className="font-semibold text-slate-900 text-lg">
              {conv.customer?.display_name || "Unknown Customer"}
            </h2>
            <p className="text-sm text-slate-500">via {conv.channel_display || conv.channel}</p>
          </div>
        </div>

        <div className="flex flex-col gap-2.5">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Phone className="h-4 w-4 text-slate-400" />
            <span>{conv.customer?.primary_phone || "No phone"}</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Mail className="h-4 w-4 text-slate-400" />
            <span className="truncate">{conv.customer?.email || "No email"}</span>
          </div>
        </div>
      </div>

      {/* Conversation Status */}
      <div className="p-6 border-b border-slate-200 flex flex-col gap-3 bg-white">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5" />
          Conversation Status
        </h3>
        <div className="flex gap-2">
          {["ACTIVE", "ARCHIVED", "CLOSED"].map((s) => (
            <Button
              key={s}
              size="sm"
              variant={conv.status === s ? "default" : "outline"}
              className={`flex-1 text-xs ${conv.status === s ? "bg-slate-800 text-white hover:bg-slate-700" : "text-slate-600 border-slate-200"}`}
              onClick={() => updateStatus({ status: s })}
              disabled={isPending || conv.status === s}
            >
              {s.charAt(0) + s.slice(1).toLowerCase()}
            </Button>
          ))}
        </div>
      </div>

      {/* Lead Details */}
      {conv.lead ? (
        <div className="p-6 flex flex-col gap-5 bg-white">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <ShieldAlert className="h-3.5 w-3.5" />
              Lead Details
            </h3>
            <Badge variant="secondary" className="bg-blue-50 text-blue-700 hover:bg-blue-50">
              {conv.lead.status_display || conv.lead.status}
            </Badge>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-500">Assigned To</span>
              <span className="font-medium text-slate-900">
                {conv.lead.assigned_staff_name || (conv.assigned_user ? (conv.assigned_user.full_name || conv.assigned_user.email) : "Unassigned")}
              </span>
            </div>
            {conv.lead.source_channel && (
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-500">Source</span>
                <span className="font-medium text-slate-900">{conv.lead.source_channel}</span>
              </div>
            )}
          </div>
          
          {conv.lead.tags && conv.lead.tags.length > 0 && (
            <div className="flex flex-col gap-2">
              <span className="text-xs text-slate-500">Tags</span>
              <div className="flex flex-wrap gap-1.5">
                {conv.lead.tags.map((tag: string) => (
                  <Badge key={tag} variant="outline" className="bg-white border-slate-200 text-slate-600">
                    <Hash className="h-3 w-3 mr-1 text-slate-400" />
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          <div className="mt-2 pt-4 border-t border-slate-100 flex flex-col gap-2">
            <Button asChild variant="outline" className="w-full justify-center gap-2 border-slate-200 text-slate-700">
              <Link to={`/app/leads/${conv.lead.id}`}>
                View Full Lead
                <ExternalLink className="h-4 w-4 text-slate-400" />
              </Link>
            </Button>
          </div>
        </div>
      ) : (
        <div className="p-6 flex flex-col items-center justify-center text-center py-12">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center mb-3">
            <ShieldAlert className="h-6 w-6 text-slate-300" />
          </div>
          <p className="text-sm font-medium text-slate-600">No Lead Attached</p>
          <p className="text-xs text-slate-400 mt-1">
            This conversation is not associated with an active lead.
          </p>
        </div>
      )}

      {/* Meta Info */}
      <div className="p-6 mt-auto border-t border-slate-200 text-xs text-slate-400 flex flex-col gap-1.5 bg-slate-50">
        <div className="flex justify-between items-center">
          <span>Started</span>
          <span className="text-slate-600">{format(new Date(conv.created_at), "MMM d, yyyy")}</span>
        </div>
        {conv.last_message_at && (
          <div className="flex justify-between items-center">
            <span>Last message</span>
            <span className="text-slate-600">{format(new Date(conv.last_message_at), "MMM d, h:mm a")}</span>
          </div>
        )}
      </div>
    </div>
  );
}
