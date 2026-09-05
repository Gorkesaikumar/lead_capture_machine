import { useParams, useNavigate } from "react-router-dom";
import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useLeadDetail, useUpdateLeadStatus, useAssignLead } from "@/api/leads.queries";
import { useTeamMembers } from "@/api/team.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { ArrowLeft, MessageSquare, Edit3, UserCheck } from "lucide-react";
import { LeadConversation } from "./components/LeadConversation";
import { LeadContextPane } from "./components/LeadContextPane";
import { SendBookingLinkDialog } from "./components/SendBookingLinkDialog";
import { LeadActivityLog } from "./components/LeadActivityLog";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: lead, isLoading, isError, refetch } = useLeadDetail(id || "");
  const { data: team = [] } = useTeamMembers();
  const updateStatus = useUpdateLeadStatus();
  const assignLead = useAssignLead();

  const [isLinkDialogOpen, setIsLinkDialogOpen] = useState(false);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);

  const [selectedStatus, setSelectedStatus] = useState("");
  const [selectedStaff, setSelectedStaff] = useState("");

  const composerRef = useRef<HTMLTextAreaElement>(null);

  const handleFocusComposer = () => {
    composerRef.current?.focus();
    composerRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const handleStatusChange = async () => {
    if (!lead) return;
    try {
      await updateStatus.mutateAsync({ id: lead.id, status: selectedStatus, notes: `Status manually updated to ${selectedStatus}.` });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Status updated");
      setStatusDialogOpen(false);
    } catch {
      toast.error("Failed to update status");
    }
  };

  const handleAssign = async () => {
    if (!lead) return;
    try {
      await assignLead.mutateAsync({ id: lead.id, staff_id: selectedStaff === "unassigned" ? null : selectedStaff });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Lead assigned");
      setAssignDialogOpen(false);
    } catch {
      toast.error("Failed to assign lead");
    }
  };

  if (isLoading) {
    return (
      <PageContainer>
        <LoadingSkeleton rows={8} />
      </PageContainer>
    );
  }

  if (isError || !lead) {
    return (
      <PageContainer>
        <ErrorState
          title="Lead not found"
          message="We couldn't retrieve the details for this lead."
          onRetry={refetch}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Top Breadcrumb */}
      <div className="mb-4">
        <Button
          variant="ghost"
          onClick={() => navigate(-1)}
          className="text-slate-500 hover:text-slate-800 -ml-2 h-8"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Leads
        </Button>
      </div>

      {/* LEAD HEADER */}
      <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-200">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {lead.customer?.display_name || "Unknown Customer"}
          </h1>
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={lead.status} />
            <SourceBadge source={lead.source_channel} />
            <span className="text-sm text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
              Assigned: {lead.assigned_staff?.full_name || "Unassigned"}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            className="text-slate-600 border-slate-200"
            onClick={() => {
              setSelectedStatus(lead.status);
              setStatusDialogOpen(true);
            }}
          >
            <Edit3 className="mr-2 h-4 w-4" /> Change Status
          </Button>
          <Button
            variant="outline"
            className="text-slate-600 border-slate-200"
            onClick={() => {
              setSelectedStaff(lead.assigned_staff?.id || "unassigned");
              setAssignDialogOpen(true);
            }}
          >
            <UserCheck className="mr-2 h-4 w-4" /> Assign User
          </Button>

          <Button
            className="bg-slate-900 hover:bg-slate-800 text-white"
            onClick={handleFocusComposer}
          >
            <MessageSquare className="mr-2 h-4 w-4" /> Message
          </Button>
        </div>
      </div>

      {/* SPLIT LAYOUT: INFO (LEFT) AND CONVERSATION (RIGHT) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Left Pane: Lead Information & Contact */}
        <div className="lg:col-span-1">
          <LeadContextPane
            lead={lead}
          />
        </div>

        {/* Right Pane: Conversation */}
        <div className="lg:col-span-2 flex flex-col">
          <div className="flex-1 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col min-h-[500px]">
            {(lead.source_channel === "INSTAGRAM" || lead.source_channel === "WHATSAPP") ? (
              <LeadConversation
                leadId={lead.id}
                conversationId={lead.conversation_id}
                customerName={lead.customer?.display_name}
                composerRef={composerRef}
                onOpenBookingLinkDialog={() => setIsLinkDialogOpen(true)}
              />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center py-16 text-slate-400 bg-slate-50/30">
                <div className="h-16 w-16 rounded-full bg-slate-100 flex items-center justify-center mb-4">
                  <MessageSquare className="h-8 w-8 text-slate-300" />
                </div>
                <h3 className="text-lg font-medium text-slate-600 mb-1">No Active Conversation</h3>
                <p className="text-sm text-slate-500 max-w-md text-center px-4">
                  This lead originated from <strong>{lead.source_channel === "WEBSITE" ? "a Website Form" : "Manual Entry"}</strong>.
                  Direct messaging is only available for leads captured via Instagram or WhatsApp.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* BOTTOM LAYOUT: ACTIVITY LOG */}
      <LeadActivityLog activities={lead.activities || []} />

      {/* DIALOGS */}
      <SendBookingLinkDialog
        open={isLinkDialogOpen}
        onOpenChange={setIsLinkDialogOpen}
        leadId={lead.id}
        defaultServiceId={lead.service?.id}
        customerName={lead.customer?.display_name}
      />

      <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Change Status</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger><SelectValue placeholder="Select status" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="NEW">New</SelectItem>
                <SelectItem value="CONTACTED">Contacted</SelectItem>
                <SelectItem value="QUALIFIED">Qualified</SelectItem>
                <SelectItem value="CONVERTED">Converted</SelectItem>
                <SelectItem value="LOST">Lost</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatusDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleStatusChange} disabled={updateStatus.isPending}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Assign Lead</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            <Select value={selectedStaff} onValueChange={setSelectedStaff}>
              <SelectTrigger><SelectValue placeholder="Select team member" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                {team.map((member: any) => (
                  <SelectItem key={member.id} value={member.user?.id || member.id}>
                    {member.user?.full_name || member.user?.email || member.full_name || member.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAssign} disabled={assignLead.isPending}>Assign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>


    </PageContainer>
  );
}
