import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/states/EmptyState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { Calendar } from "lucide-react";

export function TodaySchedule({ bookings, isLoading }: { bookings: any[]; isLoading: boolean }) {
  if (isLoading) return <Card className="border-gray-200 shadow-none"><CardContent className="p-6"><LoadingSkeleton rows={3}/></CardContent></Card>;

  if (!bookings || bookings.length === 0) {
    return (
      <Card className="border-gray-200 shadow-none">
        <CardContent className="p-0">
          <EmptyState icon={<Calendar className="h-6 w-6"/>} title="No shoots today" description="Your schedule is clear for today." />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-gray-200 shadow-none">
      <CardHeader className="pb-3 border-b border-gray-100">
        <CardTitle className="text-base font-semibold text-slate-900">Upcoming Schedule</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-gray-100">
          {bookings.map((booking: any) => {
            const time = new Date(booking.starts_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            return (
              <div key={booking.id} className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors">
                <div className="flex flex-col">
                  <span className="font-medium text-slate-900">{booking.customer?.display_name || "Unknown Customer"}</span>
                  <span className="text-sm text-slate-500">{time} • {booking.service?.name}</span>
                </div>
                <div>
                  <StatusBadge status={booking.status?.toLowerCase() || 'pending'} />
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}