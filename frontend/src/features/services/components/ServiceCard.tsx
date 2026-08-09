import { useState } from "react";
import { formatINR } from "@/utils/formatters";
import { useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Plus, Edit2, Trash2, PowerOff, Power } from "lucide-react";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ConfirmActionDialog } from "@/components/common/states/ConfirmActionDialog";
import { useToggleServiceActive, useDeleteService, useTogglePackageActive, useDeletePackage } from "@/api/services.queries";
import { toast } from "sonner";
import { PackageFormDialog } from "./PackageFormDialog";

export function ServiceCard({ service, onEdit }: { service: any, onEdit: (s: any) => void }) {
  const queryClient = useQueryClient();
  const toggleService = useToggleServiceActive();
  const deleteService = useDeleteService();
  const togglePackage = useTogglePackageActive();
  const deletePackage = useDeletePackage();

  const [confirmDelete, setConfirmDelete] = useState(false);
  const [confirmToggle, setConfirmToggle] = useState(false);
  
  const [pkgDialogOpen, setPkgDialogOpen] = useState(false);
  const [editingPkg, setEditingPkg] = useState<any>(null);

  const handleDeleteService = async () => {
    try {
      await deleteService.mutateAsync(service.id);
      toast.success("Service deleted");
      queryClient.invalidateQueries({ queryKey: ["services"] });
    } catch {
      toast.error("Failed to delete service");
    }
  };

  const handleToggleService = async () => {
    try {
      await toggleService.mutateAsync(service.id);
      toast.success(`Service ${service.is_active ? "deactivated" : "activated"}`);
      queryClient.invalidateQueries({ queryKey: ["services"] });
    } catch {
      toast.error("Failed to toggle service status");
    }
  };

  const handleTogglePkg = async (pkgId: string) => {
    try {
      await togglePackage.mutateAsync(pkgId);
      toast.success("Package status toggled");
      queryClient.invalidateQueries({ queryKey: ["services"] });
    } catch {
      toast.error("Failed to toggle package");
    }
  };

  const handleDeletePkg = async (pkgId: string) => {
    try {
      await deletePackage.mutateAsync(pkgId);
      toast.success("Package deleted");
      queryClient.invalidateQueries({ queryKey: ["services"] });
    } catch {
      toast.error("Failed to delete package");
    }
  };

  return (
    <>
      <div className={`bg-white rounded-lg border shadow-sm overflow-hidden transition-opacity ${!service.is_active ? "opacity-60 grayscale-[0.3]" : "border-gray-200"}`}>
        <div className="p-5 border-b border-gray-100 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-slate-900">{service.name}</h3>
              {!service.is_active && (
                <span className="bg-slate-100 text-slate-600 text-xs px-2 py-0.5 rounded-full font-medium">Inactive</span>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">{service.description || "No description provided."}</p>
            <div className="mt-4 flex gap-4 text-sm font-medium text-slate-700">
              <span className="bg-slate-50 px-2 py-1 rounded border border-slate-100">Base: {formatINR(service.base_price)}</span>
              <span className="bg-slate-50 px-2 py-1 rounded border border-slate-100">{service.duration_minutes} mins</span>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-500"><MoreHorizontal className="h-4 w-4" /></Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(service)}><Edit2 className="mr-2 h-4 w-4" /> Edit Service</DropdownMenuItem>
              <DropdownMenuItem onClick={() => { setEditingPkg(null); setPkgDialogOpen(true); }}><Plus className="mr-2 h-4 w-4" /> Add Package</DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setConfirmToggle(true)}>
                {service.is_active ? <><PowerOff className="mr-2 h-4 w-4" /> Deactivate</> : <><Power className="mr-2 h-4 w-4" /> Activate</>}
              </DropdownMenuItem>
              <DropdownMenuItem className="text-red-600 focus:bg-red-50 focus:text-red-700" onClick={() => setConfirmDelete(true)}>
                <Trash2 className="mr-2 h-4 w-4" /> Delete Service
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Packages List */}
        <div className="bg-slate-50/50">
          {service.packages?.length > 0 ? (
            <div className="divide-y divide-gray-100">
              {service.packages.map((pkg: any) => (
                <div key={pkg.id} className={`p-4 flex justify-between items-center ${!pkg.is_active ? "opacity-50" : ""}`}>
                  <div>
                    <h4 className="font-semibold text-slate-800 text-sm">{pkg.name}</h4>
                    <p className="text-xs text-slate-500 mt-1">{pkg.inclusions?.length || 0} inclusions</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-slate-900 text-sm">{formatINR(pkg.price)}</span>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-6 w-6"><MoreHorizontal className="h-3 w-3" /></Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => { setEditingPkg(pkg); setPkgDialogOpen(true); }}>Edit Package</DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleTogglePkg(pkg.id)}>{pkg.is_active ? "Deactivate" : "Activate"}</DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem className="text-red-600" onClick={() => {
                          if(confirm("Are you sure you want to delete this package?")) handleDeletePkg(pkg.id);
                        }}>Delete</DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-sm text-slate-400">No packages created yet.</div>
          )}
        </div>
      </div>

      <ConfirmActionDialog 
        open={confirmDelete} onOpenChange={setConfirmDelete}
        title="Delete Service" description={`Are you sure you want to delete ${service.name}? This will also remove its packages.`}
        destructive onConfirm={handleDeleteService} confirmText="Delete"
      />
      <ConfirmActionDialog 
        open={confirmToggle} onOpenChange={setConfirmToggle}
        title={service.is_active ? "Deactivate Service" : "Activate Service"} 
        description={`This service will ${service.is_active ? "no longer be available for booking" : "now be bookable"}.`}
        onConfirm={handleToggleService} confirmText={service.is_active ? "Deactivate" : "Activate"}
      />
      
      <PackageFormDialog 
        open={pkgDialogOpen} onOpenChange={setPkgDialogOpen}
        serviceId={service.id} editingPackage={editingPkg}
      />
    </>
  );
}