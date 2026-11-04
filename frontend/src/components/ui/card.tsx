import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Bordered surface that groups related content.
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-xl border border-border bg-card p-6 shadow-xs sm:p-8", className)} {...props} />;
}
