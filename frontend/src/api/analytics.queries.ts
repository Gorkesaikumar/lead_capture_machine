import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export function useDashboardSummary(preset: string = "7d", startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ["analytics", "dashboard", preset, startDate, endDate],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (preset !== "custom") {
        params.append("preset", preset);
      } else {
        if (startDate) params.append("start_date", startDate);
        if (endDate) params.append("end_date", endDate);
      }
      
      const { data } = await apiClient.get(`/analytics/dashboard/?${params.toString()}`);
      return data;
    },
  });
}
