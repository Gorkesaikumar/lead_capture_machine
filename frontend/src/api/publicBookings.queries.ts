import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export function usePublicBookingLink(token: string) {
  return useQuery({
    queryKey: ["public-booking-link", token],
    queryFn: async () => {
      const { data } = await apiClient.get(`/bookings/links/${token}/`);
      return data;
    },
    retry: false, // Don't retry if token is invalid
  });
}

export function usePublicAvailability(token: string, date?: string, serviceId?: string | null) {
  return useQuery({
    queryKey: ["public-availability", token, date, serviceId],
    queryFn: async () => {
      if (!date) return null;
      let url = `/bookings/links/${token}/availability/?date=${date}`;
      if (serviceId) {
        url += `&service_id=${serviceId}`;
      }
      const { data } = await apiClient.get(url);
      return data;
    },
    enabled: !!date && !!token && (serviceId !== undefined),
  });
}

export function useConfirmPublicBooking() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async (payload: { token: string; starts_at: string; customer_name: string; customer_phone: string; customer_email?: string; customer_notes?: string; service_id?: string; package_id?: string }) => {
      const { token, ...body } = payload;
      const { data } = await apiClient.post(`/bookings/links/${token}/confirm/`, body);
      return data;
    },
    onSuccess: (_, variables) => {
      // Invalidate availability for this token
      queryClient.invalidateQueries({ queryKey: ["public-availability", variables.token] });
    },
  });
}
