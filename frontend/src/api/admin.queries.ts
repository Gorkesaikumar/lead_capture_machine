import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface AdminKPIs {
  total_users: number;
  user_growth_pct: number;
  free_plan_users: number;
  free_plan_pct: number;
  starter_users: number;
  creator_users: number;
  enterprise_users: number;
  mrr_usd: string;
  total_revenue_usd: string;
  active_subscriptions: number;
  conversion_rate: number;
}

export function useAdminKPIs() {
  return useQuery<AdminKPIs>({
    queryKey: ["admin", "kpis"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/kpis/");
      return data;
    },
    refetchInterval: 30000,
  });
}

export function useAdminAnalytics(timeframe = "30d") {
  return useQuery({
    queryKey: ["admin", "analytics", timeframe],
    queryFn: async () => {
      const { data } = await apiClient.get(`/admin/analytics/?timeframe=${timeframe}`);
      return data;
    },
  });
}

export function useAdminUsers(params: { search?: string; plan?: string; status?: string; page?: number }) {
  return useQuery({
    queryKey: ["admin", "users", params],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/users/", { params });
      return data;
    },
  });
}

export function useAdminUserDetail(userId?: string) {
  return useQuery({
    queryKey: ["admin", "user-detail", userId],
    queryFn: async () => {
      if (!userId) return null;
      const { data } = await apiClient.get(`/admin/users/${userId}/`);
      return data;
    },
    enabled: !!userId,
  });
}

export function useAdminUserAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, action, ...payload }: { userId: string; action: string; [key: string]: any }) => {
      const { data } = await apiClient.post(`/admin/users/${userId}/action/`, { action, ...payload });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });
}

export function useAdminSubscriptionPlans() {
  return useQuery({
    queryKey: ["admin", "plans"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/subscriptions/plans/");
      return data;
    },
  });
}

export function useUpdateAdminPlanConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ planId, ...payload }: { planId: string; [key: string]: any }) => {
      const { data } = await apiClient.patch(`/admin/subscriptions/plans/${planId}/`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin"] });
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });
}

export function useAdminRevenue(params?: { status?: string; search?: string }) {
  return useQuery({
    queryKey: ["admin", "revenue", params],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/revenue/", { params });
      return data;
    },
  });
}

export function useAdminSystem() {
  return useQuery({
    queryKey: ["admin", "system"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/system/");
      return data;
    },
    refetchInterval: 15000,
  });
}

export function useAdminAuditLogs() {
  return useQuery({
    queryKey: ["admin", "audit-logs"],
    queryFn: async () => {
      const { data } = await apiClient.get("/admin/audit-logs/");
      return data;
    },
  });
}
