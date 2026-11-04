import type { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

// Small neutral pill for short labels such as a role.
export function Badge({ className, ...props }: HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border border-border bg-subtle px-2 py-0.5 text-xs font-medium whitespace-nowrap text-zinc-700",
        className,
      )}
      {...props}
    />
  );
}
