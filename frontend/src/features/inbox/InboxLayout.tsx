import { useState } from "react";
import { InboxConversationList } from "./components/InboxConversationList";
import { InboxMessageHistory } from "./components/InboxMessageHistory";
import { InboxLeadPanel } from "./components/InboxLeadPanel";
import { MessageCircle, ArrowLeft, Info, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function InboxLayout() {
  const [selectedConversationId, setSelectedConversationId] = useState<string | null>(null);
  const [showMobileDetails, setShowMobileDetails] = useState(false);

  return (
    <div className="h-[calc(100vh-64px)] flex bg-slate-50 border-t border-slate-200 overflow-hidden relative">
      
      {/* 
        Left Sidebar: Conversation List 
        Visible if no conversation is selected (on mobile), or always visible on tablet/desktop (md:flex)
      */}
      <div className={`
        ${selectedConversationId ? 'hidden md:flex' : 'flex'}
        w-full md:w-[300px] lg:w-[320px] xl:w-[350px] border-r border-slate-200 bg-white flex-col h-full shrink-0 z-10
      `}>
        <InboxConversationList
          selectedId={selectedConversationId}
          onSelect={(id) => {
            setSelectedConversationId(id);
            setShowMobileDetails(false);
          }}
        />
      </div>

      {/* Center & Right Panes */}
      {selectedConversationId ? (
        <div className={`
          ${!selectedConversationId ? 'hidden md:flex' : 'flex'}
          flex-1 overflow-hidden relative
        `}>
          
          {/* 
            Center Pane: Message History 
            Hidden on mobile if showing details. Always visible on md (tablet) and lg (desktop).
          */}
          <div className={`
            ${showMobileDetails ? 'hidden md:flex' : 'flex'}
            flex-1 flex-col bg-white min-w-0
          `}>
            {/* Mobile Header for Center Pane */}
            <div className="lg:hidden h-14 border-b border-slate-100 bg-white flex items-center justify-between px-4 shrink-0">
              <Button variant="ghost" size="sm" onClick={() => setSelectedConversationId(null)} className="md:hidden text-slate-500 p-0 h-auto hover:bg-transparent">
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
              <div className="md:hidden"></div> {/* Spacer to keep Info button on right if Back button is hidden */}
              <Button variant="ghost" size="icon" onClick={() => setShowMobileDetails(true)} className="text-slate-500 h-8 w-8 ml-auto">
                <Info className="h-4 w-4" />
              </Button>
            </div>
            
            <InboxMessageHistory conversationId={selectedConversationId} />
          </div>

          {/* 
            Right Sidebar: Lead Details 
            Shows as full screen on mobile when showMobileDetails is true, 
            Shows as full screen overlay on tablet when showMobileDetails is true,
            Shows as fixed right column on desktop (lg).
          */}
          <div className={`
            ${showMobileDetails ? 'flex absolute inset-0 z-20 bg-slate-50' : 'hidden lg:flex'}
            w-full lg:w-[300px] xl:w-[320px] lg:relative lg:inset-auto border-l border-slate-200 bg-slate-50 flex-col h-full shrink-0
          `}>
            {/* Mobile/Tablet Header for Right Pane */}
            <div className="lg:hidden h-14 border-b border-slate-200 bg-white flex items-center justify-between px-4 shrink-0 shadow-sm">
              <span className="font-medium text-slate-800">Details</span>
              <Button variant="ghost" size="icon" onClick={() => setShowMobileDetails(false)} className="text-slate-500 h-8 w-8 bg-slate-100 hover:bg-slate-200 rounded-full">
                <X className="h-4 w-4" />
              </Button>
            </div>
            <div className="flex-1 overflow-y-auto">
              <InboxLeadPanel conversationId={selectedConversationId} />
            </div>
          </div>
          
        </div>
      ) : (
        <div className="hidden md:flex flex-1 items-center justify-center bg-slate-50 text-slate-400">
          <div className="flex flex-col items-center gap-3">
            <div className="h-16 w-16 rounded-full bg-slate-100 flex items-center justify-center">
              <MessageCircle className="h-8 w-8 text-slate-300" />
            </div>
            <p>Select a conversation to start messaging</p>
          </div>
        </div>
      )}
    </div>
  );
}
