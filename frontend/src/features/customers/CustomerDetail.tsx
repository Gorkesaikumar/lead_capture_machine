import { useParams, useNavigate } from "react-router-dom";
import { useCustomerDetail, useCustomerHistory } from "@/api/customers.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Button } from "@/components/ui/button";
import { ArrowLeft } from "lucide-react";
import { CustomerProfilePane } from "./components/CustomerProfilePane";
import { CustomerHistoryPane } from "./components/CustomerHistoryPane";

export default function CustomerDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const { data: customer, isLoading: isCustLoading, isError: isCustError, refetch: refetchCust } = useCustomerDetail(id || "");
  const { data: history, isLoading: isHistLoading } = useCustomerHistory(id || "");

  const isLoading = isCustLoading || isHistLoading;

  if (isLoading) {
    return (
      <PageContainer>
        <LoadingSkeleton rows={8} />
      </PageContainer>
    );
  }

  if (isCustError || !customer) {
    return (
      <PageContainer>
        <ErrorState 
          title="Customer not found" 
          message="We couldn't retrieve the details for this customer."
          onRetry={refetchCust}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mb-6 flex items-center justify-between">
        <Button 
          variant="ghost" 
          onClick={() => navigate(-1)}
          className="text-slate-500 hover:text-slate-800 -ml-2"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Directory
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left/Context Pane: Customer Identity */}
        <div className="lg:col-span-1">
          <CustomerProfilePane customer={customer} />
        </div>

        {/* Right/Main Pane: History */}
        <div className="lg:col-span-2">
          <CustomerHistoryPane history={history || {}} />
        </div>
      </div>
    </PageContainer>
  );
}