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
      
      const payload = data?.data && data?.leads ? data.data : (data?.dashboard || data);
      if (!payload || typeof payload !== "object" || !payload.leads || typeof payload.leads !== "object") {
        throw new Error("The dashboard response is invalid or incomplete. Please try again.");
      }

      return {
        ...payload,
        leads: {
          total_leads: Number(payload.leads.total_leads) || 0,
          new_leads_today: Number(payload.leads.new_leads_today) || 0,
          instagram_leads: Number(payload.leads.instagram_leads) || 0,
          whatsapp_leads: Number(payload.leads.whatsapp_leads) || 0,
          website_leads: Number(payload.leads.website_leads) || 0,
          open_conversations: Number(payload.leads.open_conversations) || 0,
          qualified_leads: Number(payload.leads.qualified_leads) || 0,
          booking_links_sent: Number(payload.leads.booking_links_sent) || 0,
          converted_leads: Number(payload.leads.converted_leads) || 0,
          lead_to_booking_conversion_rate: Number(payload.leads.lead_to_booking_conversion_rate) || 0,
          status_new: Number(payload.leads.status_new) || 0,
          status_contacted: Number(payload.leads.status_contacted) || 0,
          status_qualified: Number(payload.leads.status_qualified) || 0,
          status_lost: Number(payload.leads.status_lost) || 0,
        },
        bookings: payload.bookings && typeof payload.bookings === "object" ? {
          total_bookings: Number(payload.bookings.total_bookings) || 0,
          bookings_today: Number(payload.bookings.bookings_today) || 0,
          bookings_tomorrow: Number(payload.bookings.bookings_tomorrow) || 0,
          upcoming_bookings: Number(payload.bookings.upcoming_bookings) || 0,
          completed_bookings: Number(payload.bookings.completed_bookings) || 0,
          cancelled_bookings: Number(payload.bookings.cancelled_bookings) || 0,
          confirmed_bookings: Number(payload.bookings.confirmed_bookings) || 0,
          pending_bookings: Number(payload.bookings.pending_bookings) || 0,
          no_show_bookings: Number(payload.bookings.no_show_bookings) || 0,
        } : {
          total_bookings: 0,
          bookings_today: 0,
          bookings_tomorrow: 0,
          upcoming_bookings: 0,
          completed_bookings: 0,
          cancelled_bookings: 0,
          confirmed_bookings: 0,
          pending_bookings: 0,
          no_show_bookings: 0,
        },
        lead_source_breakdown: Array.isArray(payload.lead_source_breakdown) ? payload.lead_source_breakdown : [],
        popular_services: Array.isArray(payload.popular_services) ? payload.popular_services : [],
        timeseries: Array.isArray(payload.timeseries) ? payload.timeseries : [],
        leads_timeseries: Array.isArray(payload.leads_timeseries) ? payload.leads_timeseries : [],
        channels: Array.isArray(payload.channels) ? payload.channels : [],
        recent_leads: Array.isArray(payload.recent_leads) ? payload.recent_leads : [],
        activities: Array.isArray(payload.activities) ? payload.activities : [],
      };
    },
  });
}
