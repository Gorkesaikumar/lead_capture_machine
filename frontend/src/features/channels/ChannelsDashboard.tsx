import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Camera, MessageCircle, Globe, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/api/client";
import { useIntegrationHealth } from "@/api/integrations.queries";
import { useLeadForms } from "@/api/leads.queries";
import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";
import { prepareMetaSignup, launchMetaSignup } from "./metaSignup";
import type { SignupConfig } from "./metaSignup";

type Channel = "instagram" | "whatsapp";
const names = { instagram: "Instagram", whatsapp: "WhatsApp" };
const callbackErrors: Record<string, string> = {
  invalid_state: "This connection request expired or was already used. Start again from Channels.",
  authorization_cancelled: "Connection was cancelled. You can try again when ready.",
  permission_required: "Required Meta permissions were not granted. Reconnect and approve the requested permissions.",
  token_expired: "Meta rejected the token. Reconnect this channel.",
  token_exchange_failed: "Meta could not complete authorization. Start the connection again.",
  no_instagram_account: "No accessible Instagram Professional account was found. Use a Business or Creator account.",
  webhook_subscription_failed: "Meta could not confirm webhooks. Ask your administrator to check the app configuration, then reconnect.",
  account_already_connected_to_another_workspace: "This account is already connected to another workspace.",
  disconnect_before_replacing: "Disconnect the current account before connecting a different account.",
  data_deletion_pending: "Account data deletion is still running. Connect again after it finishes.",
  rate_limited: "Meta temporarily limited requests. Wait and try again.",
};
function errorText(error: unknown) {
  const e = error as { response?: { data?: { detail?: string; message?: string } }; message?: string };
  return e.response?.data?.detail || e.response?.data?.message || e.message || "The connection could not be completed. Please try again.";
}
function dateLabel(value?: string | null) {
  if (!value) return "Not yet";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Not yet" : date.toLocaleString();
}

