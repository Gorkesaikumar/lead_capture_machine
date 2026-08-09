import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useCustomersList(params: Record<string, string>) {
  return useQuery({
    queryKey: ["customers", "list", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value) searchParams.append(key, value);
      });
      const { data } = await apiClient.get(`/customers/?${searchParams.toString()}`);
      return data;
    },
    placeholderData: (previousData) => previousData,
  });
}

export function useCustomerDetail(id: string) {
  return useQuery({
    queryKey: ["customers", "detail", id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/customers/${id}/`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCustomerHistory(id: string) {
  return useQuery({
    queryKey: ["customers", "history", id],
    queryFn: async () => {
      const [leadsRes, bookingsRes, convsRes] = await Promise.all([
        apiClient.get(`/customers/${id}/leads/`),
        apiClient.get(`/customers/${id}/bookings/`),
        apiClient.get(`/customers/${id}/conversations/`)
      ]);
      return {
        leads: leadsRes.data.data,
        bookings: bookingsRes.data.data,
        conversations: convsRes.data.data,
      };
    },
    enabled: !!id,
  });
}