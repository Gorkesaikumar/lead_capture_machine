import { useRef, useEffect } from "react";
import { format } from "date-fns";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCheck, Check, Clock, XCircle, MessageSquare } from "lucide-react";
import { apiClient } from "@/api/client";
import { useConversationMessages } from "@/api/conversations.queries";
import { useRealtimeEvent } from "@/contexts/RealtimeContext";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";
import { EmptyState } from "@/components/common/states/EmptyState";
import { InboxComposer } from "./InboxComposer";

interface Props {
  conversationId: string;
}

export function InboxMessageHistory({ conversationId }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const cache = useQueryClient();
  // Fetch conversation metadata (to get lead ID and channel)
  const { data: conv } = useQuery({
    queryKey: ["conversations", "detail", conversationId],
    queryFn: async () => {
      const { data } = await apiClient.get(`/conversations/${conversationId}/`);
      return data;
    },
    enabled: !!conversationId,
    refetchInterval: 15000,
  });

  // Fetch messages
  const { data: messages = [], isLoading, error, refetch, hasNextPage, fetchNextPage, isFetchingNextPage } = useConversationMessages(conversationId);

  // Real-time
  useRealtimeEvent("NEW_MESSAGE", (payload) => {
    if (payload.conversation_id === conversationId) refetch();
  });
  useRealtimeEvent("MESSAGE_UPDATED", (payload) => {
    if (payload.conversation_id === conversationId) refetch();
  });

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length, conversationId]);

  useEffect(() => {
    apiClient.post(`/conversations/${conversationId}/read/`).then(() => cache.invalidateQueries({ queryKey: ["conversations", "inbox"] })).catch(() => {});
  }, [conversationId, messages.length, cache]);
  const windowClosed = !conv?.is_window_open;

  const DeliveryIcon = ({ status }: { status: string }) => {
    switch (status) {
      case "QUEUED":
      case "SENDING":
      case "PENDING": return <Clock className="h-3 w-3 text-white/60" />;
      case "SENT": return <Check className="h-3 w-3 text-white/70" />;
      case "DELIVERED": return <CheckCheck className="h-3 w-3 text-white/80" />;
      case "READ": return <CheckCheck className="h-3 w-3 text-blue-200" />;
      case "FAILED": return <XCircle className="h-3 w-3 text-red-300" />;
      default: return null;
    }
  };

  const isMessagingSupported = conv && (conv.channel === "INSTAGRAM" || conv.channel === "WHATSAPP");

  const visibleMessages = messages;
  const hasMoreMessages = hasNextPage;

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50/50">
      {/* Header */}
      <div className="h-14 border-b border-slate-100 bg-white flex items-center px-6 shrink-0">
        <h3 className="font-medium text-slate-800">
          {conv?.customer?.display_name ? `Conversation with ${conv.customer.display_name}` : "Message History"}
        </h3>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-6 flex flex-col gap-4">
        {isLoading ? (
          <LoadingSkeleton rows={5} />
        ) : error ? (
          <ErrorState 
            code="internal_server_error"
            title="Failed to load messages"
            onRetry={refetch}
          />
        ) : messages.length === 0 ? (
          <EmptyState 
            icon={<MessageSquare className="h-8 w-8" />}
            title="No messages yet"
            description="Start the conversation by sending a message below."
          />
        ) : (
          <>
            {hasMoreMessages && (
              <div className="flex justify-center mb-4">
                <button
                  disabled={isFetchingNextPage}
                  onClick={() => fetchNextPage()}
                  className="text-xs font-medium text-blue-600 bg-blue-50 hover:bg-blue-100 px-4 py-1.5 rounded-full transition-colors"
                >
                  Load older messages
                </button>
              </div>
            )}
            {visibleMessages.map((msg: any) => {
              const isInbound = msg.direction === "INBOUND";
              const ts = format(new Date(msg.provider_timestamp || msg.created_at), "MMM d, h:mm a");
              return (
                <div key={msg.id} className={`flex flex-col gap-1 ${isInbound ? "items-start" : "items-end"}`}>
                  <div className={`max-w-[75%] rounded-2xl px-4 py-2.5 shadow-sm ${
                    isInbound ? "bg-white text-slate-800 rounded-bl-sm border border-slate-100" 
                              : "bg-blue-600 text-white rounded-br-sm"
                  }`}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {msg.text || <span className="italic opacity-60">[{msg.message_type}]</span>}
                    </p>
                  </div>
                  <div className={`flex items-center gap-1 px-1 ${!isInbound ? "flex-row-reverse" : ""}`}>
                    <span className="text-[11px] text-slate-400">{ts}</span>
                    {!isInbound && <><DeliveryIcon status={msg.delivery_status} /><span className="text-[10px] text-slate-500">{msg.delivery_status}</span></>}
                  </div>
                  {msg.error_message && <p className="text-xs text-red-700 max-w-[80%]" role="alert">{msg.error_message}</p>}
                </div>
              );
            })}
          </>
        )}
      </div>

      {/* Composer */}
      {isMessagingSupported ? (
        <InboxComposer key={conversationId}
          conversationId={conversationId}
          channel={conv.channel}
          windowClosed={windowClosed}
        />
      ) : (
        <div className="p-4 bg-white border-t border-slate-100 shrink-0">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center text-sm text-slate-500">
            {!isMessagingSupported ? (
              <>Outbound messaging is not supported for {conv?.channel_display || "this channel"}.</>
            ) : (
              <>This conversation is not linked to a lead, so replies cannot be sent.</>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
