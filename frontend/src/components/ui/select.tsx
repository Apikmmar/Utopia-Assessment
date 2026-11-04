import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Native select styled like Input, which keeps mobile pickers and keyboard behavior.
export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "min-h-11 w-full rounded-md border border-border bg-card px-3 text-base text-foreground aria-[invalid=true]:border-danger md:text-sm",
        className,
      )}
      {...props}
    />
  );
}
