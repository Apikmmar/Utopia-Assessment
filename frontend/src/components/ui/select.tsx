import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { controlClassName } from "./input";

// Native select styled like Input, which keeps mobile pickers and keyboard behavior.
export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(controlClassName, "cursor-pointer", className)} {...props} />;
}
