import { useState, useRef, useCallback } from "react";
import { toast } from "sonner";
import { Send, Loader2, MessageSquare, ChevronDown, MessageCircle, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useSendLeadMessage } from "@/api/conversations.queries";
import { MESSAGE_TEMPLATES } from "@/features/leads/constants/messageTemplates";

// ─── Templates Popover ───────────────────────────────────────────────────────

function TemplatesPopover({ onSelect }: { onSelect: (text: string) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="h-8 gap-1.5 text-slate-600 border-slate-200 text-xs">
          <MessageSquare className="h-3.5 w-3.5" />
          Templates
          <ChevronDown className="h-3 w-3 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-72 p-2" align="start">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide px-2 py-1 mb-1">
          Message Templates
        </p>
        <div className="flex flex-col gap-0.5">
          {MESSAGE_TEMPLATES.map((tpl) => (
            <button
              key={tpl.id}
              onClick={() => {
                onSelect(tpl.text);
                setOpen(false);
              }}
              className="w-full text-left rounded-md px-3 py-2.5 hover:bg-slate-50 transition-colors group"
            >
              <p className="text-sm font-medium text-slate-800 group-hover:text-blue-700">{tpl.name}</p>
              <p className="text-xs text-slate-500 mt-0.5 line-clamp-2">{tpl.description}</p>
            </button>
          ))}
        </div>
      </PopoverContent>
    </Popover>
  );
}

// ─── Messaging Window Warning ─────────────────────────────────────────────────

export function MessagingWindowWarning() {
  return (
    <Alert className="border-amber-200 bg-amber-50 rounded-none border-x-0">
      <AlertTriangle className="h-4 w-4 text-amber-600" />
      <AlertDescription className="text-amber-800 text-sm">
        <span className="font-semibold">Messaging window closed.</span> The channel’s 24-hour policy requires the customer to send a message first before you can reply. Wait for their next message.
      </AlertDescription>
    </Alert>
  );
}

// ─── Message Composer ─────────────────────────────────────────────────────────

interface ComposerProps {
  leadId: string;
  composerRef?: React.RefObject<HTMLTextAreaElement | null>;
  onInsertBookingLink?: () => void;
  windowClosed: boolean;
}

export function MessageComposer({
  leadId,
  composerRef,
  onInsertBookingLink,
  windowClosed,
}: ComposerProps) {
  const [text, setText] = useState("");
  const localRef = useRef<HTMLTextAreaElement>(null);
  const textareaRef = (composerRef || localRef) as React.RefObject<HTMLTextAreaElement>;

  const sendMessage = useSendLeadMessage(leadId);

  const handleSend = useCallback(async () => {
    const trimmed = text.trim();
    if (!trimmed || sendMessage.isPending) return;

    try {
      await sendMessage.mutateAsync({ message: trimmed });
      setText("");
      toast.success("Meta accepted the message", { description: "Delivery status is shown in the conversation." });
    } catch (err: any) {
      const errorCode = err?.response?.data?.error_code;
      const errorMsg = err?.response?.data?.message;

      if (errorCode === "messaging_window_closed") {
        toast.warning("Messaging window closed", {
          description: "The customer must send a message first. Your text has been preserved.",
          duration: 6000,
        });
      } else {
        toast.error("Failed to send message", {
          description: errorMsg || "Please try again.",
        });
      }
    }
  }, [text, sendMessage]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t border-slate-100 bg-white">
      {windowClosed && <MessagingWindowWarning />}
      <div className="p-3 flex flex-col gap-2">
        <Textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={windowClosed ? "Messaging window closed — wait for customer reply..." : "Type a message... (Ctrl+Enter to send)"}
          rows={3}
          disabled={windowClosed || sendMessage.isPending}
          className="resize-none text-sm border-slate-200 focus-visible:ring-blue-500 placeholder:text-slate-400"
        />
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <TemplatesPopover onSelect={setText} />
            {onInsertBookingLink && (
              <Button variant="outline" size="sm" onClick={onInsertBookingLink} className="h-8 gap-1.5 text-slate-600 border-slate-200 text-xs">
                <MessageCircle className="h-3.5 w-3.5" />
                Send Booking Link
              </Button>
            )}
          </div>
          <Button onClick={handleSend} disabled={!text.trim() || sendMessage.isPending || windowClosed} size="sm" className="h-8 gap-1.5 bg-blue-600 hover:bg-blue-700 text-white px-4">
            {sendMessage.isPending ? (
              <><Loader2 className="h-3.5 w-3.5 animate-spin" /> Sending…</>
            ) : (
              <><Send className="h-3.5 w-3.5" /> Send</>
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
