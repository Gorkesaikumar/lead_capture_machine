import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Link } from "react-router-dom";
import { apiClient } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AuthLayout } from "./AuthLayout";

const forgotPasswordSchema = z.object({
  email: z.string().email({ message: "Please enter a valid email address." }),
});

type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export default function ForgotPassword() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);

  const form = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (data: ForgotPasswordFormValues) => {
    setIsSubmitting(true);
    try {
      // NOTE: Using actual backend API. If endpoint doesn't exist, this will gracefully catch the 404/501 error.
      await apiClient.post("/auth/password/reset/", data);
      setIsSuccess(true);
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
          message: serverMsg || "Invalid request.",
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

  if (isSuccess) {
    return (
      <AuthLayout
        title="Check your email"
        description="We've sent a password reset link to your email address."
        footer={
          <Link to="/login" className="text-slate-900 font-medium hover:underline">
            Back to login
          </Link>
        }
      >
        <div className="flex justify-center mb-2">
          <div className="h-12 w-12 rounded-full bg-emerald-100 flex items-center justify-center">
            <svg className="h-6 w-6 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
        </div>
        <p className="text-center text-sm text-slate-600 mb-6">
          If an account exists with that email, you will receive instructions to reset your password shortly.
        </p>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Reset password"
      description="Enter your email to receive a reset link"
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
        
        <Button type="submit" className="w-full mt-2 bg-slate-900 hover:bg-slate-800 text-white" disabled={isSubmitting}>
          {isSubmitting ? "Sending..." : "Send reset link"}
        </Button>
      </form>
    </AuthLayout>
  );
}
