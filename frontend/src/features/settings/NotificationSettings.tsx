import { Bell, Mail } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

export default function NotificationSettings() {
  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-lg font-medium text-slate-900">Notification Preferences</h2>
        <p className="text-sm text-slate-500 mt-1">
          Control how and when you receive alerts from V4 Studio. 
          <span className="font-semibold text-amber-600 ml-1">Note: Push notifications are currently in development.</span>
        </p>
      </div>

      <Card className="opacity-75">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-slate-500" />
            <CardTitle>Email Notifications</CardTitle>
          </div>
          <CardDescription>
            Alerts sent directly to your account email address.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-slate-700">New Lead Captured</Label>
              <p className="text-sm text-slate-500">Receive an email when a new lead submits a website form.</p>
            </div>
            <Switch disabled checked={false} />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-slate-700">New Conversation Message</Label>
              <p className="text-sm text-slate-500">Receive an email when a lead replies on WhatsApp or Instagram.</p>
            </div>
            <Switch disabled checked={false} />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-slate-700">Lead Assignment</Label>
              <p className="text-sm text-slate-500">Receive an email when a team member assigns a lead to you.</p>
            </div>
            <Switch disabled checked={false} />
          </div>
        </CardContent>
      </Card>

      <Card className="opacity-75">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-slate-500" />
            <CardTitle>In-App Notifications</CardTitle>
          </div>
          <CardDescription>
            Alerts shown within the V4 Studio dashboard interface.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-slate-700">New Lead Captured</Label>
              <p className="text-sm text-slate-500">Show a toast alert when a new lead is captured.</p>
            </div>
            <Switch disabled checked={false} />
          </div>
          
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-slate-700">New Conversation Message</Label>
              <p className="text-sm text-slate-500">Show a badge counter on the Inbox tab for new messages.</p>
            </div>
            <Switch disabled checked={false} />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="text-base text-slate-700">Lead Assignment</Label>
              <p className="text-sm text-slate-500">Show a toast alert when a lead is assigned to you.</p>
            </div>
            <Switch disabled checked={false} />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