export function ChannelsDashboard() {
  const health = useIntegrationHealth();
  const forms = useLeadForms();
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<Channel | null>(null);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<Channel | null>(null);
  const [manage, setManage] = useState<Channel | null>(null);
  const [signupOpen, setSignupOpen] = useState(false);
  const [signup, setSignup] = useState<SignupConfig | null>(null);
  const [launching, setLaunching] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const callbackHandled = useRef(false);

  useEffect(() => () => { abort.current?.abort(); }, []);
  useEffect(() => {
    if (callbackHandled.current) return;
    const failure = params.get("error"), success = params.get("integration_success");
    if (!failure && !success) return;
    callbackHandled.current = true;
    const clean = new URLSearchParams(params);
    ["error", "provider", "integration_success"].forEach(key => clean.delete(key));
    setParams(clean, { replace: true });
    if (failure) toast.error(callbackErrors[failure] || "Meta could not complete this connection. Please try again.");
    if (success === "instagram" || success === "whatsapp") {
      void health.refetch().then(result => {
        if (result.data?.[success].connection_status === "CONNECTED") toast.success(`${names[success]} connected successfully.`);
        else toast.info("Authorization returned. Check the channel status before sending messages.");
      });
    }
  }, [params, setParams, health.refetch]);

  async function connect(channel: Channel) {
    setError(""); setBusy(channel);
    try {
      if (channel === "instagram") {
        const { data } = await apiClient.get("/integrations/oauth/instagram/login/");
        const url = new URL(data.url);
        if (url.protocol !== "https:" || url.hostname !== "www.instagram.com"
          || url.pathname !== "/oauth/authorize" || url.username || url.password || url.port || url.hash) throw new Error("Invalid Meta authorization URL.");
        window.location.assign(url.href);
      } else {
        setSignupOpen(true); setSignup(null);
        const { data } = await apiClient.get<SignupConfig>("/integrations/whatsapp/connect/");
        await prepareMetaSignup(data); setSignup(data); setBusy(null);
      }
    } catch (e) { setError(errorText(e)); setBusy(null); setSignupOpen(false); }
  }

  function launchWhatsApp() {
    if (!signup) return;
    setLaunching(true); setBusy("whatsapp"); setError("");
    abort.current = new AbortController();
    // Launch synchronously from this click; backend completion starts after Meta returns.
    const authorization = launchMetaSignup(signup, abort.current.signal);
    void authorization.then(async result => {
      await apiClient.post("/integrations/whatsapp/complete/", { ...result, state: signup.state }, { timeout: 120000 });
      const refreshed = await health.refetch();
      if (refreshed.data?.whatsapp.connection_status === "CONNECTED") toast.success("WhatsApp connected successfully.");
      else toast.info("Check the updated WhatsApp connection status before sending messages.");
    }).catch(e => setError(errorText(e))).finally(() => { setLaunching(false); setBusy(null); setSignupOpen(false); setSignup(null); });
  }

  async function disconnect() {
    if (!confirm) return;
    setBusy(confirm); setError("");
    try {
      await apiClient.post(`/integrations/${confirm}/disconnect/`);
      toast.success(`${names[confirm]} disconnected.`); setConfirm(null); setManage(null); await health.refetch();
    } catch (e) { setError(errorText(e)); } finally { setBusy(null); }
  }
  async function verify(channel: Channel) {
    setBusy(channel); setError("");
    try {
      await apiClient.post(`/integrations/${channel}/verify/`, {}, { timeout: 120000 });
      const result = await health.refetch();
      if (result.data?.[channel].connection_status === "CONNECTED") toast.success(`${names[channel]} connection verified.`);
      else setError(result.data?.[channel].diagnostic || "Connection could not be verified.");
    } catch (e) { setError(errorText(e)); } finally { setBusy(null); }
  }
  const managed = manage ? health.data?.[manage] : undefined;
  return <PageContainer>
    <PageHeader title="Channels" description="Connect Instagram, WhatsApp, and website forms to your Nextora inbox." />
    {error && <p role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">{error}</p>}
    {health.isLoading ? <LoadingSkeleton rows={4} /> : health.isError || !health.data ?
      <ErrorState code="internal_server_error" title="Could not load channels" message="Retry to check your connection status." onRetry={() => health.refetch()} /> :
      <div className="grid grid-cols-1 gap-6 mt-6 md:grid-cols-2 xl:grid-cols-3">
        {(["instagram", "whatsapp"] as const).map(channel => {
          const info = health.data[channel];
          const connected = info.connection_status === "CONNECTED";
          const disconnected = info.connection_status === "DISCONNECTED";
          const Icon = channel === "instagram" ? Camera : MessageCircle;
          const labels: Record<string, string> = { CONNECTED: "Connected", DISCONNECTED: "Disconnected", TOKEN_EXPIRED: "Token expired", PERMISSION_REQUIRED: "Reauthorization required", CONFIGURED_UNVERIFIED: "Verification needed", CONFIGURATION_REQUIRED: "Setup needed", ERROR: "Connection error" };
          return <Card key={channel} className="flex flex-col">
            <CardHeader className="space-y-3">
              <CardTitle className="flex items-center gap-2 text-xl"><Icon className="h-5 w-5 shrink-0" />{channel === "instagram" ? "Instagram Direct" : "WhatsApp Cloud API"}</CardTitle>
              <Badge className={`w-fit ${connected ? "bg-green-100 text-green-800" : "bg-slate-100 text-slate-700"}`}>
                {busy === channel ? "Connecting / updating…" : labels[info.connection_status] || "Connection error"}
              </Badge>
              <CardDescription>{channel === "instagram" ? "Receive and reply to Instagram DMs." : "Receive WhatsApp conversations and send supported replies."}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-1 flex-col gap-4">
              {(info.username || info.display_phone_number) && <div><p className="font-medium">{channel === "instagram" ? `@${info.username}` : info.display_phone_number}</p><p className="text-sm text-slate-500">{info.verified_name || info.business_name || info.name}</p></div>}
              <p className="text-sm text-slate-500">{info.diagnostic}</p>
              <div className="mt-auto flex flex-wrap gap-2 pt-3">
                {!connected && <Button disabled={!!busy} onClick={() => connect(channel)} className="w-full">{busy === channel ? <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Connecting…</> : `${disconnected ? "Connect" : "Reconnect"} ${names[channel]}`}</Button>}
                {connected && <Button onClick={() => navigate(`/app/conversations?channel=${channel.toUpperCase()}`)} className="flex-1">Open inbox</Button>}
                {!disconnected && <><Button variant="outline" onClick={() => setManage(channel)}>Manage</Button><Button variant="outline" disabled={!!busy} onClick={() => setConfirm(channel)}>Disconnect</Button></>}
              </div>
            </CardContent>
          </Card>;
        })}
        <Card className="flex flex-col"><CardHeader className="space-y-3"><CardTitle className="flex gap-2 items-center text-xl"><Globe className="h-5 w-5" />Website Forms</CardTitle><Badge className="w-fit" variant="outline">{forms.isError ? "Unavailable" : forms.isLoading ? "Loading…" : forms.data?.some((f: { is_active: boolean }) => f.is_active) ? "Active" : "Not configured"}</Badge><CardDescription>Capture inquiries from your website.</CardDescription></CardHeader><CardContent className="flex flex-1 flex-col gap-4"><p className="text-sm text-slate-500">Create a public form and embed it on your website to send new inquiries to Nextora.</p><Button className="mt-auto" onClick={() => navigate("/app/settings/website")}>{forms.data?.length ? "Manage forms" : "Create form"}</Button></CardContent></Card>
      </div>}
    <Dialog open={!!confirm} onOpenChange={open => { if (!open && !busy) setConfirm(null); }}><DialogContent><DialogHeader><DialogTitle>Disconnect {confirm ? names[confirm] : "channel"}?</DialogTitle><DialogDescription>New messages and automated replies will stop for this channel. Your existing customers, leads, and conversation history will remain available.</DialogDescription></DialogHeader><DialogFooter><Button variant="outline" disabled={!!busy} onClick={() => setConfirm(null)}>Cancel</Button><Button disabled={!!busy} onClick={disconnect}>{busy ? "Disconnecting…" : "Confirm disconnect"}</Button></DialogFooter></DialogContent></Dialog>
    <Dialog open={!!manage} onOpenChange={open => { if (!open) setManage(null); }}><DialogContent><DialogHeader><DialogTitle>Manage {manage ? names[manage] : "channel"}</DialogTitle><DialogDescription>{managed?.diagnostic}</DialogDescription></DialogHeader><dl className="space-y-3 text-sm"><div><dt className="text-slate-500">Last verified</dt><dd>{dateLabel(managed?.last_verified_at)}</dd></div><div><dt className="text-slate-500">Last message event</dt><dd>{dateLabel(managed?.last_event_time)}</dd></div><div><dt className="text-slate-500">Webhook subscription</dt><dd>{managed?.webhook_status}</dd></div></dl><DialogFooter><Button variant="outline" disabled={!!busy} onClick={() => manage && connect(manage)}>Reconnect</Button><Button disabled={!!busy} onClick={() => manage && verify(manage)}>{busy ? "Checking…" : "Check connection"}</Button></DialogFooter></DialogContent></Dialog>
    <Dialog open={signupOpen} onOpenChange={open => { if (!open && !launching) { setSignupOpen(false); setSignup(null); } }}><DialogContent><DialogHeader><DialogTitle>Connect WhatsApp</DialogTitle><DialogDescription>Continue to Meta to choose your business, WhatsApp account, and phone number. Nextora will verify the connection when you return.</DialogDescription></DialogHeader>{!signup && <p className="text-sm flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />Preparing secure Meta login…</p>}<DialogFooter><Button variant="outline" onClick={() => { abort.current?.abort(); setSignupOpen(false); setSignup(null); }}>Cancel</Button><Button disabled={!signup || launching} onClick={launchWhatsApp}>{launching ? "Complete the Meta popup…" : "Continue with Meta"}</Button></DialogFooter></DialogContent></Dialog>
  </PageContainer>;
}
