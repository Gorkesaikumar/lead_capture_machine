import { useEffect, useState, useRef } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { apiClient } from "@/api/client";
import { AuthLayout } from "./AuthLayout";
import { Loader2, CheckCircle2, XCircle } from "lucide-react";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMessage, setErrorMessage] = useState("");
  const effectRan = useRef(false);

  useEffect(() => {
    // Prevent double-execution in React strict mode
    if (effectRan.current) return;
    effectRan.current = true;

    if (!token) {
      setStatus("error");
      setErrorMessage("Verification token is missing.");
      return;
    }

    const verifyToken = async () => {
      try {
        // NOTE: Using actual backend API. If endpoint doesn't exist, this will gracefully catch the 404/501 error.
        await apiClient.post("/auth/email/verify/", { token });
        setStatus("success");
      } catch (err: any) {
        const statusCode = err.response?.status;
        const serverMsg =
          err.response?.data?.message ||
          err.response?.data?.errors?.detail ||
          err.response?.data?.detail;

        setStatus("error");
        
        if (statusCode === 404 || statusCode === 501) {
          setErrorMessage("Email verification is currently not supported by the backend.");
        } else if (statusCode === 400) {
          setErrorMessage(serverMsg || "Invalid or expired verification token.");
        } else {
          setErrorMessage(serverMsg || "A network error occurred while verifying your email.");
        }
      }
    };

    verifyToken();
  }, [token]);

  return (
    <AuthLayout
      title="Email Verification"
      description="Verifying your email address..."
      footer={
        <Link to="/login" className="text-slate-900 font-medium hover:underline">
          Back to login
        </Link>
      }
    >
      <div className="flex flex-col items-center justify-center py-6 text-center">
        {status === "loading" && (
          <>
            <Loader2 className="h-10 w-10 animate-spin text-slate-300 mb-4" />
            <p className="text-sm text-slate-600">Please wait while we verify your email...</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="h-12 w-12 rounded-full bg-emerald-100 flex items-center justify-center mb-4">
              <CheckCircle2 className="h-6 w-6 text-emerald-600" />
            </div>
            <h3 className="text-lg font-medium text-slate-900 mb-2">Email Verified</h3>
            <p className="text-sm text-slate-600">
              Your email address has been successfully verified. You can now log in to your account.
            </p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="h-12 w-12 rounded-full bg-rose-100 flex items-center justify-center mb-4">
              <XCircle className="h-6 w-6 text-rose-600" />
            </div>
            <h3 className="text-lg font-medium text-rose-900 mb-2">Verification Failed</h3>
            <p className="text-sm text-rose-600">
              {errorMessage}
            </p>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
