import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TodayTimeline } from "./components/TodayTimeline";
import { UpcomingBookings } from "./components/UpcomingBookings";

export default function BookingCalendar() {
  return (
    <PageContainer>
      <PageHeader 
        title="Booking Calendar"
        description="Manage today's appointments and upcoming schedule."
      />

      <div className="mt-6">
        <Tabs defaultValue="today" className="space-y-6">
          <TabsList className="bg-slate-100">
            <TabsTrigger value="today">Today</TabsTrigger>
            <TabsTrigger value="upcoming">Upcoming</TabsTrigger>
          </TabsList>

          <TabsContent value="today" className="m-0">
            <TodayTimeline />
          </TabsContent>

          <TabsContent value="upcoming" className="m-0">
            <UpcomingBookings />
          </TabsContent>
        </Tabs>
      </div>
    </PageContainer>
  );
}