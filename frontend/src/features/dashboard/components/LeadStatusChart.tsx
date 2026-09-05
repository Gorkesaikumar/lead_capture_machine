import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, CartesianGrid } from "recharts";

export function LeadStatusChart({ leadsMetrics }: { leadsMetrics: any }) {
  if (!leadsMetrics) return null;

  const actualChartData = [
    { name: 'New', count: leadsMetrics.status_new || 0, color: '#3b82f6' }, // blue
    { name: 'Contacted', count: leadsMetrics.status_contacted || 0, color: '#f59e0b' }, // amber
    { name: 'Qualified', count: leadsMetrics.status_qualified || 0, color: '#8b5cf6' }, // purple
    { name: 'Converted', count: leadsMetrics.converted_leads || 0, color: '#10b981' }, // emerald
    { name: 'Lost', count: leadsMetrics.status_lost || 0, color: '#ef4444' }, // red
  ];

  return (
    <Card className="border-gray-200 shadow-none">
      <CardHeader className="pb-2 border-b border-gray-100">
        <CardTitle className="text-base font-semibold text-slate-900">Lead Status</CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={actualChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
              <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
              <Tooltip 
                cursor={{ fill: '#f8fafc' }} 
                contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }} 
              />
              <Bar dataKey="count" name="Leads" radius={[4, 4, 0, 0]} barSize={32}>
                {actualChartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}
