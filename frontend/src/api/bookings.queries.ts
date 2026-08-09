import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useBookings(params?: Record<string, string>) {
  return useQuery({
    queryKey: ["bookings", params],
    queryFn: async () => {
      const searchParams = new URLSearchParams(params || {});
      const { data } = await apiClient.get(`/bookings/?${searchParams.toString()}`);
      return data.results || [];
    },
  });
}

export function useCancelBooking() {
  return useMutation({
    mutationFn: async ({ id, reason, internal_notes }: { id: string, reason: string, internal_notes?: string }) => {
      const { data } = await apiClient.post(`/bookings/${id}/cancel/`, { reason, internal_notes });
      return data;
    },
  });
}

export function useGenerateBookingLink() {
  return useMutation({
    mutationFn: async (payload: { lead: string; service?: string }) => {
      const { data } = await apiClient.post("/bookings/links/", payload);
      return data;
    },
  });
}