import { useNavigate } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Camera, MessageCircle, Globe } from "lucide-react";

interface Conversation {
  id: string;
  lead_name: string;
  channel: string;
  last_message_preview?: string;
  last_message_at?: string;
  status: string;
  unread_count: number;
}

const ChannelIcon = ({ channel }: { channel: string }) => {
  switch (channel?.toLowerCase()) {
    case "instagram": return <Camera className="h-4 w-4 text-pink-500" />;
    case "whatsapp": return <MessageCircle className="h-4 w-4 text-green-500" />;
    case "website": return <Globe className="h-4 w-4 text-slate-500" />;
    default: return <MessageCircle className="h-4 w-4 text-slate-400" />;
  }
};

export function RecentConversationsList({ conversations }: { conversations: Conversation[] }) {
  const navigate = useNavigate();

  return (
    <Card className="col-span-1 h-full">
      <CardHeader>
        <CardTitle className="text-lg">Recent Conversations</CardTitle>
      </CardHeader>
      <CardContent className="p-0 sm:p-6 sm:pt-0">
        {conversations.length === 0 ? (
          <div className="flex justify-center items-center h-32 text-slate-500 text-sm">
            No open conversations.
          </div>
        ) : (
          <div className="space-y-4">
            {conversations.map((conv) => (
              <div 
                key={conv.id}
                className="flex items-start gap-4 p-3 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors"
                onClick={() => navigate(`/inbox?c=${conv.id}`)}
              >
                <div className="relative">
                  <Avatar className="h-10 w-10">
                    <AvatarFallback className="bg-slate-100 text-slate-700 font-medium">
                      {conv.lead_name?.charAt(0) || "U"}
                    </AvatarFallback>
                  </Avatar>
                  <div className="absolute -bottom-1 -right-1 bg-white p-0.5 rounded-full shadow-sm">
                    <ChannelIcon channel={conv.channel} />
                  </div>
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-baseline mb-1">
                    <p className="text-sm font-medium text-slate-900 truncate pr-2">
                      {conv.lead_name}
                    </p>
                    {conv.last_message_at && (
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {formatDistanceToNow(new Date(conv.last_message_at))}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-600 truncate">
                    {conv.last_message_preview || "No messages yet"}
                  </p>
                </div>
                
                {conv.unread_count > 0 && (
                  <div className="h-5 min-w-[20px] rounded-full bg-blue-600 flex items-center justify-center px-1.5 self-center">
                    <span className="text-[10px] font-bold text-white">{conv.unread_count}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
