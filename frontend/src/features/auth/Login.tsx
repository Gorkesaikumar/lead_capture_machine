import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useNavigate, Navigate, Link } from "react-router-dom";
import { apiClient } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AlertCircle, Eye, EyeOff } from "lucide-react";
import { isAxiosError } from "axios";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";
import { AuthLayout } from "./AuthLayout";

const loginSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address." }),
  password: z.string().min(1, { message: "Password is required." }),
  rememberMe: z.boolean().optional(),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function Login() {
  const { login, user, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  if (isAuthLoading) {
    return <div className="min-h-screen flex items-center justify-center p-8"><LoadingSkeleton rows={2} /></div>;
  }

  if (user) {
    return <Navigate to="/app" replace />;
  }

  const onSubmit = async (data: LoginFormValues) => {
    form.clearErrors("root");
    setIsSubmitting(true);
    try {
      const response = await apiClient.post("/auth/login/", data);
      const token = response.data?.data?.token || response.data?.token || response.data?.key;
      
      if (token) {
        // Here we could handle 'rememberMe' by using localStorage vs sessionStorage
        // But since the AuthContext uses localStorage currently, we'll just login.
        await login(token);
        navigate("/app");
      } else {
        form.setError("root", {
          message: "Unable to complete sign in. Please try again.",
        });
      }
    } catch (err: unknown) {
      const response = isAxiosError(err) ? err.response : undefined;
      const status = response?.status;
      const detail = response?.data?.message || response?.data?.detail;
      const serverMessage = typeof detail === "string" ? detail : undefined;
      let message: string;

      if (status === 401) {
        message = "Invalid email or password.";
      } else if (status === 429) {
        message = serverMessage || "Too many sign-in attempts. Please wait a minute and try again.";
      } else if (status && status >= 500) {
        message = "Sign-in service is temporarily unavailable. Please try again shortly.";
      } else if (response) {
        message = serverMessage || "Unable to sign in. Please check your details and try again.";
      } else if (isAxiosError(err)) {
        message = err.code === "ECONNABORTED" || err.code === "ETIMEDOUT"
          ? "The sign-in request timed out. Please try again."
          : "Unable to connect. Please check your internet connection and try again.";
      } else {
        message = "Unable to complete sign in. Please try again.";
      }
      form.setError("root", { type: "server", message });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome back"
      description="Sign in to your account"
      footer={
        <span>
          Don't have an account?{" "}
          <Link to="/signup" className="text-slate-900 font-medium hover:underline">
            Sign up
          </Link>
        </span>
      }
    >
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
        {form.formState.errors.root && (
          <div id="login-error" role="alert" className="flex items-start gap-2 p-3 text-sm font-medium text-rose-800 bg-rose-50 border border-rose-200 rounded-md">
            <AlertCircle aria-hidden="true" className="h-4 w-4 shrink-0 mt-0.5" />
            <span>{form.formState.errors.root.message}</span>
          </div>
        )}
        <div className="space-y-2">
          <label className="text-sm font-medium leading-none text-slate-700" htmlFor="email">
            Email
          </label>
          <Input
            id="email"
            type="email"
            placeholder="admin@studio.com"
            {...form.register("email")}
            className={form.formState.errors.email ? "border-rose-300 focus-visible:ring-rose-200" : ""}
            disabled={isSubmitting}
          />
          {form.formState.errors.email && (
            <p className="text-xs text-rose-500 font-medium">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div className="space-y-2 relative">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium leading-none text-slate-700" htmlFor="password">
              Password
            </label>
            <Link to="/forgot-password" className="text-xs text-slate-500 hover:text-slate-900 hover:underline font-medium">
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              {...form.register("password")}
              className={form.formState.errors.password ? "border-rose-300 focus-visible:ring-rose-200 pr-10" : "pr-10"}
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 focus:outline-none"
              onClick={() => setShowPassword(!showPassword)}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {form.formState.errors.password && (
            <p className="text-xs text-rose-500 font-medium">{form.formState.errors.password.message}</p>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="rememberMe"
            className="h-4 w-4 rounded border-gray-300 text-slate-900 focus:ring-slate-900"
            {...form.register("rememberMe")}
            disabled={isSubmitting}
          />
          <label
            htmlFor="rememberMe"
            className="text-sm font-medium leading-none text-slate-700 peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            Remember me
          </label>
        </div>

        <Button type="submit" className="w-full mt-2 bg-slate-900 hover:bg-slate-800 text-white" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign in"}
        </Button>
      </form>
    </AuthLayout>
  );
}
