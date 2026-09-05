import type { LucideIcon } from "lucide-react";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/utils/cn";

export interface DashboardKpiCardProps {
  title: string;
  value: string | number;
  icon: LucideIcon;
  colorScheme: "pink" | "green" | "orange" | "purple";
  trend?: {
    value: string;
    period?: string;
    isPositive?: boolean;
  };
}

const COLOR_SCHEMES = {
  pink: {
    bg: "bg-rose-50/80",
    text: "text-rose-600",
    border: "border-rose-100",
    sparkline: "#f43f5e",
  },
  green: {
    bg: "bg-emerald-50/80",
    text: "text-emerald-600",
    border: "border-emerald-100",
    sparkline: "#10b981",
  },
  orange: {
    bg: "bg-amber-50/80",
    text: "text-amber-600",
    border: "border-amber-100",
    sparkline: "#f59e0b",
  },
  purple: {
    bg: "bg-purple-50/80",
    text: "text-purple-600",
    border: "border-purple-100",
    sparkline: "#8b5cf6",
  },
};

export function DashboardKpiCard({
  title,
  value,
  icon: Icon,
  colorScheme,
  trend,
}: DashboardKpiCardProps) {
  const scheme = COLOR_SCHEMES[colorScheme];
  const isPos = trend?.isPositive !== false;

  return (
    <div className="group relative overflow-hidden rounded-2xl bg-white p-5 border border-slate-200/80 shadow-2xs hover:shadow-xs transition-all duration-200 flex flex-col justify-between">
      {/* Top Section: Icon & Sparkline */}
      <div className="flex items-start justify-between">
        <div
          className={cn(
            "p-2.5 rounded-xl border flex items-center justify-center transition-transform group-hover:scale-105",
            scheme.bg,
            scheme.text,
            scheme.border
          )}
        >
          <Icon className="h-5 w-5" />
        </div>

        {/* Embedded SVG Sparkline */}
        <div className="w-20 h-9 opacity-80 group-hover:opacity-100 transition-opacity">
          <svg viewBox="0 0 100 35" className="w-full h-full overflow-visible">
            <path
              d={
                colorScheme === "pink"
                  ? "M0,25 Q20,30 40,15 T80,10 T100,5"
                  : colorScheme === "green"
                  ? "M0,28 Q25,32 50,18 T80,8 T100,3"
                  : colorScheme === "orange"
                  ? "M0,20 Q30,35 60,15 T90,20 T100,10"
                  : "M0,30 Q20,10 40,25 T70,12 T100,5"
              }
              fill="none"
              stroke={scheme.sparkline}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          </svg>
        </div>
      </div>

      {/* Middle Section: Value & Title */}
      <div className="mt-4">
        <p className="text-xs font-semibold text-slate-500 tracking-wide">
          {title}
        </p>
        <h3 className="text-2xl font-extrabold text-slate-900 tracking-tight mt-0.5">
          {value}
        </h3>
      </div>

      {/* Bottom Section: Trend Comparison */}
      {trend && (
        <div className="mt-3 flex items-center gap-1.5 text-xs">
          <span
            className={cn(
              "inline-flex items-center gap-0.5 font-bold px-1.5 py-0.5 rounded-md text-[11px]",
              isPos
                ? "bg-emerald-50 text-emerald-600 border border-emerald-100"
                : "bg-rose-50 text-rose-600 border border-rose-100"
            )}
          >
            {isPos ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {trend.value}
          </span>
          <span className="text-slate-400 text-[11px] font-medium">
            vs {trend.period || "previous period"}
          </span>
        </div>
      )}
    </div>
  );
}
