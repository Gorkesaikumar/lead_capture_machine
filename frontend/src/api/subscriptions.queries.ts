import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";

export interface Plan {
  id: string;
  code: "free" | "starter" | "creator" | "enterprise";
  name: string;
  description: string;
  price_usd: string;
  price_inr: string;
  price: string;
  currency: string;
  currency_symbol: string;
  billing_interval: string;
  lead_limit: number;
  max_users: number | null;
  can_use_instagram: boolean;
  can_use_whatsapp: boolean;
  can_use_website_forms: boolean;
  can_use_automations: boolean;
  automation_run_limit: number | null;
  automation_addon_available: boolean;
  can_access_analytics: boolean;
  features: string[];
  is_popular?: boolean;
}

export interface SubscriptionUsage {
  total_leads_count: number;
  instagram_lead_count: number;
  whatsapp_lead_count: number;
  website_lead_count: number;
  period_start: string;
  period_end: string;
  leads_remaining: number;
  usage_percentage: number;
}

export interface Subscription {
  billing: { test_mode: boolean; payment_available: boolean; cycles: number; plan: BillingAgreement | null; dm_automation: BillingAgreement | null };
  automation: AutomationAccess;
  id: string;
  status: "pending" | "active" | "past_due" | "cancelled" | "expired";
  billing_country: string;
  billing_currency: string;
  charged_amount: string;
  current_period_start: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  billing_provider: string;
  plan: Plan;
  usage: SubscriptionUsage;
  is_valid: boolean;
}

export interface BillingAgreement {
  id: string;
  subscription_id: string | null;
  status: string;
  plan_code: string;
  amount: string;
  currency: string;
  cancel_at_period_end: boolean;
  current_end: string | null;
  short_url: string;
  last_error: string;
  paid_count: number;
  total_count: number;
}

export interface AutomationAccess {
  entitled: boolean;
  included: boolean;
  addon_available: boolean;
  addon_price_inr: string;
  addon_currency: string;
  addon_runs: number;
  addon_start: string | null;
  addon_end: string | null;
  auto_renews: boolean;
  payment_available: boolean;
  can_manage_billing: boolean;
  run_limit: number | null;
  runs_used: number;
  runs_remaining: number | null;
  period_start: string | null;
  period_end: string | null;
  meta_fees_included: boolean;
}

export interface BillingTransaction {
  product_label: string;
  id: string;
  provider: string;
  provider_payment_id: string;
  provider_order_id: string;
  amount: string;
  currency: string;
  status: "success" | "failed" | "pending" | "refunded" | "partially_refunded";
  paid_at: string | null;
  created_at: string;
}

export function usePlans(country: string = "IN") {
  return useQuery({
    queryKey: ["subscriptions", "plans", country],
    queryFn: async (): Promise<{ country: string; currency: string; plans: Plan[] }> => {
      const { data } = await apiClient.get(`/subscriptions/plans/?country=${country}`);
      return data;
    },
  });
}

export function useCurrentSubscription() {
  return useQuery({
    queryKey: ["subscriptions", "current"],
    refetchInterval: 30000,
    queryFn: async (): Promise<Subscription> => {
      const { data } = await apiClient.get("/subscriptions/current/");
      return data;
    },
  });
}

export function useBillingHistory() {
  return useQuery({
    queryKey: ["subscriptions", "history"],
    queryFn: async (): Promise<BillingTransaction[]> => {
      const { data } = await apiClient.get("/subscriptions/history/");
      return data.results || [];
    },
  });
}

export function useCheckout() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { plan_code?: string; country?: string; product?: "plan" | "dm_automation"; accept_recurring: true }) => {
      const { data } = await apiClient.post("/subscriptions/recurring/checkout/", payload);
      return data;
    },
    onSettled: () => { queryClient.invalidateQueries({ queryKey: ["subscriptions"] }); },
  });
}

export function useVerifyPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      provider_subscription_id: string;
      provider_payment_id: string;
      provider_signature: string;
    }) => {
      const { data } = await apiClient.post("/subscriptions/recurring/verify/", payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });
}

export function useCancelSubscription() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (product: "plan" | "dm_automation" = "plan") => {
      const { data } = await apiClient.post("/subscriptions/recurring/cancel/", { product });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["subscriptions"] });
    },
  });
}

export function useSyncBilling() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => (await apiClient.post("/subscriptions/recurring/sync/")).data,
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["subscriptions"] }); },
  });
}
