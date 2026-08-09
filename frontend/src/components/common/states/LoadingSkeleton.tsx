import { Skeleton } from "@/components/ui/skeleton";

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-4 w-full p-4">
      <Skeleton className="h-8 w-1/4 bg-slate-100" />
      <div className="space-y-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="h-16 w-full bg-slate-100/50" />
        ))}
      </div>
    </div>
  );
}