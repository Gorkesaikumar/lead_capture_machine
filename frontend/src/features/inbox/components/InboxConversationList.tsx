import { useSearchParams } from "react-router-dom";
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { useInboxConversations } from "@/api/conversations.queries";
import { useRealtimeEvent } from "@/contexts/RealtimeContext";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { MessageCircle, Phone, Globe, Search } from "lucide-react";

import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { ErrorState } from "@/components/common/states/ErrorState";
import { EmptyState } from "@/components/common/states/EmptyState";

interface Props {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function InboxConversationList({ selectedId, onSelect }: Props) {
  const [searchParams] = useSearchParams();
  const requestedChannel = searchParams.get("channel") || "ALL";
  const [channel, setChannel] = useState<string>(["INSTAGRAM", "WHATSAPP", "WEBSITE"].includes(requestedChannel) ? requestedChannel : "ALL");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);

  const queryParams: any = { search, page };
  if (channel !== "ALL") queryParams.channel = channel;
  if (showUnreadOnly) queryParams.unread = true;

  const { data, isLoading, error, refetch } = useInboxConversations(queryParams);

  // Real-time integration
  useRealtimeEvent("NEW_MESSAGE", () => refetch());
  useRealtimeEvent("MESSAGE_UPDATED", () => refetch());

  const conversations = data?.results || data || [];

  const getChannelIcon = (ch: string) => {
    switch (ch) {
      case "INSTAGRAM":
        return <MessageCircle className="h-4 w-4 text-pink-600" />;
      case "WHATSAPP":
        return <Phone className="h-4 w-4 text-emerald-600" />;
      case "WEBSITE":
        return <Globe className="h-4 w-4 text-blue-600" />;
      default:
        return <MessageCircle className="h-4 w-4 text-slate-400" />;
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="p-4 border-b border-slate-100 flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-slate-800">Inbox</h2>
        <div className="relative">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <Input aria-label="Search conversations" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search conversations..." className="pl-9 bg-slate-50 border-slate-200 text-sm h-9" />
        </div>
        
        <div className="flex items-center justify-between">
          <Tabs value={channel} onValueChange={value => { setChannel(value); setPage(1); }} className="w-[200px]">
            <TabsList className="w-full h-8 bg-slate-100/50">
              <TabsTrigger value="ALL" className="text-xs flex-1">All</TabsTrigger>
              <TabsTrigger value="INSTAGRAM" className="text-xs flex-1">IG</TabsTrigger>
              <TabsTrigger value="WHATSAPP" className="text-xs flex-1">WA</TabsTrigger>
              <TabsTrigger value="WEBSITE" className="text-xs flex-1">Web</TabsTrigger>
            </TabsList>
          </Tabs>
          
          <div className="flex items-center space-x-2">
            <Switch 
              id="unread-only" 
              checked={showUnreadOnly} 
              onCheckedChange={setShowUnreadOnly} 
              className="scale-75"
            />
            <Label htmlFor="unread-only" className="text-xs text-slate-500 cursor-pointer">Unread</Label>
          </div>
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <LoadingSkeleton rows={5} />
        ) : error ? (
          <div className="p-4">
            <ErrorState 
              code="internal_server_error"
              title="Failed to load conversations"
              onRetry={refetch}
            />
          </div>
        ) : conversations.length === 0 ? (
          <EmptyState 
            icon={<MessageCircle className="h-6 w-6" />}
            title="No conversations found"
            description="You don't have any conversations matching the current filters."
          />
        ) : (
          <div className="flex flex-col">
            {conversations.map((conv: any) => (
              <button
                key={conv.id}
                onClick={() => onSelect(conv.id)}
                className={`w-full text-left p-4 border-b border-slate-50 transition-colors ${
                  selectedId === conv.id ? "bg-blue-50/50" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="flex items-center gap-2">
                    <span className={`text-sm ${conv.unread_count > 0 ? "font-semibold text-slate-900" : "font-medium text-slate-700"}`}>
                      {conv.customer?.display_name || "Unknown"}
                    </span>
                    {conv.unread_count > 0 && (
                      <Badge className="bg-blue-600 hover:bg-blue-700 h-5 px-1.5 min-w-[20px] rounded-full text-[10px]">
                        {conv.unread_count}
                      </Badge>
                    )}
                  </div>
                  <span className={`text-[11px] whitespace-nowrap ${conv.unread_count > 0 ? "text-blue-600 font-medium" : "text-slate-400"}`}>
                    {conv.last_message_at
                      ? formatDistanceToNow(new Date(conv.last_message_at), { addSuffix: true })
                      : "New"}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-slate-500">
                  {getChannelIcon(conv.channel)}
                  <p className={`text-xs truncate flex-1 ${conv.unread_count > 0 ? "text-slate-700 font-medium" : "text-slate-500"}`}>
                    {conv.last_message_preview || "No messages yet"}
                  </p>
                </div>
                
                {conv.lead && (
                  <div className="mt-2 flex gap-1.5 flex-wrap">
                    <Badge variant="outline" className="text-[10px] font-normal border-slate-200 text-slate-500 bg-white">
                      {conv.lead.status_display}
                    </Badge>
                    {conv.assigned_user && (
                      <Badge variant="outline" className="text-[10px] font-normal border-slate-200 text-slate-500 bg-white">
                        {conv.assigned_user.full_name || conv.assigned_user.email}
                      </Badge>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="p-3 border-t flex items-center justify-between text-sm">
        <button disabled={page === 1} className="disabled:opacity-40" onClick={() => setPage(p => p-1)}>Previous</button>
        <span>Page {page}</span><button disabled={!data?.next} className="disabled:opacity-40" onClick={() => setPage(p => p+1)}>Next</button>
      </div>
    </div>
  );
}
