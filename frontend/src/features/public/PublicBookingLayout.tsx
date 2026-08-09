import { Outlet } from "react-router-dom";
import { Camera } from "lucide-react";

export default function PublicBookingLayout() {
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <header className="bg-white border-b border-slate-200 py-4 px-6 flex items-center justify-center sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="bg-slate-900 p-2 rounded-lg">
            <Camera className="w-5 h-5 text-white" />
          </div>
          <span className="font-semibold text-lg text-slate-900 tracking-tight">Studio Booking</span>
        </div>
      </header>
      
      <main className="flex-1 w-full max-w-md mx-auto p-4 md:p-6 lg:max-w-lg">
        <Outlet />
      </main>
    </div>
  );
}

