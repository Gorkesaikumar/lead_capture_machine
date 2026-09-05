import { useRef, useEffect, useState } from "react";
import { format } from "date-fns";
import {
  Loader2,
  CheckCheck,
  Check,
  XCircle,
  Clock,
  MessageCircle,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  useLeadConversation,
} from "@/api/conversations.queries";
import { useRealtimeEvent } from "@/contexts/RealtimeContext";
// ─── Types ────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  direction: "INBOUND" | "OUTBOUND";
  text: string;
  message_type: string;
  delivery_status: "PENDING" | "SENT" | "DELIVERED" | "READ" | "FAILED";
  created_at: string;
  provider_timestamp?: string;
}

interface Props {
  leadId: string;
  conversationId?: string;
  customerName?: string;
  /** Ref so parent (QuickActions "Send Message" button) can focus composer */
  composerRef?: React.RefObject<HTMLTextAreaElement | null>;
}

// ─── Delivery Status Icon ────────────────────────────────────────────────────

function DeliveryStatusIcon({ status }: { status: Message["delivery_status"] }) {
  switch (status) {
    case "PENDING":
      return <Clock className="h-3 w-3 text-white/60" />;
    case "SENT":
      return <Check className="h-3 w-3 text-white/70" />;
    case "DELIVERED":
      return <CheckCheck className="h-3 w-3 text-white/80" />;
    case "READ":
      return <CheckCheck className="h-3 w-3 text-blue-200" />;
    case "FAILED":
      return <XCircle className="h-3 w-3 text-red-300" />;
    default:
      return null;
  }
}

// ─── Single Message Bubble ────────────────────────────────────────────────────

function MessageBubble({ message }: { message: Message }) {
  const isInbound = message.direction === "INBOUND";
  const timestamp = format(
    new Date(message.provider_timestamp || message.created_at),
    "MMM d, h:mm a"
  );

  return (
    <div
      className={`flex flex-col gap-1 ${isInbound ? "items-start" : "items-end"}`}
    >
      <div
        className={`max-w-[78%] rounded-2xl px-4 py-2.5 shadow-sm ${
          isInbound
            ? "bg-slate-100 text-slate-800 rounded-bl-sm"
            : "bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-br-sm"
        }`}
      >
        <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
          {message.text || (
            <span className="italic opacity-60">
              [{message.message_type === "IMAGE" ? "Image" : "Attachment"}]
            </span>
          )}
        </p>
      </div>
      <div
        className={`flex items-center gap-1 px-1 ${
          isInbound ? "" : "flex-row-reverse"
        }`}
      >
        <span className="text-[11px] text-slate-400">{timestamp}</span>
        {!isInbound && (
          <DeliveryStatusIcon status={message.delivery_status} />
        )}
      </div>
    </div>
  );
}

import { MessageComposer } from "@/components/common/chat/MessageComposer";

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyConversation() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 py-16 text-slate-400">
      <div className="h-14 w-14 rounded-full bg-slate-100 flex items-center justify-center">
        <MessageSquare className="h-7 w-7 text-slate-300" />
      </div>
      <div className="text-center">
        <p className="text-sm font-medium text-slate-500">No messages yet</p>
        <p className="text-xs text-slate-400 mt-1">
          Messages will appear here once the customer contacts you.
        </p>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export function LeadConversation({
  leadId,
  conversationId: initialConversationId,
  customerName,
  composerRef,
  onOpenBookingLinkDialog,
}: Props & { onOpenBookingLinkDialog: () => void }) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data, isLoading, isFetching, refetch } = useLeadConversation(leadId);

  const messages: Message[] = data?.messages || [];
  const [windowClosed, setWindowClosed] = useState(false);
  const convId = initialConversationId || data?.conversation?.id;

  // Real-time event listener: instantly refetch conversation when message arrives
  useRealtimeEvent("NEW_MESSAGE", (payload) => {
    if (payload.lead_id === leadId || (convId && payload.conversation_id === convId)) {
      refetch();
      if (payload.is_window_open !== undefined) {
        setWindowClosed(!payload.is_window_open);
      }
    }
  }, [leadId, convId, refetch]);

  useRealtimeEvent("MESSAGE_UPDATED", (payload) => {
    if (convId && payload.conversation_id === convId) {
      refetch();
    }
  }, [convId, refetch]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  // Detect messaging window closure from backend flag or last inbound timestamp
  useEffect(() => {
    if (data?.is_window_open !== undefined) {
      setWindowClosed(!data.is_window_open);
      return;
    }
    const msgs = data?.messages || [];
    if (msgs.length === 0) {
      setWindowClosed(false);
      return;
    }
    const lastInbound = [...msgs]
      .reverse()
      .find((m) => m.direction === "INBOUND");
    if (!lastInbound) {
      setWindowClosed(true);
      return;
    }
    const lastInboundTime = new Date(
      lastInbound.provider_timestamp || lastInbound.created_at
    );
    const hoursAgo =
      (Date.now() - lastInboundTime.getTime()) / (1000 * 60 * 60);
    setWindowClosed(hoursAgo >= 24);
  }, [data?.messages, data?.is_window_open]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-100 bg-white">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center">
            <MessageCircle className="h-4 w-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-800">
              {customerName || "Customer"}
            </p>
            <p className="text-xs text-slate-400">Instagram Direct</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isLoading && messages.length > 0 && (
            <Badge
              variant="outline"
              className={`text-xs ${
                windowClosed
                  ? "border-amber-300 text-amber-700 bg-amber-50"
                  : "border-emerald-300 text-emerald-700 bg-emerald-50"
              }`}
            >
              {windowClosed ? "Window Closed" : "● Window Open"}
            </Badge>
          )}
          <Badge variant="outline" className="text-xs text-slate-500">
            {messages.length} message{messages.length !== 1 ? "s" : ""}
          </Badge>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => refetch()}
            disabled={isFetching}
            className="h-7 w-7 text-slate-400 hover:text-slate-700"
            title="Refresh conversation"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? "animate-spin text-blue-600" : ""}`} />
          </Button>
        </div>
      </div>

      {/* Message List */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4 bg-slate-50/40 min-h-[380px] max-h-[480px]"
        id="conversation-messages"
      >
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center py-16">
            <Loader2 className="h-6 w-6 animate-spin text-slate-300" />
          </div>
        ) : messages.length === 0 ? (
          <EmptyConversation />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </>
        )}
      </div>

      {/* Composer */}
      <MessageComposer
        leadId={leadId}
        composerRef={composerRef}
        onInsertBookingLink={onOpenBookingLinkDialog}
        windowClosed={windowClosed}
      />
    </div>
  );
}