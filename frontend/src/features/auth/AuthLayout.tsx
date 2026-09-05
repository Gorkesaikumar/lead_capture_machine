import type { ReactNode } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Link } from "react-router-dom";

interface AuthLayoutProps {
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthLayout({ title, description, children, footer }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-surface-tint-yellow p-4 relative overflow-hidden">
      {/* Dot pattern bg */}
      <div className="absolute inset-0 hero-pattern opacity-40 pointer-events-none z-0" />

      <div className="relative z-10 w-full flex flex-col items-center">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-3 mb-8 group">
          <img src="/lead.png" alt="Nextora" className="h-16 w-auto object-contain shrink-0 drop-shadow-[0_2px_12px_rgba(123,47,255,0.35)]" />
        </Link>

        <Card className="w-full max-w-md shadow-xl border-outline-variant/60 bg-white/95 backdrop-blur-sm">
          <CardHeader className="space-y-2 text-center pb-6">
            <CardTitle className="text-2xl font-bold tracking-tight text-on-surface">
              {title}
            </CardTitle>
            <CardDescription className="text-on-surface-variant text-body-sm">
              {description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {children}
          </CardContent>
        </Card>

        {footer && (
          <div className="mt-6 text-center text-body-sm text-on-surface-variant">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
