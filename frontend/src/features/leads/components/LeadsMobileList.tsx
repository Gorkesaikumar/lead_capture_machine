import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow, format } from "date-fns";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  MoreVertical, Edit3, UserCheck, Trash2, Eye, User, MessageCircle, Mail
} from "lucide-react";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { useUpdateLeadStatus, useAssignLead, useDeleteLead } from "@/api/leads.queries";
import { useTeamMembers } from "@/api/team.queries";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function LeadsMobileList({ leads }: { leads: any[] }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: team = [] } = useTeamMembers();
  const updateStatus = useUpdateLeadStatus();
  const assignLead = useAssignLead();
  const deleteLead = useDeleteLead();

  const [activeLead, setActiveLead] = useState<any>(null);
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [assignDialogOpen, setAssignDialogOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState("");
  const [selectedStaff, setSelectedStaff] = useState("");

  const handleStatusChange = async () => {
    if (!activeLead) return;
    try {
      await updateStatus.mutateAsync({ id: activeLead.id, status: selectedStatus });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Status updated");
      setStatusDialogOpen(false);
    } catch {
      toast.error("Failed to update status");
    }
  };

  const handleAssign = async () => {
    if (!activeLead) return;
    try {
      await assignLead.mutateAsync({ id: activeLead.id, staff_id: selectedStaff === "unassigned" ? null : selectedStaff });
      queryClient.invalidateQueries({ queryKey: ["leads"] });
      toast.success("Lead assigned");
      setAssignDialogOpen(false);
    } catch {
      toast.error("Failed to assign lead");
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this lead?")) {
      try {
        await deleteLead.mutateAsync(id);
        queryClient.invalidateQueries({ queryKey: ["leads"] });
        toast.success("Lead deleted");
      } catch {
        toast.error("Failed to delete lead");
      }
    }
  };

  return (
    <>
      <div className="md:hidden space-y-3">
        {leads.map((lead) => (
          <div
            key={lead.id}
            className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm"
          >
            <div className="flex justify-between items-start mb-2">
              <div
                className="flex flex-col cursor-pointer"
                onClick={() => navigate(`/app/leads/${lead.id}`)}
              >
                <span className="font-medium text-slate-900">{lead.customer?.display_name || "Unknown"}</span>
                <div className="flex flex-col text-xs text-slate-500 mt-1 gap-0.5">
                  {lead.customer?.primary_phone && (
                    <span className="flex items-center gap-1"><MessageCircle className="w-3 h-3 text-slate-400" />{lead.customer.primary_phone}</span>
                  )}
                  {lead.customer?.email && (
                    <span className="flex items-center gap-1"><Mail className="w-3 h-3 text-slate-400" />{lead.customer.email}</span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1">
                <StatusBadge status={lead.status} />
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" size="icon" className="h-8 w-8 -mr-2">
                      <MoreVertical className="h-4 w-4 text-slate-500" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                    <DropdownMenuItem onClick={() => navigate(`/app/leads/${lead.id}`)}>
                      <Eye className="mr-2 h-4 w-4" /> View Details
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => {
                      setActiveLead(lead);
                      setSelectedStatus(lead.status);
                      setStatusDialogOpen(true);
                    }}>
                      <Edit3 className="mr-2 h-4 w-4" /> Change Status
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => {
                      setActiveLead(lead);
                      setSelectedStaff(lead.assigned_staff?.id || "unassigned");
                      setAssignDialogOpen(true);
                    }}>
                      <UserCheck className="mr-2 h-4 w-4" /> Assign Staff
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem className="text-red-600" onClick={() => handleDelete(lead.id)}>
                      <Trash2 className="mr-2 h-4 w-4" /> Delete Lead
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-y-2 mt-4 text-sm">
              <div className="flex flex-col gap-1">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Source</span>
                <div className="flex"><SourceBadge source={lead.source_channel} /></div>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-xs text-slate-400 uppercase tracking-wider">Assigned To</span>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <User className="h-3.5 w-3.5" />
                  <span className="truncate">{lead.assigned_staff?.full_name || "Unassigned"}</span>
                </div>
              </div>
            </div>

            <div className="flex justify-between items-center mt-3 pt-3 border-t border-slate-100 text-xs text-slate-500">
              <span>Updated {formatDistanceToNow(new Date(lead.updated_at), { addSuffix: true })}</span>
              <span>Created {format(new Date(lead.created_at), "MMM d, yyyy")}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Dialogs */}
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
    </>
  );
}
