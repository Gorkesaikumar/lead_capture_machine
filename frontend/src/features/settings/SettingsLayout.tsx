import { Outlet } from "react-router-dom";

export default function SettingsLayout() {
  return (
    <div className="flex-1 w-full min-h-[calc(100vh-64px)] flex flex-col items-center">
      <Outlet />
    </div>
  );
}
