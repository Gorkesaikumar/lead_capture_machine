import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "./AuthLayout";

const resetPasswordSchema = z.object({
  password: z.string().min(8, { message: "Password must be at least 8 characters." }),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

export default function ResetPassword() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Usually the token is in the URL, e.g. ?token=abc or in the path
  const token = searchParams.get("token");

  const form = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  useEffect(() => {
    if (!token) {
      toast.error("Invalid or missing reset token.");
      navigate("/login");
    }
  }, [token, navigate]);

  const onSubmit = async (data: ResetPasswordFormValues) => {
    setIsSubmitting(true);
    try {
      // NOTE: Using actual backend API. If endpoint doesn't exist, this will gracefully catch the 404/501 error.
      await apiClient.post("/auth/password/reset/confirm/", {
        token,
        password: data.password,
      });
      
      toast.success("Password reset successfully. Please log in.");
      navigate("/login");
    } catch (err: any) {
      const status = err.response?.status;
      const serverMsg =
        err.response?.data?.message ||
        err.response?.data?.errors?.detail ||
        err.response?.data?.detail;

      if (status === 404 || status === 501) {
        form.setError("root", {
          type: "manual",
          message: "Password reset is currently not supported by the backend.",
        });
      } else if (status === 400) {
        form.setError("root", {
          type: "manual",
          message: serverMsg || "Invalid or expired token.",
        });
      } else {
        form.setError("root", {
          type: "manual",
          message: serverMsg || "A network error occurred. Please try again.",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!token) return null;

  return (
    <AuthLayout
      title="Set new password"
      description="Please enter your new password"
      footer={
        <Link to="/login" className="text-slate-900 font-medium hover:underline">
          Back to login
        </Link>
      }
    >
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
        {form.formState.errors.root && (
          <div className="p-3 text-sm font-medium text-rose-800 bg-rose-50 border border-rose-100 rounded-md text-center">
            {form.formState.errors.root.message}
          </div>
        )}
        
        <div className="space-y-2 relative">
          <label className="text-sm font-medium leading-none text-slate-700" htmlFor="password">
            New Password
          </label>
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

        <div className="space-y-2">
          <label className="text-sm font-medium leading-none text-slate-700" htmlFor="confirmPassword">
            Confirm New Password
          </label>
          <Input
            id="confirmPassword"
            type={showPassword ? "text" : "password"}
            {...form.register("confirmPassword")}
            className={form.formState.errors.confirmPassword ? "border-rose-300 focus-visible:ring-rose-200" : ""}
            disabled={isSubmitting}
          />
          {form.formState.errors.confirmPassword && (
            <p className="text-xs text-rose-500 font-medium">{form.formState.errors.confirmPassword.message}</p>
          )}
        </div>
        
        <Button type="submit" className="w-full mt-2 bg-slate-900 hover:bg-slate-800 text-white" disabled={isSubmitting}>
          {isSubmitting ? "Resetting..." : "Reset password"}
        </Button>
      </form>
    </AuthLayout>
  );
}
