import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";

// Boxed loading message for a list or page section.
export function LoadingState({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="rounded-xl border border-border bg-card px-6 py-16 text-center text-sm text-muted">
      {children}
    </p>
  );
}

// Boxed failure message with a retry button.
export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 rounded-xl border border-border bg-card px-6 py-16 text-center text-sm text-danger">
      <p>{message}</p>
      <Button variant="outline" onClick={onRetry}>
        Retry
      </Button>
    </div>
  );
}

// Dashed empty message for a list with nothing to show.
export function EmptyState({ children }: { children: ReactNode }) {
  return (
    <p role="status" className="rounded-xl border border-dashed border-border-strong px-6 py-16 text-center text-sm text-muted">
      {children}
    </p>
  );
}
