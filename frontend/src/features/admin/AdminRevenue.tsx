import { useState } from "react";
import { useAdminRevenue } from "@/api/admin.queries";
import {
  TrendingUp,
  DollarSign,
  Search,
  CreditCard,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export default function AdminRevenue() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const { data, isLoading } = useAdminRevenue({ search, status: statusFilter });

  const summary = data?.summary;
  const ledger = data?.ledger || [];

  if (isLoading) {
    return (
      <div className="py-12 text-center text-slate-500 text-sm font-medium">
        Loading Revenue Telemetry & Transaction Ledger...
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            Revenue & Payment Analytics <TrendingUp className="h-6 w-6 text-emerald-600" />
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Verified financial transactions, plan contributions, and billing ledger. Failed payments are excluded from revenue.
          </p>
        </div>
      </div>

      {/* Revenue Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Today's Revenue</span>
          <div className="text-3xl font-black text-emerald-600 mt-2">
            ${summary?.today_revenue_usd || "0.00"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1 font-medium">Verified payments collected today</p>
        </Card>

        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">This Month's Revenue</span>
          <div className="text-3xl font-black text-slate-900 mt-2">
            ${summary?.month_revenue_usd || "0.00"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1 font-medium">Current calendar month total</p>
        </Card>

        <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">All-Time Total Revenue</span>
          <div className="text-3xl font-black text-amber-600 mt-2">
            ${summary?.total_revenue_usd || "0.00"}
          </div>
          <p className="text-[11px] text-slate-500 mt-1 font-medium">Sum of all successful gateway transactions</p>
        </Card>
      </div>

      {/* Revenue Contribution by Plan */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
        <CardHeader className="p-0 pb-5 border-b border-slate-100">
          <CardTitle className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-emerald-600" /> Revenue Contribution by Tier
          </CardTitle>
          <CardDescription className="text-xs text-slate-500 mt-0.5 font-medium">
            Breakdown of collected revenue generated per subscription tier
          </CardDescription>
        </CardHeader>

        <CardContent className="p-0 pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="text-xs font-extrabold text-indigo-600 uppercase">Starter Tier ($5)</div>
              <div className="text-2xl font-black text-slate-900 mt-1">${summary?.starter_revenue_usd || "0.00"}</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="text-xs font-extrabold text-pink-600 uppercase">Creator Tier ($19)</div>
              <div className="text-2xl font-black text-slate-900 mt-1">${summary?.creator_revenue_usd || "0.00"}</div>
            </div>

            <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80">
              <div className="text-xs font-extrabold text-purple-600 uppercase">Enterprise Tier ($99)</div>
              <div className="text-2xl font-black text-slate-900 mt-1">${summary?.enterprise_revenue_usd || "0.00"}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Payment Ledger Table */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-6">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4 pb-6 border-b border-slate-100">
          <div>
            <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
              <CreditCard className="h-5 w-5 text-indigo-600" /> Transaction Ledger
            </h3>
            <p className="text-xs text-slate-500 font-medium mt-0.5">Verified provider transactions with status tracking</p>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-64">
              <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Search org or txn ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-10 bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl focus:bg-white focus:border-rose-500"
              />
            </div>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-slate-900 text-xs font-semibold rounded-xl h-10 px-3 focus:bg-white focus:border-rose-500"
            >
              <option value="">All Statuses</option>
              <option value="success">Successful</option>
              <option value="pending">Pending</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        <div className="pt-4 overflow-x-auto">
          {ledger.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500 font-medium">
              No transactions match your search or filter.
            </div>
          ) : (
            <table className="w-full text-xs text-left text-slate-700">
              <thead className="bg-slate-50 text-slate-500 font-extrabold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="p-3.5">Transaction ID</th>
                  <th className="p-3.5">Organization</th>
                  <th className="p-3.5">Plan</th>
                  <th className="p-3.5">Amount (USD)</th>
                  <th className="p-3.5">Amount (INR)</th>
                  <th className="p-3.5">Gateway</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5 text-right">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {ledger.map((tx: any) => (
                  <tr key={tx.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-3.5 font-mono text-slate-900 font-semibold">{tx.transaction_id}</td>
                    <td className="p-3.5 font-bold text-slate-900">{tx.organization_name}</td>
                    <td className="p-3.5 font-semibold text-slate-700">{tx.plan_name}</td>
                    <td className="p-3.5 font-bold text-emerald-700">${tx.amount_usd}</td>
                    <td className="p-3.5 font-semibold text-rose-600">₹{tx.amount_inr}</td>
                    <td className="p-3.5 text-slate-500 font-medium">{tx.payment_provider}</td>
                    <td className="p-3.5">
                      <Badge
                        className={`capitalize font-bold text-[10px] ${
                          tx.status === "success"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : tx.status === "failed"
                            ? "bg-rose-50 text-rose-700 border-rose-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {tx.status}
                      </Badge>
                    </td>
                    <td className="p-3.5 text-right text-slate-500 font-medium">
                      {new Date(tx.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </Card>
    </div>
  );
}
