import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface IntegrationHealthData {
  platform: string;
  diagnostic?: string;
  required_permissions?: string[];
  connection_status: "CONNECTED" | "DISCONNECTED" | "ERROR" | "CONFIGURED_UNVERIFIED" | "CONFIGURATION_REQUIRED" | "TOKEN_EXPIRED" | "PERMISSION_REQUIRED";
  webhook_status: "ACTIVE" | "UNKNOWN" | "INACTIVE";
  last_event_time: string | null;
  last_successful_communication: string | null;
  requires_reconnect: boolean;
  last_event_id: string | null;
  last_processing_result: string | null;
  last_error: string | null;
  events_received_count: number;
  real_message_events_count: number;
  test_events_count: number;
  username?: string;
  name?: string;
  profile_picture_url?: string;
  display_phone_number?: string;
  business_name?: string;
  connected_at?: string;
  last_verified_at?: string;
  verified_name?: string;
}

export interface IntegrationHealthResponse {
  instagram: IntegrationHealthData;
  whatsapp: IntegrationHealthData;
}

export function useIntegrationHealth() {
  return useQuery({
    queryKey: ["integrations", "health"],
    queryFn: async (): Promise<IntegrationHealthResponse> => {
      const { data } = await apiClient.get("/integrations/status/");
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useDisconnectInstagram() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/integrations/oauth/instagram/disconnect/");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations", "health"] });
    },
  });
}

export function useInstagramAuthUrl() {
  return useQuery({
    queryKey: ["integrations", "instagram-auth-url"],
    queryFn: async () => {
      const { data } = await apiClient.get("/integrations/instagram/connect/");
      return data as { url: string };
    },
    enabled: false, // Don't fetch automatically
  });
}

export function useWhatsAppAuthUrl() {
  return useQuery({
    queryKey: ["integrations", "whatsapp-auth-url"],
    queryFn: async () => {
      const { data } = await apiClient.get("/integrations/whatsapp/connect/");
      return data as { app_id: string; config_id: string; graph_version: string; state: string; expires_in: number };
    },
    enabled: false, // Don't fetch automatically
  });
}

export function useDisconnectWhatsApp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post("/integrations/oauth/whatsapp/disconnect/");
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations", "health"] });
    },
  });
}
