import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useServicesList() {
  return useQuery({
    queryKey: ["services"],
    queryFn: async () => {
      const { data } = await apiClient.get("/services/");
      return data.results || [];
    },
  });
}

export function useCreateService() {
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/services/", payload);
      return data;
    }
  });
}

export function useUpdateService() {
  return useMutation({
    mutationFn: async ({ id, ...payload }: any) => {
      const { data } = await apiClient.patch(`/services/${id}/`, payload);
      return data;
    }
  });
}

export function useToggleServiceActive() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post(`/services/${id}/toggle-active/`);
      return data;
    }
  });
}

export function useDeleteService() {
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/services/${id}/`);
    }
  });
}

export function useCreatePackage() {
  return useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await apiClient.post("/services/packages/", payload);
      return data;
    }
  });
}

export function useUpdatePackage() {
  return useMutation({
    mutationFn: async ({ id, ...payload }: any) => {
      const { data } = await apiClient.patch(`/services/packages/${id}/`, payload);
      return data;
    }
  });
}

export function useTogglePackageActive() {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await apiClient.post(`/services/packages/${id}/toggle-active/`);
      return data;
    }
  });
}

export function useDeletePackage() {
  return useMutation({
    mutationFn: async (id: string) => {
      await apiClient.delete(`/services/packages/${id}/`);
    }
  });
}