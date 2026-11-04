import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type AlertProps = { tone: "error" | "success"; children: ReactNode };

// Live-region message for form-level errors and success status.
export function Alert({ tone, children }: AlertProps) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2.5 rounded-lg border px-3.5 py-2.5 text-sm",
        tone === "error" ? "border-red-200 bg-danger-soft text-danger" : "border-green-200 bg-success-soft text-success",
      )}
    >
      <span aria-hidden="true" className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", tone === "error" ? "bg-danger" : "bg-success")} />
      <div>{children}</div>
    </div>
  );
}
