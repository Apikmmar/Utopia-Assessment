import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export const controlClassName =
  "min-h-10 w-full rounded-lg border border-border bg-card px-3 text-base text-foreground shadow-xs transition-[border-color,box-shadow] hover:border-border-strong focus-visible:border-zinc-400 focus-visible:ring-4 focus-visible:ring-zinc-200/60 focus-visible:outline-none aria-[invalid=true]:border-danger aria-[invalid=true]:focus-visible:ring-red-100 md:text-sm";

// Shared text input with a 40px control height, a soft focus ring, and an invalid-state border.
export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(controlClassName, "placeholder:text-zinc-400", className)} {...props} />;
}
