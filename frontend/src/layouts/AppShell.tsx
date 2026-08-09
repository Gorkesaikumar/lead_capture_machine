import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";
import { Sheet, SheetContent } from "@/components/ui/sheet";

export default function AppShell() {
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);

  return (
    <div className="flex h-[100dvh] w-full overflow-hidden bg-white">
      {/* Desktop Sidebar */}
      <div className="hidden md:block h-full">
        <Sidebar />
      </div>

      {/* Mobile Sidebar (Drawer) */}
      <Sheet open={isMobileNavOpen} onOpenChange={setIsMobileNavOpen}>
        <SheetContent side="left" className="p-0 w-64">
          <Sidebar />
        </SheetContent>
      </Sheet>

      <div className="flex flex-col flex-1 min-w-0 overflow-hidden bg-slate-50">
        <Header toggleMobileNav={() => setIsMobileNavOpen(true)} />
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
