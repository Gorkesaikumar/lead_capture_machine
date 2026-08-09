import { useSearchParams } from "react-router-dom";
import { useLeadsList } from "@/api/leads.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { EmptyState } from "@/components/common/states/EmptyState";
import { Users } from "lucide-react";
import { LeadsFilterBar } from "./components/LeadsFilterBar";
import { LeadsTable } from "./components/LeadsTable";
import { LeadsMobileList } from "./components/LeadsMobileList";
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";

export default function LeadsList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1", 10);
  
  const params = Object.fromEntries(searchParams.entries());
  const { data, isLoading, isError, refetch } = useLeadsList(params);

  const handlePageChange = (newPage: number) => {
    const current = Object.fromEntries(searchParams.entries());
    current.page = newPage.toString();
    setSearchParams(current);
  };

  if (isError) {
    return (
      <PageContainer>
        <ErrorState 
          title="Failed to load leads" 
          message="We couldn't retrieve the leads pipeline. Please check your connection."
          onRetry={refetch}
        />
      </PageContainer>
    );
  }

  const leads = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / 10); // assuming default limit is 10

  return (
    <PageContainer>
      <PageHeader 
        title="Leads Pipeline"
        description="Manage incoming inquiries and track conversions."
        actions={
          <div className="bg-blue-50 text-blue-700 px-3 py-1 rounded-md text-sm font-medium border border-blue-100">
            {totalCount} Total
          </div>
        }
      />

      <div className="space-y-6">
        <LeadsFilterBar />

        {isLoading && !data ? (
          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <LoadingSkeleton rows={5} />
          </div>
        ) : leads.length === 0 ? (
          <EmptyState 
            icon={<Users className="h-8 w-8"/>} 
            title="No leads found" 
            description={Object.keys(params).length > 0 
              ? "We couldn't find any leads matching your current filters." 
              : "Your pipeline is currently empty."} 
          />
        ) : (
          <>
            <LeadsTable leads={leads} />
            <LeadsMobileList leads={leads} />

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="pt-4 flex justify-center sm:justify-end">
                <Pagination>
                  <PaginationContent>
                    <PaginationItem>
                      <PaginationPrevious 
                        onClick={() => page > 1 && handlePageChange(page - 1)}
                        className={page === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      />
                    </PaginationItem>
                    
                    <PaginationItem className="hidden sm:inline-flex px-4 text-sm text-slate-600 font-medium">
                      Page {page} of {totalPages}
                    </PaginationItem>
                    
                    <PaginationItem>
                      <PaginationNext 
                        onClick={() => page < totalPages && handlePageChange(page + 1)}
                        className={page >= totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                      />
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            )}
          </>
        )}
      </div>
    </PageContainer>
  );
}
