import { useState } from "react";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { SectionHeader } from "@/components/common/layout/SectionHeader";
import { KpiCard } from "@/components/common/ui/KpiCard";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { FilterBar } from "@/components/common/ui/FilterBar";
import { ConfirmationDialog } from "@/components/common/overlays/ConfirmationDialog";
import { EmptyState } from "@/components/common/states/EmptyState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";
import { Button } from "@/components/ui/button";
import { Camera, Users } from "lucide-react";
import { toast } from "sonner";

export default function DesignSystemShowcase() {
  const [dialogOpen, setDialogOpen] = useState(false);

  return (
    <PageContainer>
      <PageHeader 
        title="Premium Design System" 
        description="A showcase of the reusable components and primitives." 
        actions={
          <Button onClick={() => toast.success("Action triggered!")}>
            Primary Action
          </Button>
        }
      />

      <div className="space-y-12">
        {/* KPI Cards */}
        <section>
          <SectionHeader title="KPI Cards" description="Used for dashboard summaries." />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard title="Total Shoots" value="1,248" icon={Camera} trend={{ value: "12%", isPositive: true }} />
            <KpiCard title="Active Leads" value="43" icon={Users} trend={{ value: "5%", isPositive: false }} />
          </div>
        </section>

        {/* Badges */}
        <section>
          <SectionHeader title="Badges" description="Status and source indicators." />
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2">
              <p className="text-sm text-slate-500">Status Badges</p>
              <div className="flex gap-2">
                <StatusBadge status="pending" />
                <StatusBadge status="confirmed" />
                <StatusBadge status="completed" />
                <StatusBadge status="cancelled" />
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-slate-500">Source Badges</p>
              <div className="flex gap-2">
                <SourceBadge source="instagram" />
                <SourceBadge source="whatsapp" />
                <SourceBadge source="website" />
              </div>
            </div>
          </div>
        </section>

        {/* Filters */}
        <section>
          <SectionHeader title="Filter Bar" description="Search and filter lists." />
          <FilterBar />
        </section>

        {/* Buttons & Dialogs */}
        <section>
          <SectionHeader title="Overlays & Actions" description="Premium button treatments and dialogs." />
          <div className="flex gap-4 items-center">
            <Button variant="default">Default Button</Button>
            <Button variant="secondary">Secondary Button</Button>
            <Button variant="outline">Outline Button</Button>
            <Button variant="destructive" onClick={() => setDialogOpen(true)}>
              Open Destructive Dialog
            </Button>
          </div>
          
          <ConfirmationDialog 
            open={dialogOpen}
            onOpenChange={setDialogOpen}
            title="Delete Lead"
            description="Are you sure you want to delete this lead? This action cannot be undone."
            confirmLabel="Delete"
            isDestructive={true}
            onConfirm={() => toast.error("Lead deleted.")}
          />
        </section>

        {/* States */}
        <section>
          <SectionHeader title="System States" description="Empty, loading, and error states." />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <EmptyState 
              title="No leads found" 
              description="You don't have any pending leads matching this criteria."
              action={{ label: "Clear Filters", onClick: () => {} }}
            />
            <div className="border rounded-lg bg-white p-4">
              <p className="text-sm text-slate-500 mb-4 font-medium">Loading State</p>
              <LoadingSkeleton rows={4} />
            </div>
            <ErrorState message="Could not fetch data from the server." />
          </div>
        </section>
      </div>
    </PageContainer>
  );
}