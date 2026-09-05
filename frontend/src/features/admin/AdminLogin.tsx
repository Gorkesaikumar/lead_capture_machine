import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Lock, Mail, ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/api/client";
import { isAxiosError } from "axios";

export default function AdminLogin() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage("");

    let verifyingSession = false;
    try {
      const response = await apiClient.post("/auth/login/", {
        email: email.trim(),
        password,
      });
      const token = response.data?.data?.token;
      if (response.data?.status === "success" && typeof token === "string" && token.trim()) {
        verifyingSession = true;
        await login(token);
        navigate("/admin", { replace: true });
      } else {
        setErrorMessage("Authentication service returned an invalid response.");
      }
    } catch (err: unknown) {
      const status = isAxiosError(err) ? err.response?.status : undefined;
      // Never display raw server messages: proxy and application errors may
      // contain internal details and do not imply an incorrect password.
      if (verifyingSession) {
        setErrorMessage("Unable to verify your session. Please try again.");
      } else if (status === 401) {
        setErrorMessage("Invalid email or password.");
      } else if (status === 403) {
        setErrorMessage("You do not have administrator access.");
      } else if (status === 404 || status === 405) {
        setErrorMessage("Authentication endpoint is unavailable.");
      } else if (status === 429) {
        setErrorMessage("Too many sign-in attempts. Please wait a minute and try again.");
      } else if (status && status >= 500) {
        setErrorMessage("Authentication service is temporarily unavailable.");
      } else if (status === 400) {
        setErrorMessage("Please check your email and password.");
      } else if (isAxiosError(err) && !err.response) {
        setErrorMessage("Unable to connect to the server.");
      } else {
        setErrorMessage("Unable to complete sign in. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-slate-900 relative overflow-hidden">
      {/* Subtle Background Accent Orbs */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-gradient-to-tr from-rose-200/40 via-purple-200/30 to-indigo-100/50 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-md w-full space-y-8 relative z-10 animate-in fade-in duration-300">
        {/* Header Branding */}
        <div className="text-center space-y-3">
          <img src="/lead.png" alt="Nextora" className="h-24 w-auto object-contain mx-auto" />
          <h1 className="text-3xl font-black tracking-tight text-slate-900 flex items-center justify-center gap-2">
            Nextora Admin <Sparkles className="h-5 w-5 text-amber-500 fill-amber-400" />
          </h1>
          <p className="text-xs text-slate-500 font-bold uppercase tracking-widest">
            Super Admin Control Center
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white border border-slate-200/80 rounded-3xl p-8 shadow-xl shadow-slate-200/50 space-y-6">
          {errorMessage && (
            <div role="alert" className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs font-semibold flex items-center gap-2">
              <span aria-hidden="true">⚠️</span>
              <span>{errorMessage}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Admin Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
                <Input
                  type="email"
                  required
                  placeholder="admin@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-10 bg-slate-50 border-slate-200 text-slate-900 text-sm h-11 rounded-xl focus:bg-white focus:border-rose-500 focus:ring-rose-500"
                />
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Master Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3.5 h-4 w-4 text-slate-400" />
                <Input
                  type="password"
                  required
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-10 bg-slate-50 border-slate-200 text-slate-900 text-sm h-11 rounded-xl focus:bg-white focus:border-rose-500 focus:ring-rose-500"
                />
              </div>
            </div>

            <Button
              type="submit"
              disabled={isLoading}
              className="w-full bg-gradient-to-r from-rose-500 via-purple-600 to-indigo-600 hover:from-rose-600 hover:to-indigo-700 text-white font-bold h-11 rounded-xl shadow-lg shadow-purple-500/25 transition-all"
            >
              {isLoading ? "Authenticating..." : "Sign In to Admin Panel"}
              {!isLoading && <ArrowRight className="h-4 w-4 ml-2" />}
            </Button>
          </form>
        </div>

        <div className="text-center">
          <a
            href="/"
            className="text-xs text-slate-500 hover:text-slate-900 font-semibold transition-colors"
          >
            ← Return to Nextora Website
          </a>
        </div>
      </div>
    </div>
  );
}
