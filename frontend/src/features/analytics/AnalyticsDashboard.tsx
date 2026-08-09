import { useState } from "react";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useDashboardSummary } from "@/api/analytics.queries";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, 
  ResponsiveContainer, Tooltip, XAxis, YAxis 
} from "recharts";
import { format, parseISO } from "date-fns";

export default function AnalyticsDashboard() {
  const [preset, setPreset] = useState("30d");
  const { data, isLoading, isError } = useDashboardSummary(preset);

  if (isLoading) {
    return (
      <PageContainer>
        <PageHeader title="Analytics" description="Key performance metrics and trends." />
        <div className="mt-6"><LoadingSkeleton rows={10} /></div>
      </PageContainer>
    );
  }

  if (isError || !data) {
    return (
      <PageContainer>
        <PageHeader title="Analytics" />
        <div className="p-12 text-center text-red-500 bg-red-50 rounded-lg mt-6">
          Failed to load analytics data.
        </div>
      </PageContainer>
    );
  }

  const { leads, bookings, lead_source_breakdown, popular_services, timeseries } = data;

  const formattedTimeseries = timeseries?.map((t: any) => ({
    ...t,
    displayDate: format(parseISO(t.date), "MMM d"),
  })) || [];

  return (
    <PageContainer>
      <PageHeader 
        title="Analytics" 
        description="Key performance metrics and business trends."
        actions={
          <Select value={preset} onValueChange={setPreset}>
            <SelectTrigger className="w-[140px] md:w-[180px] bg-white">
              <SelectValue placeholder="Select Date Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 Days</SelectItem>
              <SelectItem value="30d">Last 30 Days</SelectItem>
              <SelectItem value="all_time">All Time</SelectItem>
            </SelectContent>
          </Select>
        }
      />

      {/* Top Level KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Leads</CardDescription>
            <CardTitle className="text-3xl font-semibold">{leads.total_leads}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-500">{leads.new_leads_today} new today</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Conversion Rate</CardDescription>
            <CardTitle className="text-3xl font-semibold">{leads.lead_to_booking_conversion_rate}%</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-500">{leads.converted_leads} converted leads</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Bookings</CardDescription>
            <CardTitle className="text-3xl font-semibold">{bookings.total_bookings}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-500">{bookings.upcoming_bookings} upcoming</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Cancellation Rate</CardDescription>
            <CardTitle className="text-3xl font-semibold">
              {bookings.total_bookings > 0 ? Math.round((bookings.cancelled_bookings / bookings.total_bookings) * 100) : 0}%
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-slate-500">{bookings.cancelled_bookings} cancelled</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        {/* Bookings over time (Area Chart) */}
        <Card>
          <CardHeader>
            <CardTitle>Bookings Over Time</CardTitle>
            <CardDescription>Completed vs Cancelled booking trends</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            {formattedTimeseries.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400">No data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={formattedTimeseries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="displayDate" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  <Area type="monotone" dataKey="completed" name="Completed" stroke="#0ea5e9" fill="#bae6fd" strokeWidth={2} />
                  <Area type="monotone" dataKey="cancelled" name="Cancelled" stroke="#f43f5e" fill="#fecdd3" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Lead Source Breakdown (Bar Chart) */}
        <Card>
          <CardHeader>
            <CardTitle>Instagram vs WhatsApp Performance</CardTitle>
            <CardDescription>Volume and conversion by channel</CardDescription>
          </CardHeader>
          <CardContent className="h-[300px]">
            {lead_source_breakdown.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400">No data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={lead_source_breakdown} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="source_channel" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    cursor={{ fill: '#f1f5f9' }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="total_leads" name="Total Leads" fill="#94a3b8" radius={[4, 4, 0, 0]} barSize={40} />
                  <Bar dataKey="converted_leads" name="Converted" fill="#10b981" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Service Popularity (Horizontal Bar Chart) */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Service Popularity</CardTitle>
            <CardDescription>Top performing photography packages by booking volume</CardDescription>
          </CardHeader>
          <CardContent className="h-[350px]">
            {popular_services.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-400">No data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart 
                  layout="vertical" 
                  data={popular_services} 
                  margin={{ top: 10, right: 10, left: 20, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                  <YAxis type="category" dataKey="service_name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#334155', fontWeight: 500 }} dx={-10} />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    cursor={{ fill: '#f1f5f9' }}
                    formatter={(value: any, name: any) => [value, name === 'booking_count' ? 'Bookings' : 'Est. Revenue ($)']}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                  <Bar dataKey="booking_count" name="Bookings" fill="#6366f1" radius={[0, 4, 4, 0]} barSize={24} />
                  <Bar dataKey="estimated_revenue" name="Est. Revenue (Rs)" fill="#cbd5e1" radius={[0, 4, 4, 0]} barSize={24} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}


