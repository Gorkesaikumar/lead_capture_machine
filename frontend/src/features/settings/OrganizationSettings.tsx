import { useState, useEffect, useMemo } from "react";
import { useCurrentOrganization, useUpdateOrganization } from "@/api/organizations.queries";
import { useAuth } from "@/contexts/AuthContext";
import { useTeamMembers } from "@/api/team.queries";
import { toast } from "sonner";
import { Loader2, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";

const DEFAULT_TIMEZONE = "Asia/Kolkata";
const availableTimezones = typeof Intl.supportedValuesOf === "function"
  ? Intl.supportedValuesOf("timeZone")
  : ["America/Los_Angeles", "America/New_York", "Europe/London", "Europe/Paris", "Asia/Dubai", "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney"];

function timezoneLabel(timezone: string) {
  try {
    const offset = new Intl.DateTimeFormat("en", {
      timeZone: timezone,
      timeZoneName: "longOffset",
    }).formatToParts(new Date()).find(part => part.type === "timeZoneName")?.value.replace("GMT", "UTC") || "UTC";
    const name = timezone === DEFAULT_TIMEZONE
      ? "India Standard Time — Asia/Kolkata"
      : timezone.replaceAll("_", " ");
    return `(${offset}) ${name}`;
  } catch {
    return timezone;
  }
}

export default function OrganizationSettings() {
  const { user } = useAuth();
  const { data: organization, isLoading: orgLoading, error: orgError } = useCurrentOrganization();
  const { data: members = [], isLoading: membersLoading } = useTeamMembers();
  const updateOrganization = useUpdateOrganization();

  const [formData, setFormData] = useState({
    name: "",
    contact_email: "",
    contact_phone: "",
    timezone: DEFAULT_TIMEZONE,
  });

  const timezoneOptions = useMemo(() => Array.from(new Set([
    DEFAULT_TIMEZONE,
    "UTC",
    ...availableTimezones.filter(zone => zone !== "Asia/Calcutta").sort(),
    formData.timezone,
  ])).map(value => ({ value, label: timezoneLabel(value) })), [formData.timezone]);

  useEffect(() => {
    if (organization) {
      setFormData({
        name: organization.name || "",
        contact_email: organization.contact_email || "",
        contact_phone: organization.contact_phone || "",
        timezone: organization.timezone || DEFAULT_TIMEZONE,
      });
    }
  }, [organization]);

  const currentUserMembership = members.find(m => m.user.email === user?.email);
  const isAuthorized = currentUserMembership?.role === "OWNER" || currentUserMembership?.role === "ADMIN";

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAuthorized) {
      toast.error("You do not have permission to update organization settings.");
      return;
    }

    try {
      await updateOrganization.mutateAsync(formData);
      toast.success("Organization settings saved successfully");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to save settings");
    }
  };

  if (orgLoading || membersLoading) {
    return <LoadingSkeleton rows={4} />;
  }

  if (orgError) {
    return <ErrorState code="internal_server_error" title="Failed to load organization" message="We could not retrieve your organization settings. Please try again." />;
  }

  return (
    <div className="flex min-h-[calc(100dvh-4rem)] w-full items-center justify-center px-4 py-8 sm:px-6 sm:py-12">
      <Card className="w-full max-w-xl">
        <CardHeader>
          <CardTitle>Organization Profile</CardTitle>
          <CardDescription>
            Manage your organization's identity and contact details.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="name">Organization Name</Label>
              <Input
                id="name"
                name="name"
                placeholder="My Studio"
                value={formData.name}
                onChange={handleChange}
                disabled={!isAuthorized}
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="contact_email">Contact Email</Label>
                <Input
                  id="contact_email"
                  name="contact_email"
                  type="email"
                  placeholder="hello@example.com"
                  value={formData.contact_email}
                  onChange={handleChange}
                  disabled={!isAuthorized}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact_phone">Contact Phone</Label>
                <Input
                  id="contact_phone"
                  name="contact_phone"
                  placeholder="+1 (555) 000-0000"
                  value={formData.contact_phone}
                  onChange={handleChange}
                  disabled={!isAuthorized}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timezone">Timezone</Label>
              <select
                id="timezone"
                name="timezone"
                value={formData.timezone}
                onChange={handleChange}
                disabled={!isAuthorized}
                aria-describedby="timezone-help"
                className="flex h-10 w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
              >
                {timezoneOptions.map(option => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
              <p id="timezone-help" className="text-xs text-slate-500">Default: India Standard Time (UTC+05:30). Offsets shown reflect current daylight saving time where applicable.</p>
            </div>
            
            {!isAuthorized && (
              <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm p-3 rounded-md">
                You must be an Admin or Owner to edit these settings.
              </div>
            )}
          </CardContent>
          <CardFooter className="border-t px-6 py-4 flex justify-end">
            <Button type="submit" disabled={!isAuthorized || updateOrganization.isPending}>
              {updateOrganization.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...
                </>
              ) : (
                <>
                  <Save className="mr-2 h-4 w-4" /> Save Changes
                </>
              )}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
