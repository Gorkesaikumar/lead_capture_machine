import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface IntegrationHealthData {
  platform: string;
  connection_status: "CONNECTED" | "DISCONNECTED";
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
}

export interface IntegrationHealthResponse {
  instagram: IntegrationHealthData;
  whatsapp: IntegrationHealthData;
}

export function useIntegrationHealth() {
  return useQuery({
    queryKey: ["integrations", "health"],
    queryFn: async (): Promise<IntegrationHealthResponse> => {
      const { data } = await apiClient.get("/integrations/health/");
      return data;
    },
    refetchInterval: 30000,
  });
}
