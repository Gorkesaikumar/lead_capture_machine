import type { ReactNode } from "react";

interface PageContainerProps {
  children: ReactNode;
}

export function PageContainer({ children }: PageContainerProps) {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 md:px-8 md:py-8 lg:py-10 space-y-8">
      {children}
    </div>
  );
}
