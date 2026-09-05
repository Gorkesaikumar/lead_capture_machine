import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { formatDistanceToNow, format } from "date-fns";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow
} from "@/components/ui/table";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger
} from "@/components/ui/dropdown-menu";
import { MoreHorizontal, User, UserCheck, Eye, Trash2, Edit3, MessageCircle, Mail } from "lucide-react";
import { useUpdateLeadStatus, useAssignLead, useDeleteLead } from "@/api/leads.queries";
import { useTeamMembers } from "@/api/team.queries";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function LeadsTable({ leads }: { leads: any[] }) {
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
      {/* Desktop Table View */}
      <div className="hidden md:block bg-white rounded-lg border border-slate-200 overflow-x-auto shadow-sm w-full">
        <Table>
          <TableHeader className="bg-slate-50 border-b border-slate-200">
            <TableRow>
              <TableHead className="font-semibold text-slate-700">Name</TableHead>
              <TableHead className="font-semibold text-slate-700">Contact</TableHead>
              <TableHead className="font-semibold text-slate-700">Source</TableHead>
              <TableHead className="font-semibold text-slate-700">Status</TableHead>
              <TableHead className="font-semibold text-slate-700">Assigned To</TableHead>
              <TableHead className="font-semibold text-slate-700">Last Activity</TableHead>
              <TableHead className="font-semibold text-slate-700">Created</TableHead>
              <TableHead className="text-right font-semibold text-slate-700">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {leads.map((lead) => (
              <TableRow
                key={lead.id}
                className="hover:bg-slate-50 transition-colors"
              >
                <TableCell
                  className="font-medium text-slate-900 cursor-pointer"
                  onClick={() => navigate(`/app/leads/${lead.id}`)}
                >
                  {lead.customer?.display_name || "Unknown"}
                </TableCell>
                <TableCell>
                  <div className="flex flex-col text-sm text-slate-600 gap-0.5">
                    {lead.customer?.primary_phone && (
                      <span className="flex items-center gap-1.5"><MessageCircle className="w-3 h-3 text-slate-400" />{lead.customer.primary_phone}</span>
                    )}
                    {lead.customer?.email && (
                      <span className="flex items-center gap-1.5"><Mail className="w-3 h-3 text-slate-400" />{lead.customer.email}</span>
                    )}
                    {!lead.customer?.primary_phone && !lead.customer?.email && (
                      <span className="text-slate-400 italic">No contact</span>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  <SourceBadge source={lead.source_channel} />
                </TableCell>
                <TableCell>
                  <StatusBadge status={lead.status} />
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1.5">
                    <User className="h-4 w-4 text-slate-400" />
                    <span className="text-sm text-slate-600">
                      {lead.assigned_staff?.full_name || "Unassigned"}
                    </span>
                  </div>
                </TableCell>
                <TableCell className="text-slate-500 text-sm whitespace-nowrap">
                  {formatDistanceToNow(new Date(lead.updated_at), { addSuffix: true })}
                </TableCell>
                <TableCell className="text-slate-500 text-sm whitespace-nowrap">
                  {format(new Date(lead.created_at), "MMM d, yyyy")}
                </TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" className="h-8 w-8 p-0">
                        <span className="sr-only">Open menu</span>
                        <MoreHorizontal className="h-4 w-4" />
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
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      {/* Mobile Stacked View */}
      <div className="md:hidden flex flex-col gap-3">
        {leads.map((lead) => (
          <div key={lead.id} className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm relative">
            <div className="flex justify-between items-start mb-2">
              <div
                className="font-medium text-slate-900 text-base cursor-pointer hover:text-blue-600"
                onClick={() => navigate(`/app/leads/${lead.id}`)}
              >
                {lead.customer?.display_name || "Unknown"}
              </div>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="h-8 w-8 p-0 -mr-2 -mt-1">
                    <span className="sr-only">Open menu</span>
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
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

            <div className="flex flex-wrap gap-2 mb-3">
              <StatusBadge status={lead.status} />
              <SourceBadge source={lead.source_channel} />
            </div>

            <div className="flex flex-col gap-1.5 text-sm text-slate-600">
              {lead.customer?.primary_phone && (
                <div className="flex items-center gap-2">
                  <MessageCircle className="w-3.5 h-3.5 text-slate-400" />
                  <span>{lead.customer.primary_phone}</span>
                </div>
              )}
              {lead.customer?.email && (
                <div className="flex items-center gap-2">
                  <Mail className="w-3.5 h-3.5 text-slate-400" />
                  <span className="truncate">{lead.customer.email}</span>
                </div>
              )}
              <div className="flex items-center gap-2 mt-1 pt-2 border-t border-slate-100">
                <User className="w-3.5 h-3.5 text-slate-400" />
                <span className="text-xs">{lead.assigned_staff?.full_name || "Unassigned"}</span>
                <span className="text-slate-300 mx-1">•</span>
                <span className="text-xs text-slate-400">{formatDistanceToNow(new Date(lead.updated_at), { addSuffix: true })}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Status Dialog */}
      <Dialog open={statusDialogOpen} onOpenChange={setStatusDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Change Status</DialogTitle>
            <DialogDescription>
              Update the sales stage for this lead.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger>
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
          <DialogFooter>
            <Button variant="outline" onClick={() => setStatusDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleStatusChange} disabled={updateStatus.isPending}>Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign Dialog */}
      <Dialog open={assignDialogOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Assign Lead</DialogTitle>
            <DialogDescription>
              Select a team member to handle this lead.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <Select value={selectedStaff} onValueChange={setSelectedStaff}>
              <SelectTrigger>
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
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssignDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleAssign} disabled={assignLead.isPending}>Assign</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
