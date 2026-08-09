import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useNavigate, Navigate } from "react-router-dom";
import { apiClient } from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { LoadingSkeleton } from "@/components/common/states/LoadingSkeleton";

const loginSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address." }),
  password: z.string().min(1, { message: "Password is required." }),
});

type LoginFormValues = z.infer<typeof loginSchema>;

export default function Login() {
  const { login, user, isLoading: isAuthLoading } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  if (isAuthLoading) {
    return <div className="min-h-screen flex items-center justify-center p-8"><LoadingSkeleton rows={2} /></div>;
  }

  if (user) {
    return <Navigate to="/" replace />;
  }

  const onSubmit = async (data: LoginFormValues) => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.post("/auth/login/", data);
      const token = response.data?.data?.token || response.data?.token || response.data?.key;
      
      if (token) {
        await login(token);
        navigate("/");
      } else {
        toast.error("Authentication failed: Invalid token format received.");
      }
    } catch (err: any) {
      const status = err.response?.status;
      const serverMsg =
        err.response?.data?.message ||
        err.response?.data?.errors?.detail ||
        err.response?.data?.detail;

      if (status === 400 || status === 401) {
        form.setError("root", {
          type: "manual",
          message: serverMsg || "Invalid email or password.",
        });
      } else if (serverMsg) {
        toast.error(serverMsg);
      } else {
        toast.error("A network error occurred. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50/50 p-4">
      <Card className="w-full max-w-sm shadow-sm border-gray-200 bg-white">
        <CardHeader className="space-y-2 text-center pb-6">
          <CardTitle className="text-2xl font-semibold tracking-tight text-slate-900">Studio Admin</CardTitle>
          <CardDescription className="text-slate-500">Sign in to your account</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-5">
            {form.formState.errors.root && (
              <div className="p-3 text-sm font-medium text-rose-800 bg-rose-50 border border-rose-100 rounded-md text-center">
                {form.formState.errors.root.message}
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
            
            <Button type="submit" className="w-full mt-2" disabled={isSubmitting}>
              {isSubmitting ? "Verifying..." : "Sign in"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
