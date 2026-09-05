import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

export function SourceBreakdownChart({ data = [] }: { data?: any[] }) {
  const safeData = Array.isArray(data) ? data : [];
  if (safeData.length === 0) {
    return (
      <Card className="border-gray-200 shadow-none">
        <CardHeader className="pb-2 border-b border-gray-100">
          <CardTitle className="text-base font-semibold text-slate-900">Lead Sources</CardTitle>
        </CardHeader>
        <CardContent className="p-6 text-center text-xs text-slate-500 font-medium">
          No lead source breakdown available in this period.
        </CardContent>
      </Card>
    );
  }

  const chartData = safeData.map(item => ({
    name: item?.source_channel === 'INSTAGRAM' ? 'Instagram' : item?.source_channel === 'WHATSAPP' ? 'WhatsApp' : 'Website',
    leads: item?.total_leads || 0,
    color: item?.source_channel === 'INSTAGRAM' ? '#db2777' : item?.source_channel === 'WHATSAPP' ? '#16a34a' : '#475569'
  }));

  return (
    <Card className="border-gray-200 shadow-none">
      <CardHeader className="pb-2 border-b border-gray-100">
        <CardTitle className="text-base font-semibold text-slate-900">Lead Sources</CardTitle>
      </CardHeader>
      <CardContent className="p-6">
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
              <XAxis type="number" hide />
              <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 13 }} width={80} />
              <Tooltip cursor={{ fill: '#f8fafc' }} contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }} />
              <Bar dataKey="leads" radius={[0, 4, 4, 0]} barSize={24}>
                {chartData.map((entry, index) => (
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