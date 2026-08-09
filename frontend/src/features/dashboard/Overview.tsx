import { useAuth } from "@/contexts/AuthContext";
import { useDashboardSummary, useRecentLeads, useUpcomingBookings } from "@/api/queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { KpiCard } from "@/components/common/ui/KpiCard";
import { ErrorState } from "@/components/common/states/ErrorState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Users, Calendar, Clock, ArrowRight } from "lucide-react";
import { TodaySchedule } from "./components/TodaySchedule";
import { RecentLeadsFeed } from "./components/RecentLeadsFeed";
import { SourceBreakdownChart } from "./components/SourceBreakdownChart";

export default function Overview() {
  const { user } = useAuth();
  
  const { 
    data: summary, 
    isLoading: isSummaryLoading, 
    isError: isSummaryError, 
    refetch: refetchSummary 
  } = useDashboardSummary("this_month");
  
  const { data: leads, isLoading: isLeadsLoading } = useRecentLeads();
  const { data: bookings, isLoading: isBookingsLoading } = useUpcomingBookings();

  if (isSummaryError) {
    return (
      <PageContainer>
        <ErrorState 
          title="Failed to load dashboard" 
          message="We couldn't retrieve the latest operational metrics. Please check your connection."
          onRetry={refetchSummary}
        />
      </PageContainer>
    );
  }

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return "Good morning";
    if (hour < 18) return "Good afternoon";
    return "Good evening";
  };

  return (
    <PageContainer>
      <PageHeader 
        title={`${getGreeting()}, ${user?.name || 'Admin'}`}
        description="Here's what's happening at the studio today."
      />

      {isSummaryLoading || !summary ? (
        <LoadingSkeleton rows={3} />
      ) : (
        <div className="space-y-6">
          {/* Top KPIs */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard 
              title="New Leads Today" 
              value={summary.leads.new_leads_today} 
              icon={Users} 
            />
            <KpiCard 
              title="Bookings Today" 
              value={summary.bookings.bookings_today} 
              icon={Calendar} 
            />
            <KpiCard 
              title="Bookings Tomorrow" 
              value={summary.bookings.bookings_tomorrow} 
              icon={ArrowRight} 
            />
            <KpiCard 
              title="Pending Bookings" 
              value={summary.bookings.pending_bookings} 
              icon={Clock} 
            />
          </div>

          {/* Secondary Insights Strip */}
          <div className="flex flex-wrap gap-6 p-4 bg-white rounded-lg border border-gray-200">
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Instagram Leads</p>
              <p className="text-lg font-semibold text-slate-900">{summary.leads.instagram_leads}</p>
            </div>
            <div className="w-px bg-gray-200 hidden sm:block"></div>
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">WhatsApp Leads</p>
              <p className="text-lg font-semibold text-slate-900">{summary.leads.whatsapp_leads}</p>
            </div>
            <div className="w-px bg-gray-200 hidden sm:block"></div>
            <div className="space-y-1">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Conversion Rate</p>
              <p className="text-lg font-semibold text-slate-900">{summary.leads.lead_to_booking_conversion_rate}%</p>
            </div>
          </div>

          {/* Activity Panels */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2 space-y-6">
              <RecentLeadsFeed leads={leads} isLoading={isLeadsLoading} />
              <TodaySchedule bookings={bookings} isLoading={isBookingsLoading} />
            </div>
            <div className="lg:col-span-1 space-y-6">
              <SourceBreakdownChart data={summary.lead_source_breakdown} />
            </div>
          </div>
        </div>
      )}
    </PageContainer>
  );
}