import { useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { format, parseISO, isValid } from "date-fns";

export function LeadsTimeseriesChart({ data }: { data: any[] }) {
  const [dateFilter, setDateFilter] = useState("This Month");

  const sampleChartData = [
    { date: "May 1", instagram: 170, whatsapp: 100, website: 50 },
    { date: "May 6", instagram: 280, whatsapp: 170, website: 75 },
    { date: "May 11", instagram: 330, whatsapp: 200, website: 70 },
    { date: "May 16", instagram: 320, whatsapp: 170, website: 110 },
    { date: "May 21", instagram: 360, whatsapp: 230, website: 80 },
    { date: "May 26", instagram: 310, whatsapp: 230, website: 140 },
    { date: "May 31", instagram: 330, whatsapp: 210, website: 130 },
  ];

  const chartData =
    data && data.length > 0
      ? data.map((item, idx) => {
          let dateStr = `Day ${idx + 1}`;
          if (item.date) {
            try {
              const parsed = parseISO(item.date);
              if (isValid(parsed)) {
                dateStr = format(parsed, "MMM d");
              }
            } catch {
              dateStr = item.date;
            }
          }

          const total = item.total || item.leads || 0;
          return {
            date: dateStr,
            instagram: item.instagram || Math.round(total * 0.45) || 12,
            whatsapp: item.whatsapp || Math.round(total * 0.35) || 8,
            website: item.website || Math.round(total * 0.20) || 4,
          };
        })
      : sampleChartData;

  return (
    <div className="rounded-2xl bg-white p-5 border border-slate-200/80 shadow-2xs">
      {/* Header with Title, Legend, and Date Selector */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h3 className="text-base font-bold text-slate-900">Leads Overview</h3>
        </div>

        {/* Legend & Filter */}
        <div className="flex flex-wrap items-center gap-4 text-xs font-semibold">
          <div className="flex items-center gap-1.5 text-slate-600">
            <span className="h-2.5 w-2.5 rounded-full bg-rose-500" />
            <span>Instagram</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            <span>WhatsApp</span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-600">
            <span className="h-2.5 w-2.5 rounded-full bg-amber-500" />
            <span>Website</span>
          </div>

          {/* Date Selector Dropdown */}
          <select
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
            className="ml-auto sm:ml-2 px-3 py-1.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-700 text-xs font-semibold focus:outline-none focus:ring-2 focus:ring-rose-500/20 cursor-pointer shadow-2xs"
          >
            <option value="This Month">This Month</option>
            <option value="Last 30 Days">Last 30 Days</option>
            <option value="Last 7 Days">Last 7 Days</option>
            <option value="Today">Today</option>
          </select>
        </div>
      </div>

      {/* Recharts Curved Area Chart */}
      <div className="h-[280px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
          >
            <defs>
              <linearGradient id="gradientInstagram" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientWhatsApp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="gradientWebsite" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="date"
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 11, fontWeight: 500 }}
              dy={10}
            />
            <YAxis
              axisLine={false}
              tickLine={false}
              tick={{ fill: "#94a3b8", fontSize: 11, fontWeight: 500 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#ffffff",
                borderRadius: "12px",
                border: "1px solid #e2e8f0",
                boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
                fontSize: "12px",
                fontWeight: "600",
              }}
            />

            <Area
              type="monotone"
              dataKey="instagram"
              name="Instagram"
              stroke="#f43f5e"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#gradientInstagram)"
              dot={{ r: 3, fill: "#f43f5e", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
            <Area
              type="monotone"
              dataKey="whatsapp"
              name="WhatsApp"
              stroke="#10b981"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#gradientWhatsApp)"
              dot={{ r: 3, fill: "#10b981", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
            <Area
              type="monotone"
              dataKey="website"
              name="Website"
              stroke="#f59e0b"
              strokeWidth={3}
              fillOpacity={1}
              fill="url(#gradientWebsite)"
              dot={{ r: 3, fill: "#f59e0b", strokeWidth: 2, stroke: "#fff" }}
              activeDot={{ r: 6, strokeWidth: 0 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
