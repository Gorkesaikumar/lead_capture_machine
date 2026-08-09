import { AlertTriangle, WifiOff, ServerCrash, ShieldAlert } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message?: string;
  /** Machine-readable code from parseError(), used to select appropriate icon and copy */
  code?: string;
  onRetry?: () => void;
}

function resolveDefaults(code?: string): { icon: React.ReactNode; title: string; message: string } {
  switch (code) {
    case "network_error":
      return {
        icon: <WifiOff className="h-8 w-8 text-amber-500" />,
        title: "No connection",
        message: "Unable to connect to the server. Please check your internet connection.",
      };
    case "request_timeout":
      return {
        icon: <WifiOff className="h-8 w-8 text-amber-500" />,
        title: "Request timed out",
        message: "The server took too long to respond. Please try again.",
      };
    case "permission_denied":
      return {
        icon: <ShieldAlert className="h-8 w-8 text-amber-500" />,
        title: "Access denied",
        message: "You do not have permission to view this resource.",
      };
    case "internal_server_error":
    case "external_service_error":
      return {
        icon: <ServerCrash className="h-8 w-8 text-rose-500" />,
        title: "Server error",
        message: "A server error occurred. Our team has been notified. Please try again later.",
      };
    default:
      return {
        icon: <AlertTriangle className="h-8 w-8 text-rose-500" />,
        title: "Something went wrong",
        message: "An unexpected error occurred. Please try again.",
      };
  }
}

export function ErrorState({ title, message, code, onRetry }: ErrorStateProps) {
  const defaults = resolveDefaults(code);
  const displayTitle = title ?? defaults.title;
  const displayMessage = message ?? defaults.message;
  const isWarning = code === "network_error" || code === "request_timeout" || code === "permission_denied";

  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center rounded-lg min-h-[200px] border ${
      isWarning
        ? "bg-amber-50/30 border-amber-100"
        : "bg-rose-50/30 border-rose-100"
    }`}>
      <div className="mb-3">{defaults.icon}</div>
      <h3 className={`text-base font-medium ${isWarning ? "text-amber-900" : "text-rose-900"}`}>
        {displayTitle}
      </h3>
      <p className={`text-sm mt-1 max-w-md ${isWarning ? "text-amber-600/80" : "text-rose-600/80"}`}>
        {displayMessage}
      </p>
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="outline"
          className={`mt-4 ${isWarning ? "border-amber-200 text-amber-700 hover:bg-amber-50" : "border-rose-200 text-rose-700 hover:bg-rose-50"}`}
        >
          Try Again
        </Button>
      )}
    </div>
  );
}