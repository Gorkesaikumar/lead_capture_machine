import { useState } from "react";
import { useServicesList } from "@/api/services.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { EmptyState } from "@/components/common/states/EmptyState";
import { Button } from "@/components/ui/button";
import { Camera, Plus } from "lucide-react";
import { ServiceCard } from "./components/ServiceCard";
import { ServiceFormSheet } from "./components/ServiceFormSheet";

export default function ServicesList() {
  const { data: services, isLoading, isError, refetch } = useServicesList();
  
  const [sheetOpen, setSheetOpen] = useState(false);
  const [editingService, setEditingService] = useState<any>(null);

  const handleAddService = () => {
    setEditingService(null);
    setSheetOpen(true);
  };

  const handleEditService = (service: any) => {
    setEditingService(service);
    setSheetOpen(true);
  };

  if (isError) {
    return (
      <PageContainer>
        <ErrorState 
          title="Failed to load services" 
          message="We couldn't retrieve the studio services."
          onRetry={refetch}
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader 
        title="Services & Packages"
        description="Manage your photography offerings, durations, and pricing tiers."
        actions={
          <Button onClick={handleAddService} className="bg-slate-900 text-white hover:bg-slate-800">
            <Plus className="mr-2 h-4 w-4" />
            Add Service
          </Button>
        }
      />

      <div className="mt-6">
        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <LoadingSkeleton rows={4} />
            <LoadingSkeleton rows={4} />
            <LoadingSkeleton rows={4} />
          </div>
        ) : !services || services.length === 0 ? (
          <EmptyState 
            icon={<Camera className="h-8 w-8"/>} 
            title="No services found" 
            description="You haven't set up any photography services yet." 
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {services.map((svc: any) => (
              <ServiceCard key={svc.id} service={svc} onEdit={handleEditService} />
            ))}
          </div>
        )}
      </div>

      <ServiceFormSheet 
        open={sheetOpen} 
        onOpenChange={setSheetOpen} 
        editingService={editingService} 
      />
    </PageContainer>
  );
}
