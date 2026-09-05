import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { 
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger 
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Plus } from "lucide-react";
import { apiClient } from "@/api/client";
import { useTeamMembers } from "@/api/team.queries";


interface CreateLeadForm {
  customer_name: string;
  phone_number?: string;
  email?: string;
  source_channel: "MANUAL" | "WEBSITE";
  summary?: string;
  notes?: string;
  status?: string;
  assigned_staff_id?: string;
}

export function CreateLeadDialog() {
  const [open, setOpen] = useState(false);
  const queryClient = useQueryClient();
  const { data: team = [] } = useTeamMembers();
  


  const { register, handleSubmit, reset, setValue, watch, formState: { isSubmitting } } = useForm<CreateLeadForm>({
    defaultValues: {
      source_channel: "MANUAL",
      status: "NEW",
      assigned_staff_id: "unassigned"
    }
  });
  
  const sourceChannel = watch("source_channel");
  const status = watch("status");
  const assignedStaffId = watch("assigned_staff_id");

  const createLead = useMutation({
    mutationFn: async (data: CreateLeadForm) => {
      const response = await apiClient.post("/leads/", {
        ...data,
        assigned_staff_id: data.assigned_staff_id === "unassigned" ? null : data.assigned_staff_id,
      });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Lead created successfully");
      setOpen(false);
      reset();
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create lead. Check required fields and workspace limits.");
    }
  });

  const onSubmit = (data: CreateLeadForm) => {
    createLead.mutate(data);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="bg-slate-900 hover:bg-slate-800 text-white">
          <Plus className="h-4 w-4 mr-2" />
          Add Lead
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add New Lead</DialogTitle>
            <DialogDescription>
              Create a sales opportunity manually. Deduplication by email or phone is automatic.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4 max-h-[60vh] overflow-y-auto px-1">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="customer_name" className="text-right text-sm">Name <span className="text-red-500">*</span></Label>
              <Input
                id="customer_name"
                className="col-span-3 h-9"
                {...register("customer_name", { required: true })}
              />
            </div>
            
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="phone_number" className="text-right text-sm">Phone</Label>
              <Input
                id="phone_number"
                placeholder="+1234567890"
                className="col-span-3 h-9"
                {...register("phone_number")}
              />
            </div>

            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="email" className="text-right text-sm">Email</Label>
              <Input
                id="email"
                type="email"
                className="col-span-3 h-9"
                {...register("email")}
              />
            </div>
            
            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right text-sm">Source</Label>
              <div className="col-span-3">
                <Select value={sourceChannel} onValueChange={(v) => setValue("source_channel", v as any)}>
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Select a source" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MANUAL">Manual Entry</SelectItem>
                    <SelectItem value="WEBSITE">Website Form</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right text-sm">Status</Label>
              <div className="col-span-3">
                <Select value={status} onValueChange={(v) => setValue("status", v)}>
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="NEW">New</SelectItem>
                    <SelectItem value="CONTACTED">Contacted</SelectItem>
                    <SelectItem value="QUALIFIED">Qualified</SelectItem>
                    <SelectItem value="CONVERTED">Converted</SelectItem>
                    <SelectItem value="LOST">Lost</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-4 items-center gap-4">
              <Label className="text-right text-sm">Assign To</Label>
              <div className="col-span-3">
                <Select value={assignedStaffId} onValueChange={(v) => setValue("assigned_staff_id", v)}>
                  <SelectTrigger className="h-9">
                    <SelectValue placeholder="Select team member" />
                  </SelectTrigger>
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
            </div>

            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="summary" className="text-right text-sm">Requirement</Label>
              <Input
                id="summary"
                placeholder="Brief description"
                className="col-span-3 h-9"
                {...register("summary")}
              />
            </div>

            <div className="grid grid-cols-4 items-start gap-4">
              <Label htmlFor="notes" className="text-right mt-2 text-sm">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Additional context..."
                className="col-span-3 min-h-[60px]"
                {...register("notes")}
              />
            </div>

          </div>
          <DialogFooter className="flex flex-col sm:flex-row gap-2 mt-4 pt-4 border-t border-slate-100">
            <Button type="button" variant="outline" onClick={() => setOpen(false)} className="w-full sm:w-auto min-h-[44px]">
              Cancel
            </Button>
            <Button type="submit" disabled={createLead.isPending || isSubmitting} className="w-full sm:w-auto min-h-[44px] bg-slate-900 hover:bg-slate-800">
              {createLead.isPending || isSubmitting ? "Saving..." : "Save Lead"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
