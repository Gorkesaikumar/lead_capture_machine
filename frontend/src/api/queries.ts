import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface AnalyticsSummary {
  date_range: { preset: string; start: string; end: string };
  leads: {
    total_leads: number;
    new_leads_today: number;
    instagram_leads: number;
    whatsapp_leads: number;
    website_leads: number;
    open_conversations: number;
    qualified_leads: number;
    booking_links_sent: number;
    converted_leads: number;
    lead_to_booking_conversion_rate: number;
    status_new: number;
    status_contacted: number;
    status_qualified: number;
    status_lost: number;
  };
  bookings: {
    total_bookings: number;
    bookings_today: number;
    bookings_tomorrow: number;
    upcoming_bookings: number;
    completed_bookings: number;
    cancelled_bookings: number;
    confirmed_bookings: number;
    pending_bookings: number;
    no_show_bookings: number;
  };
  lead_source_breakdown?: Array<{
    source_channel: string;
    total_leads: number;
    share_percentage: number;
    qualified_leads: number;
    converted_leads: number;
    conversion_rate_percentage: number;
  }>;
  popular_services?: Array<{
    service_id: string;
    service_name: string;
    service_slug: string;
    booking_count: number;
    completed_count: number;
    share_percentage: number;
    estimated_revenue: number;
  }>;
  timeseries?: Array<{
    date: string;
    total: number;
    completed?: number;
    cancelled?: number;
  }>;
  leads_timeseries?: Array<{
    date: string;
    total: number;
    converted?: number;
    instagram?: number;
    whatsapp?: number;
    website?: number;
    other?: number;
  }>;
  channels?: Array<{
    id: string;
    name: string;
    type: "instagram" | "whatsapp" | "website";
    status: string;
    leadCount: number;
  }>;
  recent_leads?: any[];
  activities?: any[];
  generated_at?: string;
  timezone?: string;
}

export function useDashboardSummary(preset = "this_month") {
  return useQuery({
    queryKey: ["dashboard", "summary", preset],
    queryFn: async () => {
      const { data } = await apiClient.get(`/analytics/dashboard/?preset=${preset}`);
      const payload = data?.data && data?.leads ? data.data : (data?.dashboard || data);
      return {
        ...payload,
        lead_source_breakdown: Array.isArray(payload?.lead_source_breakdown) ? payload.lead_source_breakdown : [],
        popular_services: Array.isArray(payload?.popular_services) ? payload.popular_services : [],
        timeseries: Array.isArray(payload?.timeseries) ? payload.timeseries : [],
        leads_timeseries: Array.isArray(payload?.leads_timeseries) ? payload.leads_timeseries : [],
        channels: Array.isArray(payload?.channels) ? payload.channels : [],
        recent_leads: Array.isArray(payload?.recent_leads) ? payload.recent_leads : [],
        activities: Array.isArray(payload?.activities) ? payload.activities : [],
      } as AnalyticsSummary;
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    gcTime: 10 * 60 * 1000,
  });
}

export function useRecentLeads() {
  return useQuery({
    queryKey: ["leads", "recent"],
    queryFn: async () => {
      // Fetch paginated leads, limit to 5
      const { data } = await apiClient.get("/leads/?limit=5&ordering=-created_at");
      return data.results || data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useUpcomingBookings() {
  return useQuery({
    queryKey: ["bookings", "upcoming"],
    queryFn: async () => {
      // Fetch paginated bookings, limit to 5
      const { data } = await apiClient.get("/bookings/?limit=5&ordering=starts_at");
      return data.results || data;
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}