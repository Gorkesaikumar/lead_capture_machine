import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/common/states/EmptyState";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { SourceBadge } from "@/components/common/ui/SourceBadge";
import { Button } from "@/components/ui/button";
import { MessageSquare, Users } from "lucide-react";

export function RecentLeadsFeed({ leads, isLoading }: { leads: any[]; isLoading: boolean }) {
  if (isLoading) return <Card className="border-gray-200 shadow-none"><CardContent className="p-6"><LoadingSkeleton rows={3}/></CardContent></Card>;

  if (!leads || leads.length === 0) {
    return (
      <Card className="border-gray-200 shadow-none">
        <CardContent className="p-0">
          <EmptyState icon={<Users className="h-6 w-6"/>} title="No recent leads" description="New incoming inquiries will appear here." />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-gray-200 shadow-none">
      <CardHeader className="pb-3 border-b border-gray-100 flex flex-row items-center justify-between">
        <CardTitle className="text-base font-semibold text-slate-900">Recent Leads</CardTitle>
        <Button variant="ghost" size="sm" className="text-slate-500 h-8">View All</Button>
      </CardHeader>
      <CardContent className="p-0">
        <div className="divide-y divide-gray-100">
          {leads.slice(0, 5).map((lead: any) => (
            <div key={lead.id} className="flex items-center justify-between p-4 hover:bg-slate-50 transition-colors">
              <div className="flex items-center gap-4">
                <SourceBadge source={lead.source_channel || lead.source || 'other'} />
                <div className="flex flex-col">
                  <span className="font-medium text-slate-900">
                    {lead.customer?.display_name || lead.display_name || lead.instagram_username || "Instagram User"}
                  </span>
                  <span className="text-sm text-slate-500">
                    {lead.trigger_service_name || lead.trigger_phrase || lead.service?.name || lead.summary || lead.service_interest || "General Inquiry"}
                  </span>
                </div>
              </div>
              <div>
                <Button variant="outline" size="sm" className="h-8 border-gray-200 shadow-sm text-slate-600">
                  <MessageSquare className="h-3.5 w-3.5 mr-2" />
                  Reply
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}