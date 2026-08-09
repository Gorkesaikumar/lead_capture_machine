import { useState } from "react";
import { format, isFuture, isToday } from "date-fns";
import { useBookings } from "@/api/bookings.queries";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Badge } from "@/components/ui/badge";
import { BookingDetailSheet } from "./BookingDetailSheet";

export function UpcomingBookings() {
  const { data: bookings, isLoading } = useBookings();
  const [selected, setSelected] = useState<any>(null);

  if (isLoading) return <LoadingSkeleton rows={6} />;

  const upcomingBookings = (bookings || []).filter((b: any) => {
    const d = new Date(b.starts_at);
    return isFuture(d) && !isToday(d);
  });

  // Group by date
  const grouped = upcomingBookings.reduce((acc: any, b: any) => {
    const dateStr = format(new Date(b.starts_at), "yyyy-MM-dd");
    if (!acc[dateStr]) acc[dateStr] = [];
    acc[dateStr].push(b);
    return acc;
  }, {});

  const dates = Object.keys(grouped).sort();

  return (
    <div className="space-y-6">
      {dates.length === 0 ? (
        <div className="bg-white rounded-lg border shadow-sm p-12 text-center text-slate-400">
          No upcoming bookings scheduled.
        </div>
      ) : (
        dates.map(dateStr => (
          <div key={dateStr} className="bg-white rounded-lg border shadow-sm overflow-hidden">
            <div className="bg-slate-50/80 px-4 py-2 border-b">
              <h4 className="font-semibold text-slate-800 text-sm">{format(new Date(dateStr), "EEEE, MMMM d, yyyy")}</h4>
            </div>
            <div className="divide-y divide-slate-100">
              {grouped[dateStr].map((b: any) => (
                <div 
                  key={b.id} 
                  onClick={() => setSelected(b)}
                  className="p-4 hover:bg-slate-50 cursor-pointer transition-colors flex flex-col md:flex-row md:items-center gap-4"
                >
                  <div className="w-32 shrink-0">
                    <p className="font-medium text-slate-900">{format(new Date(b.starts_at), "h:mm a")}</p>
                    <p className="text-xs text-slate-500">{format(new Date(b.ends_at), "h:mm a")}</p>
                  </div>
                  
                  <div className="flex-1">
                    <p className="font-medium text-slate-900">{b.customer_name}</p>
                    <p className="text-sm text-slate-600">{b.service_name}</p>
                  </div>

                  <div>
                    <Badge variant="outline" className={
                      b.status === "CONFIRMED" ? "bg-green-50 text-green-700 border-green-200" :
                      b.status === "PENDING" ? "bg-amber-50 text-amber-700 border-amber-200" :
                      b.status === "COMPLETED" ? "bg-slate-100 text-slate-600 border-slate-200" :
                      "bg-red-50 text-red-700 border-red-200"
                    }>{b.status}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
      <BookingDetailSheet booking={selected} open={!!selected} onOpenChange={(o) => !o && setSelected(null)} />
    </div>
  );
}