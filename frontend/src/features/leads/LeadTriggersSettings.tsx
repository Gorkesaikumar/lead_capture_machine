import { useState } from "react";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";
import { useLeadTriggers, useDeleteLeadTrigger } from "@/api/leads.queries";
import { useServicesList } from "@/api/services.queries";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { LeadTriggerFormSheet } from "./components/LeadTriggerFormSheet";

export default function LeadTriggersSettings() {
  const { data: triggers, isLoading } = useLeadTriggers();
  const { data: services } = useServicesList();
  const deleteTrigger = useDeleteLeadTrigger();

  const [formOpen, setFormOpen] = useState(false);
  const [editingTrigger, setEditingTrigger] = useState<any>(null);

  const handleEdit = (trigger: any) => {
    setEditingTrigger(trigger);
    setFormOpen(true);
  };

  const handleCreate = () => {
    setEditingTrigger(null);
    setFormOpen(true);
  };

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this trigger?")) {
      deleteTrigger.mutate(id);
    }
  };

  const getServiceName = (id: string) => {
    if (!services || !id) return "None";
    const svc = services.find((s: any) => s.id === id);
    return svc ? svc.name : "None";
  };

  return (
    <PageContainer>
      <PageHeader 
        title="Lead Triggers"
        description="Automatically capture and qualify leads based on incoming WhatsApp/Instagram phrases."
        actions={
          <Button onClick={handleCreate} className="bg-slate-900 text-white hover:bg-slate-800">
            <Plus className="mr-2 h-4 w-4" /> Add Trigger
          </Button>
        }
      />

      <div className="mt-6">
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton rows={4} /></div>
          ) : triggers?.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              No triggers configured. Click "Add Trigger" to create one.
            </div>
          ) : (
            <Table>
              <TableHeader className="bg-slate-50">
                <TableRow>
                  <TableHead>Phrase / Keyword</TableHead>
                  <TableHead>Match Type</TableHead>
                  <TableHead>Mapped Service</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {triggers?.map((t: any) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-medium text-slate-900">"{t.phrase}"</TableCell>
                    <TableCell className="text-sm text-slate-600">{t.match_type}</TableCell>
                    <TableCell className="text-sm text-slate-600">{getServiceName(t.service)}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="bg-slate-50 text-slate-700">{t.priority}</Badge>
                    </TableCell>
                    <TableCell>
                      {t.is_active ? (
                        <Badge className="bg-green-100 text-green-800 hover:bg-green-100">Active</Badge>
                      ) : (
                        <Badge variant="secondary" className="bg-slate-100 text-slate-500">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right space-x-2">
                      <Button variant="outline" size="sm" onClick={() => handleEdit(t)}>Edit</Button>
                      <Button variant="destructive" size="sm" onClick={() => handleDelete(t.id)}>Delete</Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>

      <LeadTriggerFormSheet 
        open={formOpen} 
        onOpenChange={setFormOpen} 
        triggerToEdit={editingTrigger} 
      />
    </PageContainer>
  );
}