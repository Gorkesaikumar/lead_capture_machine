import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface KpiCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  trend?: {
    value: string;
    isPositive: boolean;
  };
}

export function KpiCard({ title, value, icon: Icon, trend }: KpiCardProps) {
  return (
    <Card className="shadow-none border-gray-200 bg-white">
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-sm font-medium text-slate-500">{title}</p>
            <p className="text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
          </div>
          <div className="p-3 bg-slate-50 rounded-full">
            <Icon className="h-5 w-5 text-slate-700" />
          </div>
        </div>
        {trend && (
          <div className="mt-4 flex items-center gap-2 text-sm">
            <span className={cn("font-medium", trend.isPositive ? "text-emerald-600" : "text-rose-600")}>
              {trend.isPositive ? "+" : "-"}{trend.value}
            </span>
            <span className="text-slate-500">from last month</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
