import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface UserSimple {
  id: string;
  email: string;
  full_name: string;
}

export interface TeamMember {
  id: string;
  user: UserSimple;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface Invitation {
  id: string;
  email: string;
  role: string;
  status: string;
  invited_by: UserSimple;
  expires_at: string;
  created_at: string;
}

export function useTeamMembers() {
  return useQuery({
    queryKey: ["team", "members"],
    queryFn: async (): Promise<TeamMember[]> => {
      const { data } = await apiClient.get("/organizations/team/");
      return data.results || data;
    },
  });
}

export function useUpdateTeamMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: { id: string; role?: string; is_active?: boolean }) => {
      const { data } = await apiClient.patch(`/organizations/team/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] });
    },
  });
}

export function useRemoveTeamMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/organizations/team/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "members"] });
    },
  });
}

export function useInvitations() {
  return useQuery({
    queryKey: ["team", "invitations"],
    queryFn: async (): Promise<Invitation[]> => {
      const { data } = await apiClient.get("/organizations/invitations/");
      return data.results || data;
    },
  });
}

export function useInviteMember() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { email: string; role: string }) => {
      const { data } = await apiClient.post("/organizations/invitations/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "invitations"] });
    },
  });
}

export function useRevokeInvitation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/organizations/invitations/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["team", "invitations"] });
    },
  });
}
