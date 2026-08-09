import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { format } from "date-fns";
import { useCancelBooking } from "@/api/bookings.queries";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";

export function BookingDetailSheet({ booking, open, onOpenChange }: { booking: any, open: boolean, onOpenChange: (o: boolean) => void }) {
  const queryClient = useQueryClient();
  const cancelBooking = useCancelBooking();
  const [isCancelling, setIsCancelling] = useState(false);

  if (!booking) return null;

  const handleCancel = async () => {
    if (!confirm("Are you sure you want to cancel this booking?")) return;
    setIsCancelling(true);
    try {
      await cancelBooking.mutateAsync({ id: booking.id, reason: "Cancelled by Admin" });
      toast.success("Booking cancelled");
      queryClient.invalidateQueries({ queryKey: ["bookings"] });
      onOpenChange(false);
    } catch {
      toast.error("Failed to cancel booking");
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="sm:max-w-[450px] overflow-y-auto">
        <SheetHeader className="mb-6">
          <div className="flex items-center justify-between">
            <SheetTitle>Booking Details</SheetTitle>
            <Badge variant="outline" className={
              booking.status === "CONFIRMED" ? "bg-green-50 text-green-700 border-green-200" :
              booking.status === "PENDING" ? "bg-amber-50 text-amber-700 border-amber-200" :
              booking.status === "COMPLETED" ? "bg-slate-100 text-slate-600 border-slate-200" :
              "bg-red-50 text-red-700 border-red-200"
            }>{booking.status}</Badge>
          </div>
          <SheetDescription>Session ID: {booking.id.substring(0,8)}</SheetDescription>
        </SheetHeader>

        <div className="space-y-6">
          <div>
            <h4 className="text-sm font-medium text-slate-500 mb-2">Customer</h4>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <p className="font-medium text-slate-900">{booking.customer_name}</p>
              <p className="text-sm text-slate-600">{booking.customer_phone}</p>
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-slate-500 mb-2">Service</h4>
            <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
              <p className="font-medium text-slate-900">{booking.service_name}</p>
              {booking.package_name && <p className="text-sm text-slate-600 mt-1">Package: {booking.package_name}</p>}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium text-slate-500 mb-2">Schedule</h4>
            <div className="bg-blue-50 p-3 rounded-lg border border-blue-100">
              <p className="text-sm text-blue-900 font-medium">
                {format(new Date(booking.starts_at), "EEEE, MMMM d, yyyy")}
              </p>
              <p className="text-lg text-blue-950 font-bold mt-1">
                {format(new Date(booking.starts_at), "h:mm a")} — {format(new Date(booking.ends_at), "h:mm a")}
              </p>
              <p className="text-xs text-blue-800 mt-2">
                Duration: {booking.duration_minutes} mins
                <br/>
                Blocked: {format(new Date(booking.blocked_starts_at), "h:mm a")} to {format(new Date(booking.blocked_ends_at), "h:mm a")} (includes buffers)
              </p>
            </div>
          </div>

          {booking.whatsapp_notification && (
            <div>
              <h4 className="text-sm font-medium text-slate-500 mb-2">WhatsApp Notification</h4>
              <div className="bg-slate-50 p-3 rounded-lg border border-slate-100 flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900">Confirmation Message</span>
                  <Badge variant="outline" className={
                    booking.whatsapp_notification.status === "SENT" || booking.whatsapp_notification.status === "DELIVERED" || booking.whatsapp_notification.status === "READ" ? "bg-green-50 text-green-700 border-green-200" :
                    booking.whatsapp_notification.status === "PENDING" ? "bg-amber-50 text-amber-700 border-amber-200" :
                    "bg-red-50 text-red-700 border-red-200"
                  }>
                    {booking.whatsapp_notification.status}
                  </Badge>
                </div>
                {booking.whatsapp_notification.status === "FAILED" && (
                  <p className="text-xs text-red-600 mt-1">
                    {booking.whatsapp_notification.error_message}
                    {booking.whatsapp_notification.is_permanent_error ? " (Permanent Error)" : ` (Retried ${booking.whatsapp_notification.retry_count} times)`}
                  </p>
                )}
              </div>
            </div>
          )}

          {booking.customer_notes && (
            <div>
              <h4 className="text-sm font-medium text-slate-500 mb-2">Customer Notes</h4>
              <p className="text-sm text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100">{booking.customer_notes}</p>
            </div>
          )}

          {booking.internal_notes && (
            <div>
              <h4 className="text-sm font-medium text-slate-500 mb-2">Internal Notes</h4>
              <p className="text-sm text-amber-700 bg-amber-50 p-3 rounded-lg border border-amber-100">{booking.internal_notes}</p>
            </div>
          )}

          <div className="pt-6 border-t mt-8">
             <Button variant="destructive" className="w-full" disabled={isCancelling || booking.status === "CANCELLED"} onClick={handleCancel}>
               {isCancelling ? "Cancelling..." : "Cancel Booking"}
             </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}