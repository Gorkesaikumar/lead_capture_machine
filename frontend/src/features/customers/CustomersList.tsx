import { useSearchParams } from "react-router-dom";
import { useCustomersList } from "@/api/customers.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { EmptyState } from "@/components/common/states/EmptyState";
import { UserCircle } from "lucide-react";
import { CustomersFilterBar } from "./components/CustomersFilterBar";
import { CustomersTable } from "./components/CustomersTable";
import { Pagination, PaginationContent, PaginationItem, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";

export default function CustomersList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") || "1", 10);
  
  const params = Object.fromEntries(searchParams.entries());
  const { data, isLoading, isError, refetch } = useCustomersList(params);

  const handlePageChange = (newPage: number) => {
    const current = Object.fromEntries(searchParams.entries());
    current.page = newPage.toString();
    setSearchParams(current);
  };

  if (isError) {
    return (
      <PageContainer>
        <ErrorState 
          title="Failed to load customers" 
          message="We couldn't retrieve the customer directory. Please check your connection."
          onRetry={refetch}
        />
      </PageContainer>
    );
  }

  const customers = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / 10);

  return (
    <PageContainer>
      <PageHeader 
        title="Customers"
        description="View your entire client directory and their histories."
        actions={
          <div className="bg-blue-50 text-blue-700 px-3 py-1 rounded-md text-sm font-medium border border-blue-100">
            {totalCount} Total
          </div>
        }
      />

      <div className="space-y-6">
        <CustomersFilterBar />

        {isLoading && !data ? (
          <div className="bg-white p-6 rounded-lg border border-gray-200">
            <LoadingSkeleton rows={5} />
          </div>
        ) : customers.length === 0 ? (
          <EmptyState 
            icon={<UserCircle className="h-8 w-8"/>} 
            title="No customers found" 
            description={Object.keys(params).length > 0 
              ? "We couldn't find any customers matching your search." 
              : "Your customer directory is empty."} 
          />
        ) : (
          <>
            <CustomersTable customers={customers} />

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
