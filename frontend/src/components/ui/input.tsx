import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Shared text input with a 44px touch target and an invalid-state border.
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "min-h-11 w-full rounded-md border border-border bg-card px-3 text-base text-foreground placeholder:text-slate-500 aria-[invalid=true]:border-danger md:text-sm",
        className,
      )}
      {...props}
    />
  );
}
