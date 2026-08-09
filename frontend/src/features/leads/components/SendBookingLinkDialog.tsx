import { useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { useSendLeadBookingLink } from "@/api/conversations.queries";
import { BOOKING_LINK_TEMPLATE } from "../constants/messageTemplates";
import {
  Loader2,
  MessageCircle,
  ExternalLink,
  Copy,
  CheckCircle2,
} from "lucide-react";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  leadId: string;
  defaultServiceId?: string;
  customerName?: string;
}

export function SendBookingLinkDialog({
  open,
  onOpenChange,
  leadId,
  defaultServiceId,
  customerName,
}: Props) {
  const [message, setMessage] = useState(BOOKING_LINK_TEMPLATE);
  const [sent, setSent] = useState(false);
  const [sentBookingUrl, setSentBookingUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const sendBookingLink = useSendLeadBookingLink(leadId);

  const handleSendViaInstagram = async () => {
    try {
      const result = await sendBookingLink.mutateAsync({
        message,
        service_id: defaultServiceId,
      });
      setSent(true);
      setSentBookingUrl(result.booking_url);
      toast.success("Booking link sent via Instagram DM! 🎉", {
        description: `${customerName || "The customer"} will receive the link in their DMs.`,
      });
    } catch (err: any) {
      const errorCode = err?.response?.data?.error_code;
      const errorMsg = err?.response?.data?.message;

      if (errorCode === "messaging_window_closed") {
        toast.warning("Messaging window closed", {
          description:
            "The customer must send a message first. Use 'Copy Link' to share it manually.",
          duration: 7000,
        });
      } else if (errorCode === "no_instagram_identity") {
        toast.error("No Instagram identity found", {
          description:
            "This customer's Instagram ID is not recorded. Cannot send DM.",
        });
      } else {
        toast.error("Failed to send booking link", {
          description: errorMsg || "Please try again or copy the link manually.",
        });
      }
    }
  };

  const handleCopyLink = async () => {
    if (!sentBookingUrl) return;
    await navigator.clipboard.writeText(sentBookingUrl);
    setCopied(true);
    toast.success("Booking URL copied to clipboard!");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleClose = () => {
    onOpenChange(false);
    // Reset state after dialog closes
    setTimeout(() => {
      setSent(false);
      setSentBookingUrl(null);
      setCopied(false);
      setMessage(BOOKING_LINK_TEMPLATE);
    }, 300);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[540px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-full bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center">
              <MessageCircle className="h-3.5 w-3.5 text-white" />
            </div>
            Send Booking Link via Instagram
          </DialogTitle>
          <DialogDescription>
            A secure booking link will be generated and sent to{" "}
            <span className="font-medium text-slate-700">
              {customerName || "the customer"}
            </span>{" "}
            via Instagram DM. Edit the message before sending.
          </DialogDescription>
        </DialogHeader>

        {!sent ? (
          <>
            {/* Message Editor */}
            <div className="mt-2">
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-slate-600 uppercase tracking-wide">
                  Message Preview
                </label>
                <Badge variant="outline" className="text-xs text-slate-500">
                  {"{BOOKING_URL}"} will be replaced with the real link
                </Badge>
              </div>
              <Textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={7}
                className="text-sm resize-none border-slate-200 focus-visible:ring-blue-500 font-mono"
                id="booking-link-message-editor"
              />
              <p className="text-xs text-slate-400 mt-1.5">
                The placeholder <code className="bg-slate-100 px-1 rounded">{"{BOOKING_URL}"}</code> will automatically be
                replaced with the actual booking link before sending.
              </p>
            </div>

            <Alert className="border-blue-100 bg-blue-50">
              <MessageCircle className="h-4 w-4 text-blue-600" />
              <AlertDescription className="text-blue-800 text-xs">
                A 7-day booking link will be created. The customer can use it to
                select their preferred date and time.
              </AlertDescription>
            </Alert>

            <DialogFooter className="gap-2">
              <Button
                variant="outline"
                onClick={handleClose}
                disabled={sendBookingLink.isPending}
              >
                Cancel
              </Button>
              <Button
                onClick={handleSendViaInstagram}
                disabled={!message.trim() || sendBookingLink.isPending}
                className="bg-gradient-to-r from-pink-600 to-purple-600 hover:from-pink-700 hover:to-purple-700 text-white gap-2"
                id="send-booking-link-btn"
              >
                {sendBookingLink.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Sending…
                  </>
                ) : (
                  <>
                    <MessageCircle className="h-4 w-4" />
                    Send via Instagram DM
                  </>
                )}
              </Button>
            </DialogFooter>
          </>
        ) : (
          /* Success State */
          <div className="flex flex-col items-center gap-4 py-4">
            <div className="h-16 w-16 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle2 className="h-9 w-9 text-green-600" />
            </div>
            <div className="text-center">
              <h3 className="text-base font-semibold text-slate-800">
                Booking Link Sent! 🎉
              </h3>
              <p className="text-sm text-slate-500 mt-1">
                The customer received your message in their Instagram DMs.
              </p>
            </div>
            {sentBookingUrl && (
              <div className="w-full bg-slate-50 rounded-lg border border-slate-200 px-4 py-3">
                <p className="text-xs text-slate-500 mb-1">Booking URL</p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-xs text-blue-700 truncate">
                    {sentBookingUrl}
                  </code>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 px-2 shrink-0"
                    onClick={handleCopyLink}
                  >
                    {copied ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600" />
                    ) : (
                      <Copy className="h-3.5 w-3.5 text-slate-500" />
                    )}
                  </Button>
                  <a
                    href={sentBookingUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Button variant="ghost" size="sm" className="h-7 px-2">
                      <ExternalLink className="h-3.5 w-3.5 text-slate-500" />
                    </Button>
                  </a>
                </div>
              </div>
            )}
            <Button onClick={handleClose} className="w-full bg-slate-900 hover:bg-slate-800">
              Done
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}