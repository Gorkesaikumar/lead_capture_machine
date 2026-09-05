import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { 
  MessageCircle, 
  Globe, 
  Camera, 
  CheckCircle2, 
  ArrowRight,
  Loader2,
  Sparkles
} from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCurrentOrganization, useUpdateOrganization } from "@/api/organizations.queries";
import { useIntegrationHealth } from "@/api/integrations.queries";
import { useLeadForms } from "@/api/leads.queries";
import { Badge } from "@/components/ui/badge";

// --- STEPS ENUM ---
type OnboardingStep = "BUSINESS" | "CHANNELS" | "READY";

// --- STEP 1: BUSINESS INFO ---
const businessSchema = z.object({
  name: z.string().min(2, "Organization name is required"),
});
type BusinessFormValues = z.infer<typeof businessSchema>;

function BusinessInfoStep({ onNext }: { onNext: () => void }) {
  const { data: org, isLoading } = useCurrentOrganization();
  const updateOrg = useUpdateOrganization();

  const form = useForm<BusinessFormValues>({
    resolver: zodResolver(businessSchema),
    values: {
      name: org?.name || "",
    },
  });

  const onSubmit = async (data: BusinessFormValues) => {
    try {
      await updateOrg.mutateAsync({ name: data.name });
      onNext();
    } catch (err) {
      toast.error("Failed to update organization name.");
    }
  };

  if (isLoading) {
    return <div className="flex justify-center p-8"><Loader2 className="animate-spin h-6 w-6 text-slate-400" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center">
        <h2 className="text-2xl font-semibold tracking-tight">Business Information</h2>
        <p className="text-sm text-slate-500">Let's start by setting up your workspace details.</p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none text-slate-700" htmlFor="name">
            Organization Name
          </label>
          <Input
            id="name"
            placeholder="Studio Name"
            {...form.register("name")}
            className={form.formState.errors.name ? "border-rose-300" : ""}
          />
          {form.formState.errors.name && (
            <p className="text-xs text-rose-500">{form.formState.errors.name.message}</p>
          )}
        </div>
        
        <div className="pt-4 flex justify-end">
          <Button type="submit" disabled={updateOrg.isPending}>
            {updateOrg.isPending ? "Saving..." : "Continue"}
            {!updateOrg.isPending && <ArrowRight className="ml-2 h-4 w-4" />}
          </Button>
        </div>
      </form>
    </div>
  );
}

