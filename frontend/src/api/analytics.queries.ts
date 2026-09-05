import { useAuth } from "@/contexts/AuthContext";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useDashboardSummary(preset: string = "7d", startDate?: string, endDate?: string) {
  const { user } = useAuth();
  return useQuery({
    queryKey: ["analytics", "dashboard", preset, startDate, endDate, user?.workspace?.id],
    enabled: !!user?.workspace?.id,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (preset !== "custom") {
        params.append("preset", preset);
      } else {
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);
      }
      
      const { data } = await apiClient.get(`/analytics/dashboard/?${params.toString()}`);
      const metrics = ["total_leads", "new_leads_today", "converted_leads", "open_conversations", "lead_to_booking_conversion_rate"];
      const lists = ["channels", "recent_leads", "activities", "leads_timeseries"];
      if (!data?.leads || metrics.some(key => !Number.isFinite(data.leads[key]))
          || lists.some(key => !Array.isArray(data[key]))) {
        throw new Error("The dashboard response is incomplete. Please try again after the application update completes.");
      }
      return data;
    },
  });
}
