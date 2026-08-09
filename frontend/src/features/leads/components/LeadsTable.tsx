import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { StatusBadge } from "@/components/common/ui/StatusBadge";
import { Button } from "@/components/ui/button";
import { formatDistanceToNow } from "date-fns";
import { ChevronRight } from "lucide-react";
import { useNavigate } from "react-router-dom";

export function LeadsTable({ leads }: { leads: any[] }) {
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto shadow-sm w-full block">
      <Table>
        <TableHeader className="bg-slate-50 border-b border-gray-200">
          <TableRow>
            <TableHead className="font-semibold text-slate-700">Customer</TableHead>
            <TableHead className="font-semibold text-slate-700">Source</TableHead>
            <TableHead className="font-semibold text-slate-700">Requirement</TableHead>
            <TableHead className="font-semibold text-slate-700">Status</TableHead>
            <TableHead className="font-semibold text-slate-700">Received</TableHead>
            <TableHead className="text-right font-semibold text-slate-700">Action</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {leads.map((lead) => (
            <TableRow 
              key={lead.id} 
              className="hover:bg-slate-50 cursor-pointer transition-colors"
              onClick={() => navigate(`/leads/${lead.id}`)}
            >
              <TableCell className="py-4">
                <div className="flex flex-col">
                  <span className="font-medium text-slate-900">{lead.customer?.display_name || "Unknown"}</span>
                  <span className="text-xs text-slate-500">{lead.customer?.primary_phone || lead.customer?.email}</span>
                </div>
              </TableCell>
              <TableCell>
                <SourceBadge source={lead.source_channel} />
              </TableCell>
              <TableCell className="text-slate-600 max-w-[200px] truncate" title={lead.trigger_service_name || lead.trigger_phrase || lead.service?.name || lead.summary}>
                {lead.trigger_service_name || lead.trigger_phrase || lead.service?.name || lead.summary || "General Inquiry"}
              </TableCell>
              <TableCell>
                <StatusBadge status={lead.status} />
              </TableCell>
              <TableCell className="text-slate-500 text-sm whitespace-nowrap">
                {formatDistanceToNow(new Date(lead.created_at), { addSuffix: true })}
              </TableCell>
              <TableCell className="text-right">
                <Button variant="ghost" size="icon" className="h-8 w-8 text-slate-400 hover:text-slate-600">
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
