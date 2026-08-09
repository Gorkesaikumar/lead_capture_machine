import { useState } from "react";
import { format } from "date-fns";
import { useBookings } from "@/api/bookings.queries";
import { useServicesList } from "@/api/services.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Search, CalendarX } from "lucide-react";
import { BookingDetailSheet } from "@/features/calendar/components/BookingDetailSheet";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { EmptyState } from "@/components/common/states/EmptyState";

export default function BookingsList() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<string>("all");
  const [service, setService] = useState<string>("all");

  const queryParams: Record<string, string> = {};
  if (search) queryParams.search = search;
  if (status !== "all") queryParams.status = status;
  if (service !== "all") queryParams.service = service;

  const { data: bookings, isLoading } = useBookings(queryParams);
  const { data: services } = useServicesList();
  
  const [selectedBooking, setSelectedBooking] = useState<any>(null);

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONFIRMED": return <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Confirmed</Badge>;
      case "PENDING": return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">Pending</Badge>;
      case "COMPLETED": return <Badge variant="outline" className="bg-slate-100 text-slate-600 border-slate-200">Completed</Badge>;
      case "CANCELLED": return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">Cancelled</Badge>;
      case "NO_SHOW": return <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">No Show</Badge>;
      default: return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <PageContainer>
      <PageHeader 
        title="All Bookings"
        description="View and manage all customer appointments."
      />

      <div className="mt-6 space-y-4">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 items-center bg-white p-4 rounded-lg border shadow-sm">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <Input 
              placeholder="Search customers or notes..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 h-10"
            />
          </div>
          
          <div className="w-full sm:w-48">
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="h-10 bg-white">
                <SelectValue placeholder="All Statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="CONFIRMED">Confirmed</SelectItem>
                <SelectItem value="PENDING">Pending</SelectItem>
                <SelectItem value="COMPLETED">Completed</SelectItem>
                <SelectItem value="CANCELLED">Cancelled</SelectItem>
                <SelectItem value="NO_SHOW">No Show</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="w-full sm:w-48">
            <Select value={service} onValueChange={setService}>
              <SelectTrigger className="h-10 bg-white">
                <SelectValue placeholder="All Services" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Services</SelectItem>
                {services?.map((s: any) => (
                  <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {(search || status !== "all" || service !== "all") && (
            <Button variant="ghost" onClick={() => { setSearch(""); setStatus("all"); setService("all"); }}>
              Clear
            </Button>
          )}
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="p-6"><LoadingSkeleton rows={5} /></div>
          ) : bookings?.length === 0 ? (
            <div className="p-6">
              <EmptyState 
                icon={<CalendarX className="h-8 w-8"/>} 
                title="No bookings found" 
                description="We couldn't find any bookings matching your criteria." 
              />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader className="bg-slate-50">
                  <TableRow>
                    <TableHead>Date / Time</TableHead>
                    <TableHead>Customer</TableHead>
                    <TableHead>Service</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Created At</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {bookings?.map((booking: any) => (
                    <TableRow 
                      key={booking.id} 
                      className="cursor-pointer hover:bg-slate-50"
                      onClick={() => setSelectedBooking(booking)}
                    >
                      <TableCell>
                        <div className="font-medium text-slate-900">{format(new Date(booking.starts_at), "MMM d, yyyy")}</div>
                        <div className="text-xs text-slate-500">{format(new Date(booking.starts_at), "h:mm a")} - {format(new Date(booking.ends_at), "h:mm a")}</div>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium text-slate-900">{booking.customer_name}</div>
                        <div className="text-xs text-slate-500">{booking.customer_phone}</div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm text-slate-900">{booking.service_name}</div>
                        {booking.package_name && <div className="text-xs text-slate-500">{booking.package_name}</div>}
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(booking.status)}
                      </TableCell>
                      <TableCell className="text-sm text-slate-500">
                        {format(new Date(booking.created_at), "MMM d, yyyy")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>
      </div>

      <BookingDetailSheet 
        booking={selectedBooking} 
        open={!!selectedBooking} 
        onOpenChange={(open) => !open && setSelectedBooking(null)} 
      />
    </PageContainer>
  );
}