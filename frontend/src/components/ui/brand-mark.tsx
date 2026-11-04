import { cn } from "@/lib/cn";

// Product wordmark: a small dark tile with the initial, followed by the name.
export function BrandMark({ className }: { className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm font-semibold tracking-tight", className)}>
      <span aria-hidden="true" className="grid size-6 place-items-center rounded-md bg-primary text-xs text-primary-foreground">
        U
      </span>
      Utopia
    </span>
  );
}
