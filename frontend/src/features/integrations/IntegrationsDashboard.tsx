import { PageContainer } from "@/components/common/layout/PageContainer";
import { PageHeader } from "@/components/common/layout/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MessageCircle, AlertCircle, CheckCircle2, Clock, Camera } from "lucide-react";
import { useIntegrationHealth } from "@/api/integrations.queries";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { format } from "date-fns";

export default function IntegrationsDashboard() {
  const { data: health, isLoading, isError } = useIntegrationHealth();

  if (isLoading) {
    return (
      <PageContainer>
        <PageHeader title="Integrations" description="Manage connections to external messaging platforms." />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
          <LoadingSkeleton rows={4} />
          <LoadingSkeleton rows={4} />
        </div>
      </PageContainer>
    );
  }

  if (isError || !health) {
    return (
      <PageContainer>
        <PageHeader title="Integrations" description="Manage connections to external messaging platforms." />
        <div className="p-12 text-center text-red-500 bg-red-50 rounded-lg mt-6">
          Failed to load integration health. Ensure backend is reachable.
        </div>
      </PageContainer>
    );
  }

  const ig = health.instagram;
  const wa = health.whatsapp;

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "Never";
    return format(new Date(dateStr), "MMM d, yyyy h:mm a");
  };

  return (
    <PageContainer>
      <PageHeader 
        title="Integrations" 
        description="Monitor connectivity and webhook health for external platforms."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6">
        {/* Instagram Card */}
        <Card className={ig.connection_status === "CONNECTED" ? "border-slate-200" : "border-red-200 bg-red-50/30"}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-xl">
                <Camera className="h-5 w-5 text-slate-900" />
                Instagram Direct
              </CardTitle>
              <CardDescription>Receive and reply to Instagram DMs</CardDescription>
            </div>
            {ig.connection_status === "CONNECTED" ? (
              <Badge className="bg-green-100 text-green-800 hover:bg-green-100"><CheckCircle2 className="w-3 h-3 mr-1" /> Connected</Badge>
            ) : (
              <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" /> Disconnected</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-1">
                <span className="text-slate-500 flex items-center gap-1"><Clock className="w-3 h-3" /> Webhook Status</span>
                <p className="font-medium">{ig.webhook_status}</p>
              </div>
              <div className="space-y-1">
                <span className="text-slate-500">Last Event Received</span>
                <p className="font-medium">{formatDate(ig.last_event_time)}</p>
              </div>
              <div className="space-y-1 col-span-2">
                <span className="text-slate-500">Last Successful Sync</span>
                <p className="font-medium text-slate-900">{formatDate(ig.last_successful_communication)}</p>
              </div>

              {/* Webhook Diagnostics */}
              <div className="col-span-2 mt-2 p-3 bg-slate-50 rounded border border-slate-100 grid grid-cols-3 gap-2">
                <div className="space-y-1">
                   <span className="text-xs text-slate-500 uppercase tracking-wider">Total Events</span>
                   <p className="font-semibold text-slate-700">{ig.events_received_count}</p>
                </div>
                <div className="space-y-1">
                   <span className="text-xs text-slate-500 uppercase tracking-wider">Test Events</span>
                   <p className="font-semibold text-slate-700">{ig.test_events_count}</p>
                </div>
                <div className="space-y-1">
                   <span className="text-xs text-slate-500 uppercase tracking-wider">Real Events</span>
                   <p className="font-semibold text-emerald-600">{ig.real_message_events_count}</p>
                </div>
              </div>

            </div>
          </CardContent>
          {ig.requires_reconnect && (
            <CardFooter className="bg-slate-50 border-t pt-4">
              <div className="text-sm text-amber-700 flex-1">
                Missing environment credentials (META_APP_SECRET or INSTAGRAM_ACCESS_TOKEN).
              </div>
            </CardFooter>
          )}
        </Card>

        {/* WhatsApp Card */}
        <Card className={wa.connection_status === "CONNECTED" ? "border-slate-200" : "border-red-200 bg-red-50/30"}>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2 text-xl">
                <MessageCircle className="h-5 w-5 text-slate-900" />
                WhatsApp Cloud API
              </CardTitle>
              <CardDescription>Business messaging and booking alerts</CardDescription>
            </div>
            {wa.connection_status === "CONNECTED" ? (
              <Badge className="bg-green-100 text-green-800 hover:bg-green-100"><CheckCircle2 className="w-3 h-3 mr-1" /> Connected</Badge>
            ) : (
              <Badge variant="destructive"><AlertCircle className="w-3 h-3 mr-1" /> Disconnected</Badge>
            )}
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-1">
                <span className="text-slate-500 flex items-center gap-1"><Clock className="w-3 h-3" /> Webhook Status</span>
                <p className="font-medium">{wa.webhook_status}</p>
              </div>
              <div className="space-y-1">
                <span className="text-slate-500">Last Event Received</span>
                <p className="font-medium">{formatDate(wa.last_event_time)}</p>
              </div>
              <div className="space-y-1 col-span-2">
                <span className="text-slate-500">Last Successful Sync</span>
                <p className="font-medium text-slate-900">{formatDate(wa.last_successful_communication)}</p>
              </div>
              
              {/* Webhook Diagnostics */}
              <div className="col-span-2 mt-2 p-3 bg-slate-50 rounded border border-slate-100 grid grid-cols-3 gap-2">
                <div className="space-y-1">
                   <span className="text-xs text-slate-500 uppercase tracking-wider">Total Events</span>
                   <p className="font-semibold text-slate-700">{wa.events_received_count}</p>
                </div>
                <div className="space-y-1">
                   <span className="text-xs text-slate-500 uppercase tracking-wider">Test Events</span>
                   <p className="font-semibold text-slate-700">{wa.test_events_count}</p>
                </div>
                <div className="space-y-1">
                   <span className="text-xs text-slate-500 uppercase tracking-wider">Real Events</span>
                   <p className="font-semibold text-emerald-600">{wa.real_message_events_count}</p>
                </div>
              </div>

            </div>
          </CardContent>
          {wa.requires_reconnect && (
            <CardFooter className="bg-slate-50 border-t pt-4">
              <div className="text-sm text-amber-700 flex-1">
                Missing environment credentials (WHATSAPP_ACCESS_TOKEN or META_APP_SECRET).
              </div>
            </CardFooter>
          )}
        </Card>
      </div>
    </PageContainer>
  );
}


