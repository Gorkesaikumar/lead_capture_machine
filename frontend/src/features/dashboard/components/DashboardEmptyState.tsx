import { useNavigate } from "react-router-dom";
import { MessageSquare, Globe, Plus, Sparkles } from "lucide-react";

export function DashboardEmptyState() {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-[50vh] px-4 py-10 bg-white rounded-2xl border border-slate-200/80 shadow-2xs">
      <div className="h-16 w-16 bg-gradient-to-br from-rose-100 to-pink-100 rounded-2xl flex items-center justify-center mb-4 text-rose-600 shadow-2xs border border-rose-200/60">
        <Sparkles className="h-8 w-8" />
      </div>

      <h2 className="text-xl font-bold text-slate-900 mb-1">No leads captured yet</h2>
      <p className="text-xs font-medium text-slate-500 text-center max-w-md mb-8 leading-relaxed">
        Connect your social channels or create a website form to start capturing leads automatically in Nextora.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full max-w-3xl">
        {/* Instagram CTA */}
        <div className="group rounded-2xl p-5 border border-slate-200/80 bg-slate-50/50 hover:bg-white hover:border-rose-200 hover:shadow-xs transition-all flex flex-col justify-between">
          <div className="text-center">
            <div className="mx-auto bg-gradient-to-tr from-amber-500 via-rose-500 to-purple-600 p-3 rounded-xl w-max mb-3 text-white shadow-2xs">
              <MessageSquare className="h-5 w-5" />
            </div>
            <h3 className="text-xs font-bold text-slate-900">Instagram Direct</h3>
            <p className="text-[11px] font-medium text-slate-500 mt-0.5">Capture leads from DMs</p>
          </div>
          <button
            onClick={() => navigate("/app/settings/channels")}
            className="mt-4 w-full py-2 px-3 text-xs font-semibold text-rose-600 bg-rose-50 hover:bg-rose-100/80 border border-rose-200/80 rounded-xl transition-colors flex items-center justify-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Connect Instagram
          </button>
        </div>

        {/* WhatsApp CTA */}
        <div className="group rounded-2xl p-5 border border-slate-200/80 bg-slate-50/50 hover:bg-white hover:border-emerald-200 hover:shadow-xs transition-all flex flex-col justify-between">
          <div className="text-center">
            <div className="mx-auto bg-emerald-500 p-3 rounded-xl w-max mb-3 text-white shadow-2xs">
              <MessageSquare className="h-5 w-5" />
            </div>
            <h3 className="text-xs font-bold text-slate-900">WhatsApp Business</h3>
            <p className="text-[11px] font-medium text-slate-500 mt-0.5">Capture leads from chats</p>
          </div>
          <button
            onClick={() => navigate("/app/settings/channels")}
            className="mt-4 w-full py-2 px-3 text-xs font-semibold text-emerald-600 bg-emerald-50 hover:bg-emerald-100/80 border border-emerald-200/80 rounded-xl transition-colors flex items-center justify-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Connect WhatsApp
          </button>
        </div>

        {/* Website CTA */}
        <div className="group rounded-2xl p-5 border border-slate-200/80 bg-slate-50/50 hover:bg-white hover:border-amber-200 hover:shadow-xs transition-all flex flex-col justify-between">
          <div className="text-center">
            <div className="mx-auto bg-amber-500 p-3 rounded-xl w-max mb-3 text-white shadow-2xs">
              <Globe className="h-5 w-5" />
            </div>
            <h3 className="text-xs font-bold text-slate-900">Website Forms</h3>
            <p className="text-[11px] font-medium text-slate-500 mt-0.5">Embed lead capture forms</p>
          </div>
          <button
            onClick={() => navigate("/app/settings/website")}
            className="mt-4 w-full py-2 px-3 text-xs font-semibold text-amber-600 bg-amber-50 hover:bg-amber-100/80 border border-amber-200/80 rounded-xl transition-colors flex items-center justify-center gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Create Form
          </button>
        </div>
      </div>
    </div>
  );
}
