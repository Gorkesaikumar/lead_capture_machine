import { Menu, LogOut, User as UserIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/contexts/AuthContext";
import { useRealtime } from "@/contexts/RealtimeContext";

export default function Header({ toggleMobileNav }: { toggleMobileNav: () => void }) {
  const { user, logout } = useAuth();
  const { status } = useRealtime();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-gray-200 bg-white px-4 md:px-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="md:hidden text-slate-500" onClick={toggleMobileNav}>
          <Menu className="h-5 w-5" />
          <span className="sr-only">Toggle menu</span>
        </Button>
        <div className="hidden md:flex items-center text-sm font-medium text-slate-500">
          Photo Studio / Dashboard
        </div>
      </div>
      
      <div className="flex items-center gap-3 md:gap-4">
        {/* Real-time Connection Indicator */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border bg-slate-50">
          {status === "CONNECTED" ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-emerald-700 hidden sm:inline">Live</span>
            </>
          ) : status === "RECONNECTING" || status === "CONNECTING" ? (
            <>
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
              </span>
              <span className="text-amber-700 hidden sm:inline">Connecting...</span>
            </>
          ) : (
            <>
              <span className="inline-flex rounded-full h-2 w-2 bg-slate-400"></span>
              <span className="text-slate-500 hidden sm:inline">Offline</span>
            </>
          )}
        </div>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full bg-slate-100 hover:bg-slate-200 border border-slate-200 shadow-sm">
              <UserIcon className="h-5 w-5 text-slate-600" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56 bg-white">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user?.name || 'Administrator'}</p>
                <p className="text-xs leading-none text-slate-500">{user?.email}</p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => logout()} className="text-rose-600 focus:bg-rose-50 focus:text-rose-700 cursor-pointer">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}