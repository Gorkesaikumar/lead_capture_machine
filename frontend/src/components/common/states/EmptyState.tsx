import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Ghost } from "lucide-react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center border border-dashed border-gray-200 rounded-lg bg-slate-50/50 min-h-[300px]">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500 mb-4">
        {icon || <Ghost className="h-6 w-6" />}
      </div>
      <h3 className="text-lg font-medium text-slate-900">{title}</h3>
      <p className="text-sm text-slate-500 mt-1 max-w-sm">{description}</p>
      {action && (
        <Button onClick={action.onClick} className="mt-6" variant="outline">
          {action.label}
        </Button>
      )}
    </div>
  );
}
