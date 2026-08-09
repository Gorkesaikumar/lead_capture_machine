import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useConversationMessages(conversationId?: string) {
  return useQuery({
    queryKey: ["conversations", conversationId, "messages"],
    queryFn: async () => {
      if (!conversationId) return [];
      const { data } = await apiClient.get(`/conversations/${conversationId}/messages/`);
      if (Array.isArray(data)) return data;
      return data.results || [];
    },
    enabled: !!conversationId,
  });
}

/**
 * Fetches a lead's conversation + all messages in a single call.
 * Real-time updates are pushed via WebSocket with a 30s background fallback.
 */
export function useLeadConversation(leadId?: string) {
  return useQuery({
    queryKey: ["leads", leadId, "conversation"],
    queryFn: async () => {
      if (!leadId) return { conversation: null, messages: [], is_window_open: true };
      const { data } = await apiClient.get(`/leads/${leadId}/conversation/`);
      return data as {
        conversation: any | null;
        messages: any[];
        is_window_open?: boolean;
        window_expires_at?: string;
        last_inbound_message_at?: string;
      };
    },
    enabled: !!leadId,
    refetchInterval: 30000, // 30s background safety fallback
  });
}

/**
 * Sends an outbound Instagram DM for a lead.
 * Returns the stored Message object on success.
 * Returns a structured error with error_code on failure.
 */
export function useSendLeadMessage(leadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ message }: { message: string }) => {
      const { data } = await apiClient.post(`/leads/${leadId}/messages/`, { message });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", leadId, "conversation"] });
      queryClient.invalidateQueries({ queryKey: ["leads", "detail", leadId] });
    },
  });
}

/**
 * Generates a booking link and sends it via Instagram DM.
 * Returns { message, booking_url, booking_link_token } on success.
 */
export function useSendLeadBookingLink(leadId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ message, service_id }: { message?: string; service_id?: string }) => {
      const payload: Record<string, string> = {};
      if (message) payload.message = message;
      if (service_id) payload.service_id = service_id;
      const { data } = await apiClient.post(`/leads/${leadId}/send-booking-link/`, payload);
      return data as { message: any; booking_url: string; booking_link_token: string };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["leads", leadId, "conversation"] });
      queryClient.invalidateQueries({ queryKey: ["leads", "detail", leadId] });
    },
  });
}