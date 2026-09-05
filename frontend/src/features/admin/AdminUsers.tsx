import { ErrorState } from "@/components/common/states/ErrorState";
import { useState } from "react";
import { useAdminUsers } from "@/api/admin.queries";
import {
  Users,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
} from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import AdminUserDetailModal from "./AdminUserDetailModal";

export default function AdminUsers() {
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);

  const { data, isLoading, isError, refetch } = useAdminUsers({
    search,
    plan: planFilter,
    status: statusFilter,
    page,
  });

  const users = data?.results || [];
  const totalCount = data?.count || 0;
  const totalPages = Math.ceil(totalCount / 20) || 1;

  if (isError) return <ErrorState title="Unable to load users" message="Data is unavailable. Please retry." onRetry={refetch} />;

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            User Management <Users className="h-6 w-6 text-rose-600" />
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Search, filter, inspect workspace telemetry, and execute administrative actions.
          </p>
        </div>
      </div>

      {/* Controls & Filters */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl p-5">
        <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
          {/* Search */}
          <div className="relative w-full md:w-96">
            <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
            <Input
              placeholder="Search by name, email, or organization..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="pl-10 bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl focus:bg-white focus:border-rose-500"
            />
          </div>

          {/* Filters */}
          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-slate-400 shrink-0" />
              <select
                value={planFilter}
                onChange={(e) => {
                  setPlanFilter(e.target.value);
                  setPage(1);
                }}
                className="bg-slate-50 border border-slate-200 text-slate-900 text-xs font-semibold rounded-xl h-10 px-3 focus:bg-white focus:border-rose-500"
              >
                <option value="">All Subscription Plans</option>
                <option value="free">Free Plan</option>
                <option value="starter">Starter Plan</option>
                <option value="creator">Creator Plan</option>
                <option value="enterprise">Enterprise Plan</option>
              </select>
            </div>

            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="bg-slate-50 border border-slate-200 text-slate-900 text-xs font-semibold rounded-xl h-10 px-3 focus:bg-white focus:border-rose-500"
            >
              <option value="">All Account Statuses</option>
              <option value="active">Active Only</option>
              <option value="suspended">Suspended Only</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Users Data Table */}
      <Card className="bg-white border-slate-200/80 shadow-sm rounded-2xl overflow-hidden">
        {isLoading ? (
          <div className="py-16 text-center text-slate-500 text-sm font-medium">
            Loading user registry...
          </div>
        ) : users.length === 0 ? (
          <div className="py-16 text-center space-y-2">
            <Users className="h-10 w-10 text-slate-300 mx-auto" />
            <div className="text-sm font-bold text-slate-900">No Users Found</div>
            <p className="text-xs text-slate-500">Try adjusting your search query or filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-slate-700">
              <thead className="bg-slate-50 text-slate-500 font-extrabold uppercase tracking-wider border-b border-slate-200">
                <tr>
                  <th className="p-4">User</th>
                  <th className="p-4">Organization / Workspace</th>
                  <th className="p-4">Current Plan</th>
                  <th className="p-4">Lead Quota Usage</th>
                  <th className="p-4">Joined Date</th>
                  <th className="p-4">Status</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {users.map((user: any) => (
                  <tr key={user.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="p-4">
                      <div className="font-bold text-slate-900 text-sm flex items-center gap-2">
                        {user.full_name}
                        {user.is_superuser && (
                          <Badge className="bg-amber-50 text-amber-700 border-amber-200 text-[9px] px-1.5 py-0 font-bold">
                            Super Admin
                          </Badge>
                        )}
                      </div>
                      <div className="text-slate-500 text-xs mt-0.5">{user.email}</div>
                    </td>

                    <td className="p-4 font-semibold text-slate-900">
                      {user.organization_name}
                    </td>

                    <td className="p-4">
                      <Badge
                        className={`capitalize font-bold text-xs px-2.5 py-1 ${
                          user.subscription?.plan_code === "free"
                            ? "bg-slate-100 text-slate-700 border-slate-200"
                            : user.subscription?.plan_code === "starter"
                            ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                            : user.subscription?.plan_code === "creator"
                            ? "bg-pink-50 text-pink-700 border-pink-200"
                            : "bg-purple-50 text-purple-700 border-purple-200"
                        }`}
                      >
                        {user.subscription?.plan_name || "Free"}
                      </Badge>
                    </td>

                    <td className="p-4">
                      {user.usage ? (
                        <div className="space-y-1.5 max-w-[140px]">
                          <div className="flex justify-between text-[11px] font-bold">
                            <span className="text-slate-900">
                              {user.usage.total_used} / {user.usage.lead_limit}
                            </span>
                            <span className="text-slate-500">{user.usage.usage_percentage}%</span>
                          </div>
                          <div className="h-1.5 w-full bg-slate-100 rounded-full overflow-hidden border border-slate-200">
                            <div
                              className="h-full bg-rose-600 rounded-full"
                              style={{ width: `${Math.min(100, user.usage.usage_percentage)}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span className="text-slate-400">N/A</span>
                      )}
                    </td>

                    <td className="p-4 text-slate-500 font-medium">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>

                    <td className="p-4">
                      <Badge
                        className={`capitalize font-bold text-[10px] ${
                          user.is_active
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-rose-50 text-rose-700 border-rose-200"
                        }`}
                      >
                        {user.is_active ? "Active" : "Suspended"}
                      </Badge>
                    </td>

                    <td className="p-4 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setSelectedUserId(user.id)}
                        className="text-xs font-bold text-rose-600 hover:text-rose-700 hover:bg-rose-50 h-8 rounded-lg"
                      >
                        <Eye className="h-3.5 w-3.5 mr-1" /> View Details
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        <div className="p-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <div className="text-xs text-slate-500 font-medium">
            Showing <span className="text-slate-900 font-bold">{users.length}</span> of{" "}
            <span className="text-slate-900 font-bold">{totalCount}</span> registered users
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="bg-white border-slate-200 text-xs text-slate-900 h-8 font-semibold"
            >
              <ChevronLeft className="h-4 w-4" /> Previous
            </Button>
            <span className="text-xs text-slate-600 font-bold px-2">
              Page {page} of {totalPages}
            </span>
            <Button
              size="sm"
              variant="outline"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="bg-white border-slate-200 text-xs text-slate-900 h-8 font-semibold"
            >
              Next <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </Card>

      {/* User Details Modal */}
      <AdminUserDetailModal
        userId={selectedUserId}
        isOpen={!!selectedUserId}
        onClose={() => {
          setSelectedUserId(null);
          refetch();
        }}
      />
    </div>
  );
}
