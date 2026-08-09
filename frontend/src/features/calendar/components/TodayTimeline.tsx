import { useState } from "react";
import { format, isToday } from "date-fns";
import { useBookings } from "@/api/bookings.queries";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Badge } from "@/components/ui/badge";
import { BookingDetailSheet } from "./BookingDetailSheet";

export function TodayTimeline() {
  // Pass today's date to backend or just fetch all and filter client side if backend doesn't support date exactly
  const { data: bookings, isLoading } = useBookings();
  const [selected, setSelected] = useState<any>(null);

  if (isLoading) return <LoadingSkeleton rows={4} />;

  // Filter for today's bookings.
  const todayBookings = (bookings || []).filter((b: any) => isToday(new Date(b.starts_at)));

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      <div className="p-5 border-b flex justify-between items-center bg-slate-50/50">
        <div>
          <h3 className="font-bold text-slate-900 text-lg">{format(new Date(), "EEEE, MMMM d")}</h3>
          <p className="text-sm text-slate-500">{todayBookings.length} bookings today</p>
        </div>
      </div>

      <div className="p-0">
        {todayBookings.length === 0 ? (
          <div className="p-12 text-center text-slate-400">
            No bookings scheduled for today.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {todayBookings.map((b: any) => (
              <div 
                key={b.id} 
                onClick={() => setSelected(b)}
                className="p-4 hover:bg-slate-50 cursor-pointer transition-colors flex flex-col md:flex-row md:items-center gap-4"
              >
                <div className="w-32 shrink-0">
                  <p className="font-semibold text-slate-900">{format(new Date(b.starts_at), "h:mm a")}</p>
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
        )}
      </div>

      <BookingDetailSheet booking={selected} open={!!selected} onOpenChange={(o) => !o && setSelected(null)} />
    </div>
  );
}