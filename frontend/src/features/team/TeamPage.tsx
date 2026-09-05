import { useState, useMemo } from "react";
import { 
  useTeamMembers, 
  useInvitations, 
  useUpdateTeamMember, 
  useRemoveTeamMember, 
  useInviteMember, 
  useRevokeInvitation 
} from "@/api/team.queries";
import { useAuth } from "@/contexts/AuthContext";
import { format } from "date-fns";
import { toast } from "sonner";
import { 
  UserPlus, 
  ShieldAlert, 
  MoreVertical,
  CheckCircle2,
  XCircle,
  Mail,
  UserCog
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger, DropdownMenuSeparator } from "@/components/ui/dropdown-menu";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";
import { EmptyState } from "@/components/common/states/EmptyState";

function getRoleBadgeColor(role: string) {
  switch (role) {
    case "OWNER": return "bg-purple-100 text-purple-800 border-purple-200";
    case "ADMIN": return "bg-blue-100 text-blue-800 border-blue-200";
    default: return "bg-slate-100 text-slate-800 border-slate-200";
  }
}

export default function TeamPage() {
  const { user } = useAuth();
  const { data: members = [], isLoading: membersLoading, error: membersError, refetch: refetchMembers } = useTeamMembers();
  const { data: invitations = [], isLoading: invitationsLoading, error: invitationsError, refetch: refetchInvitations } = useInvitations();
  
  const updateMember = useUpdateTeamMember();
  const removeMember = useRemoveTeamMember();
  const revokeInvite = useRevokeInvitation();
  
  const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("MEMBER");
  const inviteMemberMutation = useInviteMember();

  // Find the current user's membership to determine their actual role
  const currentUserMembership = useMemo(() => {
    return members.find((m: any) => m.user.email === user?.email);
  }, [members, user]);

  const isAuthorized = currentUserMembership?.role === "OWNER" || currentUserMembership?.role === "ADMIN";

  const handleInvite = async () => {
    if (!inviteEmail.trim()) return;
    try {
      await inviteMemberMutation.mutateAsync({ email: inviteEmail, role: inviteRole });
      toast.success("Invitation accepted by the mail server");
      setIsInviteModalOpen(false);
      setInviteEmail("");
      setInviteRole("MEMBER");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to send invitation");
    }
  };

  const handleChangeRole = async (memberId: string, newRole: string) => {
    if (!window.confirm(`Are you sure you want to change this member's role to ${newRole}?`)) return;
    try {
      await updateMember.mutateAsync({ id: memberId, role: newRole });
      toast.success("Role updated successfully");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update role");
    }
  };

  const handleToggleStatus = async (member: any) => {
    const action = member.is_active ? "deactivate" : "activate";
    if (!window.confirm(`Are you sure you want to ${action} this member?`)) return;
    try {
      await updateMember.mutateAsync({ id: member.id, is_active: !member.is_active });
      toast.success(`Member ${action}d successfully`);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || `Failed to ${action} member`);
    }
  };

  const handleRemove = async (memberId: string) => {
    if (!window.confirm("Are you sure you want to remove this member from the organization? This action cannot be undone.")) return;
    try {
      await removeMember.mutateAsync(memberId);
      toast.success("Member removed successfully");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to remove member");
    }
  };

  const handleRevokeInvite = async (inviteId: string) => {
    if (!window.confirm("Are you sure you want to revoke this invitation?")) return;
    try {
      await revokeInvite.mutateAsync(inviteId);
      toast.success("Invitation revoked");
    } catch (err) {
      toast.error("Failed to revoke invitation");
    }
  };

  if (membersLoading || invitationsLoading) {
    return <LoadingSkeleton rows={5} />;
  }

  if (membersError || invitationsError) {
    return (
      <ErrorState 
        code="internal_server_error" 
        title="Failed to load team data" 
        message="There was an error loading the team members or invitations. Please try again."
        onRetry={() => {
          refetchMembers();
          refetchInvitations();
        }}
      />
    );
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-8 md:px-8">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Team Management</h1>
          <p className="text-sm text-slate-500 mt-1">Manage organization members, roles, and invitations.</p>
        </div>
        {isAuthorized && (
          <Button onClick={() => setIsInviteModalOpen(true)} className="gap-2">
            <UserPlus className="h-4 w-4" />
            Invite Member
          </Button>
        )}
      </div>

      <Tabs defaultValue="members" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="members">Active Members ({members.length})</TabsTrigger>
          <TabsTrigger value="invitations">Pending Invitations ({invitations.filter((i: any) => i.status === 'PENDING').length})</TabsTrigger>
        </TabsList>

        <TabsContent value="members" className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            {members.length === 0 ? (
              <EmptyState 
                icon={<UserCog className="h-6 w-6" />}
                title="No members found"
                description="Your organization has no active members."
                action={isAuthorized ? { label: "Invite Member", onClick: () => setIsInviteModalOpen(true) } : undefined}
              />
            ) : (
              <>
                <div className="hidden md:grid grid-cols-12 gap-4 p-4 text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50 border-b border-slate-100">
                  <div className="col-span-4">Member</div>
                  <div className="col-span-2">Role</div>
                  <div className="col-span-2 text-center">Status</div>
                  <div className="col-span-3">Joined</div>
                  <div className="col-span-1 text-right">Actions</div>
                </div>
                <div className="divide-y divide-slate-100">
                  {members.map((member: any) => {
                    const canManage = isAuthorized && member.role !== "OWNER" && member.user.email !== user?.email;
                    return (
                      <div key={member.id} className="flex flex-col md:grid md:grid-cols-12 gap-3 md:gap-4 p-4 items-start md:items-center hover:bg-slate-50/50 transition-colors relative">
                        {/* Member Info */}
                        <div className="col-span-4 flex items-center gap-3 w-full pr-8 md:pr-0">
                          <div className="h-9 w-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-600 font-semibold shrink-0">
                            {member.user.full_name?.charAt(0) || member.user.email.charAt(0).toUpperCase()}
                          </div>
                          <div className="flex flex-col min-w-0 flex-1">
                            <span className="font-medium text-slate-900 truncate">
                              {member.user.full_name || "No Name"}
                              {member.user.email === user?.email && " (You)"}
                            </span>
                            <span className="text-xs text-slate-500 truncate">{member.user.email}</span>
                          </div>
                        </div>
                        
                        {/* Mobile Action Dropdown (Absolute Top Right) */}
                        <div className="absolute right-4 top-4 md:hidden">
                          {canManage ? (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreVertical className="h-4 w-4 text-slate-500" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {member.role === "MEMBER" && (
                                  <DropdownMenuItem onClick={() => handleChangeRole(member.id, "ADMIN")}>
                                    Make Admin
                                  </DropdownMenuItem>
                                )}
                                {member.role === "ADMIN" && (
                                  <DropdownMenuItem onClick={() => handleChangeRole(member.id, "MEMBER")}>
                                    Make Member
                                  </DropdownMenuItem>
                                )}
                                <DropdownMenuItem onClick={() => handleToggleStatus(member)}>
                                  {member.is_active ? "Deactivate" : "Activate"}
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => handleRemove(member.id)} className="text-red-600 focus:text-red-600 focus:bg-red-50">
                                  Remove Member
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          ) : (
                            <div className="h-8 w-8" />
                          )}
                        </div>
                        
                        {/* Role & Status (Mobile row) */}
                        <div className="flex items-center gap-2 md:contents w-full">
                          <div className="col-span-2 flex items-center">
                            <Badge variant="outline" className={getRoleBadgeColor(member.role)}>
                              {member.role}
                            </Badge>
                          </div>

                          <div className="col-span-2 flex justify-center items-center">
                            {member.is_active ? (
                              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200"><CheckCircle2 className="w-3 h-3 mr-1" /> Active</Badge>
                            ) : (
                              <Badge variant="outline" className="bg-slate-50 text-slate-500 border-slate-200"><XCircle className="w-3 h-3 mr-1" /> Inactive</Badge>
                            )}
                          </div>
                          
                          {/* Mobile Joined Date */}
                          <div className="md:hidden text-xs text-slate-400 ml-auto pt-0.5">
                             {format(new Date(member.created_at), "MMM d, yy")}
                          </div>
                        </div>

                        {/* Desktop Joined Date */}
                        <div className="col-span-3 hidden md:block text-sm text-slate-500">
                          {format(new Date(member.created_at), "MMM d, yyyy")}
                        </div>

                        {/* Desktop Actions */}
                        <div className="col-span-1 hidden md:flex justify-end">
                          {canManage ? (
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreVertical className="h-4 w-4 text-slate-500" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {member.role === "MEMBER" && (
                                  <DropdownMenuItem onClick={() => handleChangeRole(member.id, "ADMIN")}>
                                    Make Admin
                                  </DropdownMenuItem>
                                )}
                                {member.role === "ADMIN" && (
                                  <DropdownMenuItem onClick={() => handleChangeRole(member.id, "MEMBER")}>
                                    Make Member
                                  </DropdownMenuItem>
                                )}
                                <DropdownMenuItem onClick={() => handleToggleStatus(member)}>
                                  {member.is_active ? "Deactivate" : "Activate"}
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onClick={() => handleRemove(member.id)} className="text-red-600 focus:text-red-600 focus:bg-red-50">
                                  Remove Member
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          ) : (
                            <div className="h-8 w-8" />
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
            </>
            )}
          </div>
        </TabsContent>

        <TabsContent value="invitations" className="space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
            {invitations.length === 0 ? (
              <EmptyState 
                icon={<Mail className="h-6 w-6" />}
                title="No pending invitations"
                description="Invite team members to collaborate in V4 Studio."
                action={isAuthorized ? { label: "Invite Team Member", onClick: () => setIsInviteModalOpen(true) } : undefined}
              />
            ) : (
              <div className="divide-y divide-slate-100">
                <div className="grid grid-cols-12 gap-4 p-4 text-xs font-semibold text-slate-500 uppercase tracking-wider bg-slate-50/50 border-b border-slate-100">
                  <div className="col-span-5">Email</div>
                  <div className="col-span-2">Role</div>
                  <div className="col-span-2">Status</div>
                  <div className="col-span-2 hidden md:block">Invited By</div>
                  <div className="col-span-3 md:col-span-1 text-right">Actions</div>
                </div>
                {invitations.map((invite: any) => (
                  <div key={invite.id} className="grid grid-cols-12 gap-4 p-4 items-center hover:bg-slate-50/50 transition-colors">
                    <div className="col-span-5 font-medium text-sm text-slate-900 truncate">
                      {invite.email}
                    </div>
                    <div className="col-span-2">
                      <Badge variant="outline" className={getRoleBadgeColor(invite.role)}>
                        {invite.role}
                      </Badge>
                    </div>
                    <div className="col-span-2">
                      <Badge variant="secondary" className="bg-amber-100 text-amber-800">{invite.status}</Badge>
                    </div>
                    <div className="col-span-2 hidden md:block text-sm text-slate-500 truncate">
                      {invite.invited_by?.full_name || invite.invited_by?.email || "Unknown"}
                    </div>
                    <div className="col-span-3 md:col-span-1 flex justify-end">
                      {isAuthorized && invite.status === "PENDING" && (
                        <Button 
                          variant="ghost" 
                          size="sm" 
                          onClick={() => handleRevokeInvite(invite.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 text-xs"
                        >
                          Revoke
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>

      {/* Invite Modal */}
      <Dialog open={isInviteModalOpen} onOpenChange={setIsInviteModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite Team Member</DialogTitle>
            <DialogDescription>
              They will receive an email with instructions to join your organization.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4 py-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-slate-700">Email Address</label>
              <Input
                type="email"
                placeholder="colleague@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium text-slate-700">Role</label>
              <Select value={inviteRole} onValueChange={setInviteRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="MEMBER">Member (Standard Access)</SelectItem>
                  <SelectItem value="ADMIN">Admin (Full Access)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {inviteRole === "ADMIN" && (
              <div className="bg-blue-50 border border-blue-100 p-3 rounded-md flex gap-2 items-start text-sm text-blue-800">
                <ShieldAlert className="w-4 h-4 mt-0.5 shrink-0" />
                <p>Admins can modify organization settings, billing, and manage other team members (except Owners).</p>
              </div>
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsInviteModalOpen(false)}>Cancel</Button>
            <Button onClick={handleInvite} disabled={!inviteEmail.trim() || inviteMemberMutation.isPending}>
              {inviteMemberMutation.isPending ? "Sending..." : "Send Invitation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
