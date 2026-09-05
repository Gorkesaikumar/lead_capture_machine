import { openPaymentCheckout } from "@/api/razorpay";
import MetaAutomationRules from "@/features/automations/MetaAutomationRules";
import { useState } from "react";
import { format } from "date-fns";
import {
  CreditCard,
  Check,
  AlertTriangle,
  Zap,
  TrendingUp,
  Globe,
  Camera,
  MessageSquare,
  FileText,
  ShieldCheck,
  Calendar,
  Sparkles,
} from "lucide-react";
import {
  useCurrentSubscription,
  usePlans,
  useCheckout,
  useVerifyPayment,
  useCancelSubscription,
  useBillingHistory,
  useSyncBilling,
  type Plan,
} from "@/api/subscriptions.queries";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";

export default function SubscriptionPage() {
  const [selectedCountry, setSelectedCountry] = useState<"IN" | "US">("IN");
  const [isProcessingPlan, setIsProcessingPlan] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const { data: subData, isLoading: subLoading, error: subError, refetch: refetchSub } = useCurrentSubscription();
  const { data: plansData, isLoading: plansLoading, error: plansError, refetch: refetchPlans } = usePlans(selectedCountry);
  const { data: billingHistory = [] } = useBillingHistory();

  const checkoutMutation = useCheckout();
  const verifyPaymentMutation = useVerifyPayment();
  const cancelMutation = useCancelSubscription();
  const syncMutation = useSyncBilling();

  if (subLoading || plansLoading) {
    return <LoadingSkeleton rows={6} />;
  }

  if (subError || plansError || !subData) {
    return (
      <ErrorState
        code="internal_server_error"
        title="Failed to load billing & subscription data"
        message="Could not connect to subscription services. Please try again."
        onRetry={() => {
          refetchSub();
          refetchPlans();
        }}
      />
    );
  }

  const { plan: currentPlan, usage, status: subStatus, current_period_end, cancel_at_period_end } = subData;
  const plans = plansData?.plans || [];
  const currencySymbol = selectedCountry === "IN" ? "₹" : "$";

  const totalUsed = usage?.total_leads_count || 0;
  const leadLimit = currentPlan?.lead_limit || 100;
  const leadsRemaining = usage?.leads_remaining ?? Math.max(0, leadLimit - totalUsed);
  const usagePct = usage?.usage_percentage ?? Math.min(100, Math.round((totalUsed / leadLimit) * 100));

  const isWarning = usagePct >= 80 && usagePct < 100;
  const isCritical = usagePct >= 100;

  const handleSelectPlan = async (targetPlan: Plan) => {
    if (!window.confirm(`Authorize ${targetPlan.currency} ${targetPlan.price} every month for ${targetPlan.name}? Renewal continues for up to ${subData.billing.cycles} monthly charges unless you cancel. Existing paid access is honoured before the first full charge. Razorpay may request a refundable mandate verification payment.`)) return;
    setIsProcessingPlan(targetPlan.code);
    setToastMessage(null);

    try {
      const order = await checkoutMutation.mutateAsync({
        plan_code: targetPlan.code,
        country: selectedCountry,
        accept_recurring: true,
      });

      const paid = await openPaymentCheckout(order);
      const verified = await verifyPaymentMutation.mutateAsync({
        provider_subscription_id: paid.razorpay_subscription_id || order.subscription_id,
        provider_payment_id: paid.razorpay_payment_id,
        provider_signature: paid.razorpay_signature,
      });

      setToastMessage({
        type: "success",
        text: verified.message,
      });
    } catch (err: any) {
      setToastMessage({
        type: "error",
        text: err?.response?.data?.detail || err?.response?.data?.message || err?.message || "Failed to process plan subscription. Please try again.",
      });
    } finally {
      setIsProcessingPlan(null);
    }
  };

  const buyAutomation = async () => {
    if (!window.confirm(`Authorize ₹399 every month for DM Automation, in addition to your Starter plan? Renewal continues for up to ${subData.billing.cycles} monthly charges unless cancelled. Meta fees are separate.`)) return;
    setIsProcessingPlan("dm_automation");
    setToastMessage(null);
    try {
      const order = await checkoutMutation.mutateAsync({ product: "dm_automation", accept_recurring: true });
      const paid = await openPaymentCheckout(order);
      const verified = await verifyPaymentMutation.mutateAsync({ provider_subscription_id: paid.razorpay_subscription_id || order.subscription_id,
        provider_payment_id: paid.razorpay_payment_id, provider_signature: paid.razorpay_signature });
      setToastMessage({ type: "success", text: verified.message });
    } catch (err: any) {
      setToastMessage({ type: "error", text: err?.response?.data?.detail || err?.response?.data?.message || err?.message || "Could not activate automation." });
    } finally { setIsProcessingPlan(null); }
  };

  const handleCancelSubscription = async () => {
    if (!window.confirm("Are you sure you want to cancel your subscription at the end of the billing period?")) {
      return;
    }
    try {
      const res = await cancelMutation.mutateAsync("plan");
      setToastMessage({ type: "success", text: res.message });
    } catch (err: any) {
      setToastMessage({ type: "error", text: err?.response?.data?.message || "Cancellation could not be confirmed. Check payment status before retrying." });
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto w-full p-6 sm:p-8">
      {/* Toast banner */}
      {toastMessage && (
        <div
          role="status"
          className={`p-4 rounded-xl border flex items-center justify-between shadow-sm animate-in fade-in ${
            toastMessage.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-900"
              : "bg-rose-50 border-rose-200 text-rose-900"
          }`}
        >
          <div className="flex items-center gap-3">
            <Sparkles className={`h-5 w-5 ${toastMessage.type === "success" ? "text-emerald-600" : "text-rose-600"}`} />
            <span className="text-sm font-medium">{toastMessage.text}</span>
          </div>
          <button onClick={() => setToastMessage(null)} className="text-xs opacity-70 hover:opacity-100 font-bold">
            ✕
          </button>
        </div>
      )}

      {/* Quota Warning Banners */}
      {isCritical && (
        <div className="bg-gradient-to-r from-rose-50 to-red-50 border-2 border-rose-300 rounded-2xl p-5 shadow-sm flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="h-10 w-10 bg-rose-500 text-white rounded-xl flex items-center justify-center shrink-0 shadow-md">
            <AlertTriangle className="h-5 w-5" />
          </div>
          <div className="flex-1">
            <h3 className="text-base font-bold text-rose-950">
              {currentPlan.code === "free"
                ? "You've reached your Free Plan limit."
                : `Monthly lead limit reached (${totalUsed} / ${leadLimit} Leads)`}
            </h3>
            <p className="text-sm text-rose-700 mt-0.5">
              {currentPlan.code === "free"
                ? `You've captured all ${leadLimit} leads available for this billing period. Upgrade your plan to continue capturing leads from Instagram, WhatsApp, and Website Forms.`
                : "New incoming leads from Instagram, WhatsApp, and Website forms will be blocked until your plan is upgraded or the next billing cycle begins."}
            </p>
          </div>
          <Button
            onClick={() => document.getElementById("pricing-cards")?.scrollIntoView({ behavior: "smooth" })}
            className="bg-rose-600 hover:bg-rose-700 text-white font-semibold shadow-md shrink-0"
          >
            Upgrade Plan Now
          </Button>
        </div>
      )}

      {!isCritical && usagePct >= 90 && (
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-4 flex items-center gap-3 text-rose-900 shadow-sm">
          <AlertTriangle className="h-5 w-5 text-rose-600 shrink-0" />
          <div className="flex-1 text-sm font-medium">
            <span className="font-bold">Usage Warning:</span> You're almost out of leads. Only {leadsRemaining} lead{leadsRemaining === 1 ? "" : "s"} remaining in your {currentPlan.name} Plan ({totalUsed}/{leadLimit} used).
          </div>
          <Button
            size="sm"
            onClick={() => document.getElementById("pricing-cards")?.scrollIntoView({ behavior: "smooth" })}
            className="bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold shrink-0"
          >
            Upgrade Plan
          </Button>
        </div>
      )}

      {!isCritical && usagePct >= 80 && usagePct < 90 && (
        <div className="bg-amber-50 border border-amber-300 rounded-2xl p-4 flex items-center gap-3 text-amber-900 shadow-sm">
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
          <div className="flex-1 text-sm font-medium">
            <span className="font-bold">Usage Warning:</span> You've used 80% of your monthly lead limit ({totalUsed}/{leadLimit} leads). Consider upgrading to continue capturing leads without interruption.
          </div>
        </div>
      )}

      {!isCritical && usagePct >= 50 && usagePct < 80 && (
        <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-center gap-3 text-blue-900 shadow-sm">
          <Zap className="h-5 w-5 text-blue-600 shrink-0" />
          <div className="flex-1 text-sm font-medium">
            You've used {totalUsed} of your {leadLimit} {currentPlan.name} Plan leads this billing period.
          </div>
        </div>
      )}

      {/* Top Header & Country Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Subscription & Billing</h1>
          <p className="text-sm text-slate-500 mt-1">Manage your plan, lead entitlements, multi-currency billing, and usage limits.</p>
        </div>

        <div className="flex items-center gap-2 bg-slate-100 p-1.5 rounded-xl border border-slate-200/60 self-start sm:self-auto">
          <span className="text-xs font-semibold text-slate-500 px-2 flex items-center gap-1">
            <Globe className="h-3.5 w-3.5" /> Billing Country:
          </span>
          <button
            onClick={() => setSelectedCountry("IN")}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              selectedCountry === "IN"
                ? "bg-white text-rose-600 shadow-sm border border-slate-200/80"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            🇮🇳 India (INR ₹)
          </button>
          <button
            onClick={() => setSelectedCountry("US")}
            className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 ${
              selectedCountry === "US"
                ? "bg-white text-rose-600 shadow-sm border border-slate-200/80"
                : "text-slate-600 hover:text-slate-900"
            }`}
          >
            🇺🇸 International (USD $)
          </button>
        </div>
      </div>

      {!subData.automation.payment_available && <p role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm">Payments are not configured. Plan and add-on purchases become available after the administrator configures Razorpay.</p>}
      {!subData.automation.can_manage_billing && <p className="text-sm text-slate-600">Only a workspace owner or administrator can manage billing.</p>}
      <section aria-label="Automatic billing" className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
        <h2 className="font-semibold text-slate-900">Automatic monthly billing {subData.billing.test_mode && <Badge variant="outline">Test mode</Badge>}</h2>
        <p className="text-sm text-slate-600">Paid plans and the optional automation add-on renew each month after you authorize Razorpay. Cancel anytime to stop future charges; your paid access remains until its expiry. Each mandate allows up to {subData.billing.cycles} monthly charges. International subscriptions require an eligible card.</p>
        <p className="text-sm text-slate-600">To change an existing recurring plan, cancel its renewal and choose the new plan after the current billing cycle ends.</p>
        {(["plan", "dm_automation"] as const).map(product => {
          const agreement = subData.billing[product];
          if (!agreement) return null;
          const ended = ["cancelled", "completed", "expired", "failed"].includes(agreement.status);
          return <div key={agreement.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3 text-sm">
            <div><strong>{product === "plan" ? "Plan" : "DM Automation"}: {agreement.currency} {agreement.amount}/month</strong><p className="capitalize text-slate-600">{agreement.status} {agreement.cancel_at_period_end && "· renewal cancelled"}</p>{agreement.last_error && <p className="text-amber-800">{agreement.last_error}</p>}{["pending", "halted", "paused"].includes(agreement.status) && <p className="text-amber-800">Renewal needs attention. Check your payment method in Razorpay; access is limited to the period already paid.</p>}</div>
            {subData.automation.can_manage_billing && <div className="flex flex-wrap gap-2">
              {agreement.short_url && !ended && <a href={agreement.short_url} target="_blank" rel="noopener noreferrer" className="text-rose-700 underline">Open Razorpay</a>}
              {!ended && !agreement.cancel_at_period_end && <Button variant="outline" size="sm" disabled={cancelMutation.isPending} onClick={async () => {
                if (!window.confirm(`Stop automatic renewal for ${product === "plan" ? "your plan and automation add-on" : "DM Automation"}? Paid access remains until expiry.`)) return;
                try { const result = await cancelMutation.mutateAsync(product); setToastMessage({ type: "success", text: result.message }); }
                catch (error: any) { setToastMessage({ type: "error", text: error.response?.data?.message || "Cancellation could not be confirmed. Please check payment status." }); }
              }}>Stop renewal</Button>}
            </div>}
          </div>;
        })}
        {subData.automation.can_manage_billing && <Button variant="outline" disabled={syncMutation.isPending || !!isProcessingPlan} onClick={async () => {
          try { const result = await syncMutation.mutateAsync(); setToastMessage({ type: "success", text: result.message }); }
          catch (error: any) { setToastMessage({ type: "error", text: error.response?.data?.message || "Payment status could not be refreshed. Please try again shortly." }); }
        }}>{syncMutation.isPending ? "Checking payments…" : "Check payment status"}</Button>}
      </section>

      {/* Active Subscription & Usage Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Current Plan Details */}
        <Card className="border border-slate-200/80 shadow-sm rounded-2xl bg-white overflow-hidden flex flex-col justify-between">
          <CardHeader className="border-b border-slate-100 bg-slate-50/50 pb-4">
            <div className="flex justify-between items-center">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Current Plan</span>
              <Badge className="bg-emerald-500/10 text-emerald-700 border-emerald-200 capitalize font-bold px-2.5 py-0.5">
                {subStatus}
              </Badge>
            </div>
            <CardTitle className="text-2xl font-extrabold text-slate-900 mt-2">{currentPlan.name} Plan</CardTitle>
            <CardDescription className="text-xs text-slate-500">
              {currentPlan.lead_limit} combined leads / month entitlement
            </CardDescription>
          </CardHeader>
          <CardContent className="p-5 space-y-3 text-sm text-slate-600">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500 flex items-center gap-1.5 text-xs">
                <CreditCard className="h-3.5 w-3.5 text-slate-400" /> Charged Amount
              </span>
              <span className="font-bold text-slate-900">
                {subData.billing_currency === "INR" ? "₹" : "$"}{Number(subData.charged_amount || 0).toLocaleString("en-US", { maximumFractionDigits: 2 })} {subData.billing_currency} (base plan)
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500 flex items-center gap-1.5 text-xs">
                <Calendar className="h-3.5 w-3.5 text-slate-400" /> Paid Period Ends
              </span>
              <span className="font-semibold text-slate-800">
                {current_period_end ? format(new Date(current_period_end), "MMM dd, yyyy") : "N/A"}
              </span>
            </div>
            {cancel_at_period_end && (
              <p className="text-xs text-rose-600 bg-rose-50 p-2 rounded-lg font-medium">
                ⚠️ Scheduled for cancellation on period end.
              </p>
            )}
          </CardContent>
          <CardFooter className="bg-slate-50/50 border-t border-slate-100 p-4">
            {!cancel_at_period_end ? (
              <Button disabled={!subData.automation.can_manage_billing || currentPlan.code === "free"} variant="ghost" size="sm" onClick={handleCancelSubscription} className="text-xs text-slate-500 hover:text-rose-600 w-full">
                Cancel Subscription
              </Button>
            ) : (
              <span className="text-xs text-slate-400 italic text-center w-full">Cancellation Pending</span>
            )}
          </CardFooter>
        </Card>

        {/* Combined Quota Usage Widget */}
        <Card className="md:col-span-2 border border-slate-200/80 shadow-sm rounded-2xl bg-white p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
                  <Zap className="h-5 w-5 text-rose-500" /> Combined Lead Quota Usage
                </h3>
                <p className="text-xs text-slate-500">Instagram Direct + WhatsApp Business + Website Forms</p>
              </div>
              <div className="text-right">
                <span className="text-2xl font-extrabold text-slate-900">{totalUsed}</span>
                <span className="text-sm font-semibold text-slate-400"> / {leadLimit} Leads</span>
              </div>
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="h-3 w-full bg-slate-100 rounded-full overflow-hidden p-0.5 border border-slate-200/50">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isCritical
                      ? "bg-rose-500"
                      : isWarning
                      ? "bg-amber-500"
                      : "bg-gradient-to-r from-rose-500 via-pink-500 to-amber-500"
                  }`}
                  style={{ width: `${usagePct}%` }}
                />
              </div>
              <div className="flex justify-between text-xs font-semibold text-slate-500">
                <span>{usagePct}% Consumed</span>
                <span className={isCritical ? "text-rose-600 font-bold" : "text-emerald-600 font-bold"}>
                  {leadsRemaining} Leads Remaining
                </span>
              </div>
            </div>

            {/* Channel Breakout Metrics */}
            <div className="grid grid-cols-3 gap-3 mt-6 pt-4 border-t border-slate-100">
              <div className="bg-pink-50/60 p-3 rounded-xl border border-pink-100">
                <div className="flex items-center gap-1.5 text-xs font-bold text-pink-700">
                  <Camera className="h-3.5 w-3.5 text-pink-600" /> Instagram
                </div>
                <div className="text-xl font-extrabold text-pink-950 mt-1">{usage?.instagram_lead_count || 0}</div>
                <div className="text-[10px] text-pink-600/80">Direct Messages</div>
              </div>

              <div className="bg-emerald-50/60 p-3 rounded-xl border border-emerald-100">
                <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700">
                  <MessageSquare className="h-3.5 w-3.5 text-emerald-600" /> WhatsApp
                </div>
                <div className="text-xl font-extrabold text-emerald-950 mt-1">{usage?.whatsapp_lead_count || 0}</div>
                <div className="text-[10px] text-emerald-600/80">Business Inquiries</div>
              </div>

              <div className="bg-amber-50/60 p-3 rounded-xl border border-amber-100">
                <div className="flex items-center gap-1.5 text-xs font-bold text-amber-700">
                  <FileText className="h-3.5 w-3.5 text-amber-600" /> Website
                </div>
                <div className="text-xl font-extrabold text-amber-950 mt-1">{usage?.website_lead_count || 0}</div>
                <div className="text-[10px] text-amber-600/80">Form Submissions</div>
              </div>
            </div>
          </div>
        </Card>
      </div>

      {/* Pricing Cards Section */}
      <div id="pricing-cards" className="pt-6 space-y-6">
        <div className="text-center max-w-xl mx-auto">
          <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">Choose Your Growth Plan</h2>
          <p className="text-sm text-slate-500 mt-1">
            Choose monthly access with automatic renewal. Manage an existing mandate above before changing plans.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => {
            const isCurrent = plan.code.toLowerCase() === currentPlan.code.toLowerCase() && subData.is_valid;
            const isPopular = plan.is_popular || plan.code === "creator";
            const isFree = plan.code === "free";
            const priceVal = isFree ? "0" : plan.price || (selectedCountry === "IN" ? plan.price_inr : plan.price_usd);

            return (
              <Card
                key={plan.id || plan.code}
                className={`relative flex flex-col justify-between rounded-2xl transition-all duration-200 overflow-hidden ${
                  isCurrent
                    ? "border-2 border-rose-500 shadow-lg ring-2 ring-rose-500/20 bg-white"
                    : isPopular
                    ? "border-2 border-slate-900 shadow-md bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 text-white"
                    : "border border-slate-200 shadow-sm bg-white hover:border-slate-300"
                }`}
              >
                {/* Ribbon Badges with Fixed Slot Height for Perfect Card Alignment */}
                {isCurrent ? (
                  <div className="bg-rose-500 text-white text-[10px] font-extrabold px-3 py-1 text-center uppercase tracking-widest h-6 flex items-center justify-center">
                    Active Plan
                  </div>
                ) : isPopular ? (
                  <div className="bg-gradient-to-r from-rose-500 to-pink-500 text-white text-[10px] font-extrabold px-3 py-1 text-center uppercase tracking-widest h-6 flex items-center justify-center">
                    Most Popular
                  </div>
                ) : (
                  <div className="h-6" />
                )}

                <CardHeader className="p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className={`text-xl font-extrabold ${isPopular && !isCurrent ? "text-white" : "text-slate-900"}`}>
                        {plan.name}
                      </CardTitle>
                      <CardDescription className={`text-xs mt-1 ${isPopular && !isCurrent ? "text-slate-400" : "text-slate-500"}`}>
                        {plan.description}
                      </CardDescription>
                    </div>
                  </div>

                  <div className="mt-4 flex items-baseline gap-1">
                    <span className={`text-4xl font-black ${isPopular && !isCurrent ? "text-white" : "text-slate-900"}`}>
                      {currencySymbol}{priceVal}
                    </span>
                    <span className={`text-xs font-semibold ${isPopular && !isCurrent ? "text-slate-400" : "text-slate-500"}`}>
                      / month
                    </span>
                  </div>
                </CardHeader>

                <CardContent className="p-6 pt-0 space-y-4 flex-1">
                  {/* Highlighted Combined Lead Entitlement */}
                  <div
                    className={`p-3 rounded-xl flex items-center gap-3 border ${
                      isPopular && !isCurrent
                        ? "bg-slate-800/80 border-slate-700 text-rose-300"
                        : "bg-rose-50/80 border-rose-100 text-rose-900"
                    }`}
                  >
                    <TrendingUp className="h-5 w-5 shrink-0 text-rose-500" />
                    <div>
                      <div className="text-sm font-extrabold">{plan.lead_limit} Combined Leads</div>
                      <div className="text-[11px] opacity-80">Instagram + WhatsApp + Website</div>
                    </div>
                  </div>

                  {/* Bullet features */}
                  <ul className="space-y-2.5 text-xs">
                    {(plan.features || []).map((feat, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <Check className={`h-4 w-4 shrink-0 mt-0.5 ${isPopular && !isCurrent ? "text-rose-400" : "text-emerald-600"}`} />
                        <span className={isPopular && !isCurrent ? "text-slate-300" : "text-slate-600"}>{feat}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>

                <CardFooter className="p-6 pt-0">
                  <Button
                    disabled={isFree || !!isProcessingPlan || !subData.automation.payment_available || !subData.automation.can_manage_billing || !!(subData.billing.plan && !["created", "cancelled", "completed", "expired", "failed"].includes(subData.billing.plan.status))}
                    onClick={() => handleSelectPlan(plan)}
                    className={`w-full font-bold h-11 rounded-xl transition-all shadow-sm ${
                      isPopular
                        ? "bg-gradient-to-r from-rose-500 to-pink-500 hover:from-rose-600 hover:to-pink-600 text-white shadow-rose-500/25"
                        : "bg-slate-900 hover:bg-slate-800 text-white"
                    }`}
                  >
                    {isProcessingPlan === plan.code
                      ? "Processing..."
                      : isFree
                      ? (isCurrent ? "Current Free Plan" : "Get Started Free")
                      : isCurrent && subData.is_valid
                      ? (subData.billing.plan && !["cancelled", "completed", "expired", "failed"].includes(subData.billing.plan.status) ? "Current Active Plan" : "Enable automatic renewal")
                      : `Upgrade to ${plan.name}`}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      </div>

      <section aria-label="DM Automation add-on" className="rounded-2xl border border-rose-200 bg-white p-6 space-y-4">
        <div className="flex flex-wrap justify-between gap-4"><div><h2 className="text-xl font-bold">DM Automation add-on</h2><p className="mt-1 text-sm text-slate-600">Available on Starter · 1,000 automation runs per month</p></div><div><strong className="text-2xl">₹399</strong><span className="text-sm text-slate-500"> / month extra</span></div></div>
        <p className="text-sm">Starter ₹400 + automation ₹399 = <strong>₹799/month</strong> in INR. Meta and messaging-provider charges are separate. Creator and Enterprise retain included automation with no additional app run cap.</p>
        <p className="text-sm text-slate-600">The add-on renews automatically every month after authorization and requires an active Starter subscription. Stopping your base plan renewal also stops the add-on renewal. No automatic overage charges.</p>
        {subData.automation.included ? <p className="text-sm text-emerald-700">Automation is included in your plan; no add-on purchase is needed.</p>
          : subData.automation.addon_available && subData.automation.entitled ? <p className="text-sm text-emerald-700">Add-on active until {subData.automation.addon_end && format(new Date(subData.automation.addon_end), "MMM dd, yyyy")}. {subData.automation.runs_used.toLocaleString()} / {subData.automation.run_limit?.toLocaleString()} runs used.</p>
          : <div className="space-y-2"><Button disabled={!subData.is_valid || !subData.automation.addon_available || !subData.automation.payment_available || !subData.automation.can_manage_billing || !!isProcessingPlan} onClick={buyAutomation}>Activate DM Automation — ₹399</Button><p className="text-sm text-slate-600">{!subData.is_valid || !subData.automation.addon_available ? "An active Starter plan is required. Choose or renew Starter above." : !subData.automation.can_manage_billing ? "Only a workspace owner or administrator can purchase the add-on." : !subData.automation.payment_available ? "Payments are not configured. The administrator must configure Razorpay before purchases are available." : "Payment is verified before automation access is activated. Charged in INR."}</p></div>}
        <MetaAutomationRules />
      </section>

      {/* Billing Transaction Ledger */}
      <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm space-y-4">
        <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-slate-600" /> Billing Transaction History
        </h3>

        {billingHistory.length === 0 ? (
          <p className="text-xs text-slate-500 py-4 italic">No prior billing transactions recorded.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left text-slate-600">
              <thead className="bg-slate-50 text-slate-500 uppercase font-semibold border-b border-slate-200/80">
                <tr>
                  <th className="p-3">Date</th>
                  <th className="p-3">Item</th>
                  <th className="p-3">Order ID</th>
                  <th className="p-3">Gateway</th>
                  <th className="p-3">Amount</th>
                  <th className="p-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {billingHistory.map((tx) => (
                  <tr key={tx.id} className="hover:bg-slate-50/50">
                    <td className="p-3 font-medium text-slate-900">
                      {tx.paid_at || tx.created_at ? format(new Date(tx.paid_at || tx.created_at), "MMM dd, yyyy HH:mm") : "N/A"}
                    </td>
                    <td className="p-3">{tx.product_label}</td>
                    <td className="p-3 font-mono text-slate-500">{tx.provider_order_id}</td>
                    <td className="p-3 capitalize">{tx.provider}</td>
                    <td className="p-3 font-bold text-slate-900">
                      {tx.currency === "INR" ? "₹" : "$"}{tx.amount} {tx.currency}
                    </td>
                    <td className="p-3">
                      <Badge className={`capitalize font-bold px-2 py-0.5 text-[10px] ${tx.status === "success" ? "bg-emerald-50 text-emerald-800 border-emerald-200" : tx.status === "failed" ? "bg-rose-50 text-rose-800 border-rose-200" : "bg-amber-50 text-amber-900 border-amber-200"}`}>
                        {tx.status.replaceAll("_", " ")}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
