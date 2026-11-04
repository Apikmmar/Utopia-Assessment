import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type AlertProps = { tone: "error" | "success"; children: ReactNode };

// Live-region message for form-level errors and success status.
export function Alert({ tone, children }: AlertProps) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "rounded-md border px-3 py-2 text-sm",
        tone === "error" ? "border-danger bg-danger-soft text-danger" : "border-success bg-success-soft text-success",
      )}
    >
      {children}
    </div>
  );
}
