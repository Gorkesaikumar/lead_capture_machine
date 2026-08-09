import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { formatDistanceToNow } from "date-fns";
import { useNavigate } from "react-router-dom";

export function CustomersTable({ customers }: { customers: any[] }) {
  const navigate = useNavigate();

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden shadow-sm">
      <Table>
        <TableHeader className="bg-slate-50 border-b border-gray-200">
          <TableRow>
            <TableHead className="font-semibold text-slate-700">Name</TableHead>
            <TableHead className="font-semibold text-slate-700">Contact</TableHead>
            <TableHead className="font-semibold text-slate-700">Channels</TableHead>
            <TableHead className="font-semibold text-slate-700 text-center">Leads</TableHead>
            <TableHead className="font-semibold text-slate-700 text-center">Bookings</TableHead>
            <TableHead className="text-right font-semibold text-slate-700">Last Activity</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {customers.map((cust) => {
            const initials = cust.display_name ? cust.display_name.substring(0, 2).toUpperCase() : "CU";
            return (
              <TableRow 
                key={cust.id} 
                className="hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => navigate(`/customers/${cust.id}`)}
              >
                <TableCell className="py-4">
                  <div className="flex items-center gap-3">
                    <Avatar className="h-8 w-8 border border-slate-100">
                      <AvatarFallback className="bg-slate-100 text-slate-600 text-xs font-semibold">{initials}</AvatarFallback>
                    </Avatar>
                    <span className="font-medium text-slate-900">{cust.display_name || "Unknown"}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex flex-col text-sm">
                    <span className="text-slate-700">{cust.primary_phone || "—"}</span>
                    <span className="text-slate-500 text-xs">{cust.email}</span>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex gap-1 flex-wrap">
                    {cust.identities?.map((id: any) => (
                      <SourceBadge key={id.id} source={id.channel} />
                    ))}
                    {(!cust.identities || cust.identities.length === 0) && <span className="text-slate-400 text-sm">—</span>}
                  </div>
                </TableCell>
                <TableCell className="text-center text-slate-600 font-medium">
                  {cust.leads_count || 0}
                </TableCell>
                <TableCell className="text-center text-slate-600 font-medium">
                  {cust.bookings_count || 0}
                </TableCell>
                <TableCell className="text-right text-slate-500 text-sm whitespace-nowrap">
                  {cust.last_seen_at ? formatDistanceToNow(new Date(cust.last_seen_at), { addSuffix: true }) : "Unknown"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}