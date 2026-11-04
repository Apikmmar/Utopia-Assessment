import type { ComponentProps } from "react";
import { Link } from "react-router";
import { cn } from "@/lib/cn";

// Quiet secondary link that darkens and underlines on hover.
export function TextLink({ className, ...props }: ComponentProps<typeof Link>) {
  return (
    <Link
      className={cn(
        "inline-flex min-h-10 items-center text-sm font-medium text-muted underline-offset-4 transition-colors hover:text-foreground hover:underline",
        className,
      )}
      {...props}
    />
  );
}
