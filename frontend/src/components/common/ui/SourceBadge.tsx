import { Badge } from "@/components/ui/badge";
import { MessageCircle, Globe, Smartphone } from "lucide-react";

type SourceType = "instagram" | "whatsapp" | "website" | "other";

const sourceConfig: Record<SourceType, { label: string; icon: any; className: string }> = {
  instagram: { label: "Instagram", icon: Smartphone, className: "bg-pink-50 text-pink-700 border-pink-200" },
  whatsapp: { label: "WhatsApp", icon: MessageCircle, className: "bg-green-50 text-green-700 border-green-200" },
  website: { label: "Website", icon: Globe, className: "bg-slate-50 text-slate-700 border-slate-200" },
  other: { label: "Other", icon: Globe, className: "bg-gray-50 text-gray-700 border-gray-200" },
};

export function SourceBadge({ source }: { source: SourceType | string }) {
  const normalizedSource = (source || "other").toLowerCase() as SourceType;
  const config = sourceConfig[normalizedSource] || sourceConfig.other;
  const Icon = config.icon;
  return (
    <Badge variant="outline" className={`gap-1.5 px-2 py-0.5 font-medium ${config.className}`}>
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  );
}