// --- STEP 2: CHANNELS ---
function ConnectChannelsStep({ onNext }: { onNext: () => void }) {
  const { data: health, isLoading: isHealthLoading } = useIntegrationHealth();
  const { data: forms = [], isLoading: isFormsLoading } = useLeadForms();

  const isLoading = isHealthLoading || isFormsLoading;
  
  const ig = health?.instagram;
  const wa = health?.whatsapp;
  const activeFormsCount = forms.filter((f: any) => f.is_active).length;

  const handleConnectInstagram = async () => {
    try {
      const { data } = await apiClient.get("/integrations/oauth/instagram/login/");
      if (data && data.url) {
        window.location.href = data.url;
      }
    } catch (e) {
      toast.error("Failed to initiate Instagram Login");
    }
  };

  const handleConnectWhatsApp = async () => {
    try {
      const businessId = window.prompt("Enter the Meta business portfolio ID that owns your WhatsApp account. This connection requires business_management permission.");
      if (!businessId) return;
      const { data } = await apiClient.get("/integrations/oauth/whatsapp/login/", { params: { business_id: businessId.trim() } });
      if (data && data.url) {
        window.location.href = data.url;
      }
    } catch (e) {
      toast.error("Failed to initiate WhatsApp Login");
    }
  };

  if (isLoading) {
    return <div className="flex justify-center p-8"><Loader2 className="animate-spin h-6 w-6 text-slate-400" /></div>;
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2 text-center">
        <h2 className="text-2xl font-semibold tracking-tight">Connect Channels</h2>
        <p className="text-sm text-slate-500">
          Connect your communication channels to start receiving leads directly into V4 Studio.
        </p>
      </div>

      <div className="grid gap-4">
        {/* Instagram */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-pink-50 rounded-lg">
                <Camera className="h-5 w-5 text-pink-600" />
              </div>
              <div>
                <CardTitle className="text-base">Instagram Direct</CardTitle>
                <CardDescription className="text-xs">Receive and reply to DMs</CardDescription>
              </div>
            </div>
            {ig?.connection_status === "CONNECTED" ? (
              <Badge className="bg-green-100 text-green-800"><CheckCircle2 className="w-3 h-3 mr-1" /> Connected</Badge>
            ) : (
              <Badge variant="secondary">Not connected</Badge>
            )}
          </CardHeader>
          <CardContent className="pt-2">
             {ig?.connection_status !== "CONNECTED" && (
                <Button variant="outline" size="sm" onClick={handleConnectInstagram} className="w-full">
                  Connect Instagram
                </Button>
             )}
          </CardContent>
        </Card>

        {/* WhatsApp */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-50 rounded-lg">
                <MessageCircle className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <CardTitle className="text-base">WhatsApp Business</CardTitle>
                <CardDescription className="text-xs">Business messaging alerts</CardDescription>
              </div>
            </div>
            {wa?.connection_status === "CONNECTED" ? (
              <Badge className="bg-green-100 text-green-800"><CheckCircle2 className="w-3 h-3 mr-1" /> Connected</Badge>
            ) : (
              <Badge variant="secondary">Not connected</Badge>
            )}
          </CardHeader>
          <CardContent className="pt-2">
             {wa?.connection_status !== "CONNECTED" && (
                <Button variant="outline" size="sm" onClick={handleConnectWhatsApp} className="w-full">
                  Connect WhatsApp
                </Button>
             )}
          </CardContent>
        </Card>

        {/* Website Forms */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-50 rounded-lg">
                <Globe className="h-5 w-5 text-amber-600" />
              </div>
              <div>
                <CardTitle className="text-base">Website Forms</CardTitle>
                <CardDescription className="text-xs">Embeddable lead widgets</CardDescription>
              </div>
            </div>
            {activeFormsCount > 0 ? (
              <Badge className="bg-green-100 text-green-800"><CheckCircle2 className="w-3 h-3 mr-1" /> Active</Badge>
            ) : (
              <Badge variant="secondary">Not setup</Badge>
            )}
          </CardHeader>
          <CardContent className="pt-2">
             {activeFormsCount === 0 && (
                <Button variant="outline" size="sm" onClick={() => window.open('/channels/website', '_blank')} className="w-full">
                  Create Form
                </Button>
             )}
          </CardContent>
        </Card>
      </div>

      <div className="pt-4 flex justify-between items-center">
        <Button variant="ghost" className="text-slate-500" onClick={onNext}>
          Skip for now
        </Button>
        <Button onClick={onNext}>
          Continue <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// --- STEP 3: READY ---
function WorkspaceReadyStep() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center space-y-6 py-8 text-center">
      <div className="h-16 w-16 rounded-full bg-slate-900 flex items-center justify-center">
        <Sparkles className="h-8 w-8 text-white" />
      </div>
      
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Workspace Ready!</h2>
        <p className="text-sm text-slate-500 max-w-sm mx-auto">
          Your V4 Studio workspace has been configured. You're ready to start managing your leads and conversations.
        </p>
      </div>

      <Button onClick={() => navigate("/app")} className="w-full max-w-xs mt-4" size="lg">
        Go to Dashboard
      </Button>
    </div>
  );
}

// --- MAIN FLOW ---
export default function OnboardingFlow() {
  const [step, setStep] = useState<OnboardingStep>("BUSINESS");

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Stepper Header */}
        <div className="mb-8 flex items-center justify-center space-x-4 text-sm font-medium text-slate-400">
          <div className={`flex items-center gap-2 ${step === "BUSINESS" ? "text-slate-900" : (step === "CHANNELS" || step === "READY") ? "text-emerald-600" : ""}`}>
            <div className={`h-6 w-6 rounded-full flex items-center justify-center border-2 ${step === "BUSINESS" ? "border-slate-900" : (step === "CHANNELS" || step === "READY") ? "border-emerald-600 bg-emerald-50" : "border-slate-200"}`}>
              {step === "CHANNELS" || step === "READY" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : "1"}
            </div>
            <span className="hidden sm:inline">Business</span>
          </div>
          <div className="h-px w-8 bg-slate-200" />
          <div className={`flex items-center gap-2 ${step === "CHANNELS" ? "text-slate-900" : step === "READY" ? "text-emerald-600" : ""}`}>
             <div className={`h-6 w-6 rounded-full flex items-center justify-center border-2 ${step === "CHANNELS" ? "border-slate-900" : step === "READY" ? "border-emerald-600 bg-emerald-50" : "border-slate-200"}`}>
              {step === "READY" ? <CheckCircle2 className="h-4 w-4 text-emerald-600" /> : "2"}
            </div>
            <span className="hidden sm:inline">Channels</span>
          </div>
          <div className="h-px w-8 bg-slate-200" />
          <div className={`flex items-center gap-2 ${step === "READY" ? "text-slate-900" : ""}`}>
             <div className={`h-6 w-6 rounded-full flex items-center justify-center border-2 ${step === "READY" ? "border-slate-900" : "border-slate-200"}`}>
              3
            </div>
            <span className="hidden sm:inline">Ready</span>
          </div>
        </div>

        {/* Content Card */}
        <Card className="border-slate-200 shadow-sm bg-white">
          <CardContent className="p-6 sm:p-8">
            {step === "BUSINESS" && <BusinessInfoStep onNext={() => setStep("CHANNELS")} />}
            {step === "CHANNELS" && <ConnectChannelsStep onNext={() => setStep("READY")} />}
            {step === "READY" && <WorkspaceReadyStep />}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
