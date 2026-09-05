import { Badge } from "@/components/ui/badge";

type StatusType = "pending" | "confirmed" | "completed" | "cancelled" | "new" | "contacted" | "qualified" | "converted" | "lost";

const statusConfig: Record<StatusType, { label: string; className: string }> = {
  // Booking Statuses
  pending: { label: "Pending", className: "bg-amber-100 text-amber-800 hover:bg-amber-100/80 border-transparent font-medium" },
  confirmed: { label: "Confirmed", className: "bg-blue-100 text-blue-800 hover:bg-blue-100/80 border-transparent font-medium" },
  completed: { label: "Completed", className: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100/80 border-transparent font-medium" },
  cancelled: { label: "Cancelled", className: "bg-rose-100 text-rose-800 hover:bg-rose-100/80 border-transparent font-medium" },

  // Lead Statuses
  new: { label: "New", className: "bg-purple-100 text-purple-800 hover:bg-purple-100/80 border-transparent font-medium" },
  contacted: { label: "Contacted", className: "bg-blue-100 text-blue-800 hover:bg-blue-100/80 border-transparent font-medium" },
  qualified: { label: "Qualified", className: "bg-cyan-100 text-cyan-800 hover:bg-cyan-100/80 border-transparent font-medium" },
  converted: { label: "Converted", className: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100/80 border-transparent font-medium" },
  lost: { label: "Lost", className: "bg-slate-100 text-slate-600 hover:bg-slate-100/80 border-transparent font-medium" },
};

export function StatusBadge({ status }: { status: StatusType | string }) {
  const normalizedStatus = (status || "pending").toLowerCase() as StatusType;
  const config = statusConfig[normalizedStatus] || { label: status, className: "bg-gray-100 text-gray-800 border-transparent font-medium" };
  return <Badge variant="outline" className={config.className}>{config.label}</Badge>;
}
