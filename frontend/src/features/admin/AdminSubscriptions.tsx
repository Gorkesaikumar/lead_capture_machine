import { useState } from "react";
import {
  useAdminSubscriptionPlans,
  useUpdateAdminPlanConfig,
} from "@/api/admin.queries";
import {
  CreditCard,
  Edit,
  Check,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { toast } from "sonner";

export default function AdminSubscriptions() {
  const { data: plans = [], isLoading, refetch } = useAdminSubscriptionPlans();
  const updateMutation = useUpdateAdminPlanConfig();

  const [editingPlan, setEditingPlan] = useState<any | null>(null);
  const [formData, setFormData] = useState({
    price_usd: "",
    price_inr: "",
    lead_limit: "",
    name: "",
    description: "",
    featuresText: "",
  });

  const handleEditClick = (plan: any) => {
    setEditingPlan(plan);
    setFormData({
      price_usd: plan.price_usd,
      price_inr: plan.price_inr,
      lead_limit: String(plan.lead_limit),
      name: plan.name,
      description: plan.description || "",
      featuresText: Array.isArray(plan.features) ? plan.features.join("\n") : "",
    });
  };

  const handleSave = async () => {
    if (!editingPlan) return;

    if (Number(formData.price_usd) < 0 || Number(formData.price_inr) < 0) {
      toast.error("Plan price cannot be negative.");
      return;
    }
    if (Number(formData.lead_limit) < 0) {
      toast.error("Lead limit cannot be negative.");
      return;
    }

    try {
      const features = formData.featuresText
        .split("\n")
        .map((f) => f.trim())
        .filter(Boolean);

      const res = await updateMutation.mutateAsync({
        planId: editingPlan.id,
        price_usd: formData.price_usd,
        price_inr: formData.price_inr,
        lead_limit: Number(formData.lead_limit),
        name: formData.name,
        description: formData.description,
        features,
      });

      toast.success(res.message || "Plan configuration updated!");
      setEditingPlan(null);
      refetch();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update plan configuration.");
    }
  };

  if (isLoading) {
    return (
      <div className="py-12 text-center text-slate-500 text-sm font-medium">
        Loading Centralized Subscription Plan Control Center...
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
            Subscription Control Center <CreditCard className="h-6 w-6 text-indigo-600" />
          </h1>
          <p className="text-xs text-slate-500 font-medium mt-1">
            Authoritative configuration for Free, Starter, Creator, and Enterprise plans. Updates dynamically affect pricing & checkouts.
          </p>
        </div>
      </div>

      {/* Plan Configuration Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {plans.map((plan: any) => (
          <Card
            key={plan.id}
            className={`bg-white border-slate-200/80 shadow-sm rounded-2xl overflow-hidden flex flex-col justify-between relative ${
              plan.code === "creator" ? "ring-2 ring-rose-500/50" : ""
            }`}
          >
            {plan.code === "creator" && (
              <div className="bg-gradient-to-r from-rose-500 via-purple-600 to-indigo-600 text-white text-[10px] font-extrabold uppercase tracking-widest text-center py-1">
                Most Popular Tier
              </div>
            )}

            <div>
              <CardHeader className="p-6 border-b border-slate-100">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-xl font-black text-slate-900">{plan.name}</CardTitle>
                    <CardDescription className="text-xs text-slate-500 mt-1 font-medium">
                      {plan.description || `Plan Code: ${plan.code}`}
                    </CardDescription>
                  </div>
                  <Badge className="bg-slate-100 text-slate-700 border-slate-200 uppercase text-[10px] font-bold">
                    {plan.code}
                  </Badge>
                </div>

                <div className="mt-4 space-y-1">
                  <div className="text-3xl font-black text-slate-900">
                    ${plan.price_usd} <span className="text-xs text-slate-500 font-semibold">/ mo</span>
                  </div>
                  <div className="text-xs font-bold text-rose-600">
                    India Price: ₹{plan.price_inr} / mo
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-6 space-y-4">
                {/* Combined Lead Limit Box */}
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center gap-3">
                  <TrendingUp className="h-5 w-5 text-rose-600 shrink-0" />
                  <div>
                    <div className="text-sm font-black text-slate-900">{plan.lead_limit} Combined Leads</div>
                    <div className="text-[10px] text-slate-500 font-medium">Instagram + WhatsApp + Website</div>
                  </div>
                </div>

                {/* Live Telemetry stats */}
                <div className="grid grid-cols-2 gap-2 text-xs border-y border-slate-100 py-3">
                  <div>
                    <span className="text-slate-500 font-medium">Active Subscribers:</span>
                    <div className="font-extrabold text-slate-900 mt-0.5">{plan.active_subscribers} orgs</div>
                  </div>
                  <div>
                    <span className="text-slate-500 font-medium">Total Revenue:</span>
                    <div className="font-extrabold text-emerald-600 mt-0.5">${plan.revenue_generated_usd}</div>
                  </div>
                </div>

                {/* Features Checklist */}
                <div className="space-y-2 text-xs">
                  <span className="font-bold text-slate-500 uppercase tracking-wider text-[10px]">
                    Entitled Features
                  </span>
                  <ul className="space-y-1.5 text-slate-700 font-medium">
                    {(plan.features || []).map((feat: string, idx: number) => (
                      <li key={idx} className="flex items-start gap-2">
                        <Check className="h-3.5 w-3.5 text-emerald-600 shrink-0 mt-0.5" />
                        <span>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </CardContent>
            </div>

            <div className="p-6 pt-0">
              <Button
                onClick={() => handleEditClick(plan)}
                className="w-full bg-slate-900 hover:bg-slate-800 text-white font-bold text-xs h-10 rounded-xl"
              >
                <Edit className="h-3.5 w-3.5 mr-2" /> Edit Plan Configuration
              </Button>
            </div>
          </Card>
        ))}
      </div>

      {/* Edit Plan Dialog */}
      <Dialog open={!!editingPlan} onOpenChange={() => setEditingPlan(null)}>
        <DialogContent className="max-w-md bg-white border-slate-200 text-slate-900 p-6 rounded-3xl shadow-2xl">
          <DialogHeader>
            <DialogTitle className="text-lg font-black text-slate-900 flex items-center gap-2">
              <Edit className="h-5 w-5 text-rose-600" /> Edit {editingPlan?.name} Plan
            </DialogTitle>
            <DialogDescription className="text-xs text-slate-500 font-medium">
              Updates to pricing or lead limits will dynamically update new checkouts and application pricing pages.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-3">
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Plan Display Name</label>
              <Input
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl focus:bg-white focus:border-rose-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">USD Price ($)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.price_usd}
                  onChange={(e) => setFormData({ ...formData, price_usd: e.target.value })}
                  className="bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl font-bold text-emerald-600 focus:bg-white focus:border-rose-500"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-bold text-slate-700">INR Price (₹)</label>
                <Input
                  type="number"
                  step="0.01"
                  value={formData.price_inr}
                  onChange={(e) => setFormData({ ...formData, price_inr: e.target.value })}
                  className="bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl font-bold text-rose-600 focus:bg-white focus:border-rose-500"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Monthly Combined Lead Quota</label>
              <Input
                type="number"
                value={formData.lead_limit}
                onChange={(e) => setFormData({ ...formData, lead_limit: e.target.value })}
                className="bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl font-bold focus:bg-white focus:border-rose-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Description</label>
              <Input
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="bg-slate-50 border-slate-200 text-slate-900 text-xs h-10 rounded-xl focus:bg-white focus:border-rose-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-700">Features List (One per line)</label>
              <textarea
                rows={4}
                value={formData.featuresText}
                onChange={(e) => setFormData({ ...formData, featuresText: e.target.value })}
                className="w-full bg-slate-50 border border-slate-200 text-slate-900 text-xs p-3 rounded-xl focus:bg-white focus:outline-none focus:border-rose-500"
              />
            </div>
          </div>

          <DialogFooter className="pt-4 border-t border-slate-100">
            <Button variant="ghost" onClick={() => setEditingPlan(null)} className="text-xs font-semibold">
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              disabled={updateMutation.isPending}
              className="bg-gradient-to-r from-rose-500 via-purple-600 to-indigo-600 text-white font-bold text-xs rounded-xl shadow-md shadow-purple-500/20"
            >
              {updateMutation.isPending ? "Saving Changes..." : "Save & Propagate Configuration"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
