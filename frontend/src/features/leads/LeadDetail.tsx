import { useParams, useNavigate } from "react-router-dom";
import { useRef, useState } from "react";
import { useLeadDetail } from "@/api/leads.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { LeadConversation } from "./components/LeadConversation";
import { LeadContextPane } from "./components/LeadContextPane";
import { SendBookingLinkDialog } from "./components/SendBookingLinkDialog";

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: lead, isLoading, isError, refetch } = useLeadDetail(id || "");
  const [isLinkDialogOpen, setIsLinkDialogOpen] = useState(false);

  // Ref for the composer textarea — Quick Action "Send Message" focuses it
  const composerRef = useRef<HTMLTextAreaElement>(null);

  const handleFocusComposer = () => {
    composerRef.current?.focus();
    composerRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
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
      <div className="mb-4">
        <Button
          variant="ghost"
          onClick={() => navigate(-1)}
          className="text-slate-500 hover:text-slate-800 -ml-2"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Leads
        </Button>
      </div>

      <PageHeader
        title={lead.customer?.display_name || "Lead Details"}
        description={lead.summary || "Instagram conversation and booking management"}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left/Main Pane: Conversation */}
        <div className="lg:col-span-2">
          <LeadConversation
            leadId={lead.id}
            conversationId={lead.conversation_id}
            customerName={lead.customer?.display_name}
            composerRef={composerRef}
            onOpenBookingLinkDialog={() => setIsLinkDialogOpen(true)}
          />
        </div>

        {/* Right/Context Pane: Meta data & Actions */}
        <div className="lg:col-span-1">
          <LeadContextPane
            lead={lead}
            onSendLinkClick={() => setIsLinkDialogOpen(true)}
            onFocusComposer={handleFocusComposer}
          />
        </div>
      </div>

      <SendBookingLinkDialog
        open={isLinkDialogOpen}
        onOpenChange={setIsLinkDialogOpen}
        leadId={lead.id}
        defaultServiceId={lead.service?.id}
        customerName={lead.customer?.display_name}
      />
    </PageContainer>
  );
}