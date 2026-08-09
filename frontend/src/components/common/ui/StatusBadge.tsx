import { Badge } from "@/components/ui/badge";

type StatusType = "pending" | "confirmed" | "completed" | "cancelled";

const statusConfig: Record<StatusType, { label: string; className: string }> = {
  pending: { label: "Pending", className: "bg-amber-100 text-amber-800 hover:bg-amber-100/80 border-transparent font-medium" },
  confirmed: { label: "Confirmed", className: "bg-blue-100 text-blue-800 hover:bg-blue-100/80 border-transparent font-medium" },
  completed: { label: "Completed", className: "bg-emerald-100 text-emerald-800 hover:bg-emerald-100/80 border-transparent font-medium" },
  cancelled: { label: "Cancelled", className: "bg-rose-100 text-rose-800 hover:bg-rose-100/80 border-transparent font-medium" },
};

export function StatusBadge({ status }: { status: StatusType | string }) {
  const normalizedStatus = (status || "pending").toLowerCase() as StatusType;
  const config = statusConfig[normalizedStatus] || statusConfig.pending;
  return <Badge variant="outline" className={config.className}>{config.label}</Badge>;
}