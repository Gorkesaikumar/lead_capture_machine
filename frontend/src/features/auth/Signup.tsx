import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Link, useNavigate } from "react-router-dom";
import { apiClient } from "@/api/client";
import { Input } from "@/components/ui/input";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import { AuthLayout } from "./AuthLayout";
import { useAuth } from "@/contexts/AuthContext";

const signupSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }),
  email: z.string().email({ message: "Please enter a valid email address." }),
  organization: z.string().min(2, { message: "Organization name is required." }),
  password: z.string().min(8, { message: "Password must be at least 8 characters." }),
  confirmPassword: z.string(),
  terms: z.boolean().refine((val) => val === true, {
    message: "You must accept the terms and conditions.",
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type SignupFormValues = z.infer<typeof signupSchema>;

export default function Signup() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: {
      name: "",
      email: "",
      organization: "",
      password: "",
      confirmPassword: "",
      terms: false,
    },
  });

  const onSubmit = async (data: SignupFormValues) => {
    setIsSubmitting(true);
    try {
      const response = await apiClient.post("/auth/signup/", {
        name: data.name,
        email: data.email,
        organization: data.organization,
        password: data.password,
      });

      const { token, organization_id } = response.data.data;

      // Store org before calling login so the API header is set correctly
      if (organization_id) {
        localStorage.setItem("organizationId", organization_id);
      }

      // Auto-login: fetchMe with the new token, then redirect
      if (token) {
        await login(token);
        toast.success("Account created successfully! Welcome to Nextora.");
        navigate("/onboarding");
      } else {
        toast.success("Account created! Please log in.");
        navigate("/login");
      }
    } catch (err: any) {
      const status = err.response?.status;
      const detail = err.response?.data?.detail;
      const errors = err.response?.data?.errors;

      if (status === 400) {
        if (errors && Object.keys(errors).length > 0) {
          // Map field errors from backend to individual form fields
          Object.entries(errors).forEach(([field, msg]) => {
            const fieldKey = (field === "organization_name" || field === "organizationName") ? "organization" 
                           : (field === "full_name" || field === "fullName") ? "name" 
                           : field;
            form.setError(fieldKey as any, { type: "manual", message: Array.isArray(msg) ? msg[0] : (msg as string) });
          });
        } else if (detail) {
          form.setError("root", { type: "manual", message: detail });
        } else {
          form.setError("root", { type: "manual", message: "Invalid registration details. Please check your input." });
        }
      } else if (!err.response) {
        // Network-level error
        form.setError("root", {
          type: "manual",
          message: "Unable to connect to the server. Please check your internet connection.",
        });
      } else {
        form.setError("root", {
          type: "manual",
          message: detail || "Something went wrong while creating your account. Please try again later.",
        });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Create an account"
      description="Start managing your leads and conversations"
      footer={
        <span>
          Already have an account?{" "}
          <Link to="/login" className="text-primary font-semibold hover:underline">
            Sign in
          </Link>
        </span>
      }
    >
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">

        {/* Root error */}
        {form.formState.errors.root && (
          <div className="p-3 text-sm font-medium text-red-700 bg-red-50 border border-red-100 rounded-lg">
            {form.formState.errors.root.message}
          </div>
        )}

        {/* Full Name */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface" htmlFor="name">
            Full Name
          </label>
          <Input
            id="name"
            placeholder="John Doe"
            {...form.register("name")}
            className={`bg-white text-on-surface placeholder:text-on-surface-variant/60 border-outline-variant focus-visible:ring-primary/30 focus-visible:border-primary ${
              form.formState.errors.name ? "border-red-300 focus-visible:ring-red-200" : ""
            }`}
            disabled={isSubmitting}
          />
          {form.formState.errors.name && (
            <p className="text-xs text-red-600 font-medium">{form.formState.errors.name.message}</p>
          )}
        </div>

        {/* Email */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface" htmlFor="email">
            Email
          </label>
          <Input
            id="email"
            type="email"
            placeholder="you@company.com"
            {...form.register("email")}
            className={`bg-white text-on-surface placeholder:text-on-surface-variant/60 border-outline-variant focus-visible:ring-primary/30 focus-visible:border-primary ${
              form.formState.errors.email ? "border-red-300 focus-visible:ring-red-200" : ""
            }`}
            disabled={isSubmitting}
          />
          {form.formState.errors.email && (
            <p className="text-xs text-red-600 font-medium">{form.formState.errors.email.message}</p>
          )}
        </div>

        {/* Organization */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface" htmlFor="organization">
            Organization Name
          </label>
          <Input
            id="organization"
            placeholder="Acme Photography"
            {...form.register("organization")}
            className={`bg-white text-on-surface placeholder:text-on-surface-variant/60 border-outline-variant focus-visible:ring-primary/30 focus-visible:border-primary ${
              form.formState.errors.organization ? "border-red-300 focus-visible:ring-red-200" : ""
            }`}
            disabled={isSubmitting}
          />
          {form.formState.errors.organization && (
            <p className="text-xs text-red-600 font-medium">{form.formState.errors.organization.message}</p>
          )}
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface" htmlFor="password">
            Password
          </label>
          <div className="relative">
            <Input
              id="password"
              type={showPassword ? "text" : "password"}
              placeholder="Min. 8 characters"
              {...form.register("password")}
              className={`bg-white text-on-surface placeholder:text-on-surface-variant/60 border-outline-variant focus-visible:ring-primary/30 focus-visible:border-primary pr-10 ${
                form.formState.errors.password ? "border-red-300 focus-visible:ring-red-200" : ""
              }`}
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface focus:outline-none transition-colors"
              onClick={() => setShowPassword(!showPassword)}
              tabIndex={-1}
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {form.formState.errors.password && (
            <p className="text-xs text-red-600 font-medium">{form.formState.errors.password.message}</p>
          )}
        </div>

        {/* Confirm Password — separate eye toggle */}
        <div className="space-y-1.5">
          <label className="text-sm font-semibold text-on-surface" htmlFor="confirmPassword">
            Confirm Password
          </label>
          <div className="relative">
            <Input
              id="confirmPassword"
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Repeat your password"
              {...form.register("confirmPassword")}
              className={`bg-white text-on-surface placeholder:text-on-surface-variant/60 border-outline-variant focus-visible:ring-primary/30 focus-visible:border-primary pr-10 ${
                form.formState.errors.confirmPassword ? "border-red-300 focus-visible:ring-red-200" : ""
              }`}
              disabled={isSubmitting}
            />
            <button
              type="button"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface focus:outline-none transition-colors"
              onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              tabIndex={-1}
              aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
            >
              {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          {form.formState.errors.confirmPassword && (
            <p className="text-xs text-red-600 font-medium">{form.formState.errors.confirmPassword.message}</p>
          )}
        </div>

        {/* Terms */}
        <div className="flex items-start gap-3 pt-1">
          <input
            type="checkbox"
            id="terms"
            className="mt-0.5 h-4 w-4 rounded border-outline-variant text-primary focus:ring-primary cursor-pointer"
            {...form.register("terms")}
            disabled={isSubmitting}
          />
          <div>
            <label htmlFor="terms" className="text-sm text-on-surface cursor-pointer select-none">
              Accept terms and conditions
            </label>
            {form.formState.errors.terms && (
              <p className="text-xs text-red-600 font-medium mt-0.5">{form.formState.errors.terms.message}</p>
            )}
          </div>
        </div>

        {/* Submit button — Nextora primary red */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full mt-2 bg-primary text-on-primary py-2.5 px-4 rounded-lg font-semibold text-sm hover:bg-primary-container transition-colors disabled:opacity-60 disabled:cursor-not-allowed shadow-md"
        >
          {isSubmitting ? "Creating account…" : "Sign up"}
        </button>
      </form>
    </AuthLayout>
  );
}
