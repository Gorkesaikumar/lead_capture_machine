import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useLeadsList(params: Record<string, string>) {
  return useQuery({
    queryKey: ["leads", "list", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value);
      });
      const { data } = await apiClient.get(`/leads/?${searchParams.toString()}`);
      return data; // assumes { count: number, results: any[] }
    },
    // Keep previous data when fetching new pages for smoother UX
    placeholderData: (previousData) => previousData,
  });
}

export function useLeadDetail(id: string) {
  return useQuery({
    queryKey: ["leads", "detail", id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/leads/${id}/`);
      return data;
    },
    enabled: !!id,
  });
}

export function useUpdateLeadStatus() {
  return useMutation({
    mutationFn: async ({ id, status, notes }: { id: string; status: string; notes?: string }) => {
      const { data } = await apiClient.post(`/leads/${id}/status/`, { status, notes });
      return data;
    },
  });
}

export function useAssignLead() {
  return useMutation({
    mutationFn: async ({ id, staff_id }: { id: string; staff_id: string | null }) => {
      const { data } = await apiClient.post(`/leads/${id}/assign/`, { staff_id });
      return data;
    },
  });
}

export function useDeleteLead() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.delete(`/leads/${id}/`);
      return data;
    },
  });
}


export function useLeadTriggers() {
  return useQuery({
    queryKey: ["lead-triggers"],
    queryFn: async () => {
      const { data } = await apiClient.get("/leads/triggers/");
      return data.results || data;
    },
  });
}

export function useCreateLeadTrigger() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/leads/triggers/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead-triggers"] });
    },
  });
}

export function useUpdateLeadTrigger() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: any) => {
      const { data } = await apiClient.patch(`/leads/triggers/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead-triggers"] });
    },
  });
}

export function useDeleteLeadTrigger() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/leads/triggers/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead-triggers"] });
    },
  });
}


// =======================
// LEAD FORMS
// =======================

export function useLeadForms() {
  return useQuery({
    queryKey: ["lead-forms"],
    queryFn: async () => {
      const { data } = await apiClient.get("/leads/forms/");
      return data.results || data;
    },
  });
}

export function useCreateLeadForm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/leads/forms/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead-forms"] });
    },
  });
}

export function useUpdateLeadForm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: any) => {
      const { data } = await apiClient.patch(`/leads/forms/${id}/`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead-forms"] });
    },
  });
}

export function useDeleteLeadForm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/leads/forms/${id}/`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["lead-forms"] });
    },
  });
}
