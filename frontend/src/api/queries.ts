import { useQuery } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface AnalyticsSummary {
  date_range: { preset: string; start: string; end: string };
  leads: {
    total_leads: number;
    new_leads_today: number;
    instagram_leads: number;
    whatsapp_leads: number;
    qualified_leads: number;
    booking_links_sent: number;
    converted_leads: number;
    lead_to_booking_conversion_rate: number;
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
  lead_source_breakdown: Array<{
    source_channel: string;
    total_leads: number;
    share_percentage: number;
    qualified_leads: number;
    converted_leads: number;
    conversion_rate_percentage: number;
  }>;
  popular_services: Array<{
    service_id: string;
    service_name: string;
    service_slug: string;
    booking_count: number;
    completed_count: number;
    share_percentage: number;
    estimated_revenue: number;
  }>;
}

export function useDashboardSummary(preset = "this_month") {
  return useQuery({
    queryKey: ["dashboard", "summary", preset],
    queryFn: async () => {
      const { data } = await apiClient.get<AnalyticsSummary>(`/analytics/dashboard/?preset=${preset}`);
      return data;
    },
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
  });
}