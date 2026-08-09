import { useState } from "react";
import { toast } from "sonner";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { formatDistanceToNow } from "date-fns";
import {
  Mail,
  Phone,
  UserCircle,
  MessageSquare,
  Sparkles,
  Edit3,
  MessageCircle,
} from "lucide-react";
import { useUpdateLeadStatus } from "@/api/leads.queries";
import { useQueryClient } from "@tanstack/react-query";

const LEAD_STATUSES = [
  { value: "NEW", label: "New" },
  { value: "CONTACTED", label: "Contacted" },
  { value: "QUALIFIED", label: "Qualified" },
  { value: "BOOKING_LINK_SENT", label: "Booking Link Sent" },
  { value: "BOOKED", label: "Booked" },
  { value: "COMPLETED", label: "Completed" },
  { value: "LOST", label: "Lost" },
  { value: "CANCELLED", label: "Cancelled" },
];

interface Props {
  lead: any;
  onSendLinkClick: () => void;
  onFocusComposer: () => void;
}

export function LeadContextPane({ lead, onSendLinkClick, onFocusComposer }: Props) {
  const customer = lead.customer;
  const initials = customer?.display_name
    ? customer.display_name.substring(0, 2).toUpperCase()
    : "CU";

  // Status Change Dialog
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState(lead.status);
  const [aiDialogOpen, setAiDialogOpen] = useState(false);

  const updateStatus = useUpdateLeadStatus();
  const queryClient = useQueryClient();

  const handleStatusChange = async () => {
    try {
      await updateStatus.mutateAsync({
        id: lead.id,
        status: selectedStatus,
        notes: `Status manually updated to ${selectedStatus}.`,
      });
      queryClient.invalidateQueries({ queryKey: ["leads", "detail", lead.id] });
      toast.success("Lead status updated.");
      setStatusDialogOpen(false);
    } catch {
      toast.error("Failed to update status.");
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Quick Actions Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
        <h3 className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wider">
          Quick Actions
        </h3>
        <div className="flex flex-col gap-2">
          {/* Send Message */}
          <Button
            className="w-full justify-start gap-2.5 bg-slate-900 hover:bg-slate-800 text-white"
            onClick={onFocusComposer}
            id="quick-action-send-message"
          >
            <MessageSquare className="h-4 w-4" />
            Send Message
          </Button>

          {/* Send Booking Link */}
          <Button
            variant="outline"
            className="w-full justify-start gap-2.5 text-slate-700 border-slate-200 hover:bg-slate-50"
            onClick={onSendLinkClick}
            id="quick-action-send-booking-link"
          >
            <div className="h-4 w-4 rounded-full bg-gradient-to-br from-pink-500 to-purple-600 flex items-center justify-center">
              <MessageCircle className="h-2.5 w-2.5 text-white" />
            </div>
            Send Booking Link
          </Button>

          {/* AI Follow-up */}
          <Button
            variant="outline"
            className="w-full justify-start gap-2.5 text-slate-500 border-slate-200 border-dashed hover:bg-slate-50"
            onClick={() => setAiDialogOpen(true)}
            id="quick-action-ai-followup"
          >
            <Sparkles className="h-4 w-4 text-slate-400" />
            AI Follow-up
          </Button>

          {/* Change Status */}
          <Button
            variant="outline"
            className="w-full justify-start gap-2.5 text-slate-600 border-slate-200 hover:bg-slate-50"
            onClick={() => {
              setSelectedStatus(lead.status);
              setStatusDialogOpen(true);
            }}
            id="quick-action-change-status"
          >
            <Edit3 className="h-4 w-4" />
            Change Status
          </Button>
        </div>
      </div>

      {/* Customer Detail Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm">
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
          Lead Context
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
          <div className="flex justify-between items-start pb-3 border-b border-slate-100">
            <span className="text-xs text-slate-500 mt-0.5">Requirement</span>
            <span className="text-xs font-medium text-slate-700 text-right max-w-[140px]">
              {lead.trigger_service_name ||
                lead.trigger_phrase ||
                lead.service?.name ||
                "General Inquiry"}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-slate-500">Received</span>
            <span className="text-xs font-medium text-slate-700">
              {formatDistanceToNow(new Date(lead.created_at), {
                addSuffix: true,
              })}
            </span>
          </div>
        </div>
      </div>

      {/* Status Change Dialog */}
      <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
        <DialogContent className="sm:max-w-[380px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit3 className="h-4 w-4 text-slate-600" />
              Change Lead Status
            </DialogTitle>
            <DialogDescription>
              Select the new status for this lead opportunity.
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger id="status-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LEAD_STATUSES.map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setStatusDialogOpen(false)}
              disabled={updateStatus.isPending}
            >
              Cancel
            </Button>
            <Button
              onClick={handleStatusChange}
              disabled={
                selectedStatus === lead.status || updateStatus.isPending
              }
              className="bg-slate-900 hover:bg-slate-800 text-white"
              id="confirm-status-btn"
            >
              {updateStatus.isPending ? "Updating…" : "Update Status"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AI Follow-up Dialog */}
      <Dialog open={aiDialogOpen} onOpenChange={setAiDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-purple-500" />
              AI Follow-up Assistant
            </DialogTitle>
            <DialogDescription>
              Automatically generate contextual follow-up messages based on the
              conversation.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col items-center gap-4 py-6 text-center">
            <div className="h-16 w-16 rounded-full bg-purple-50 flex items-center justify-center border-2 border-purple-100">
              <Sparkles className="h-8 w-8 text-purple-300" />
            </div>
            <div>
              <p className="text-sm font-medium text-slate-700">
                AI Assistant Not Configured
              </p>
              <p className="text-xs text-slate-500 mt-2 max-w-[280px] leading-relaxed">
                This is a future integration point for AI-generated follow-up
                responses. Configure an AI provider (e.g., Gemini, GPT-4) in
                settings to enable this feature.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button
              className="w-full bg-slate-900 hover:bg-slate-800"
              onClick={() => setAiDialogOpen(false)}
            >
              Got it
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
