import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { failureMessage } from "@/lib/failure-message";
import { useChangeStatus } from "../queries";
import type { Order } from "../schemas";

type StatusAction = "start" | "review" | "close";

const ACTION_FOR_STATUS: Record<string, Partial<Record<string, { action: StatusAction; label: string; pending: string }>>> = {
  technician: { assigned: { action: "start", label: "Start job", pending: "Starting…" } },
  manager: {
    job_done: { action: "review", label: "Mark reviewed", pending: "Saving…" },
    reviewed: { action: "close", label: "Close order", pending: "Closing…" },
  },
};
const CHANGED_MESSAGE = "This order's status changed in the meantime. The page now shows its current status.";

// Returns the failure text for a status step; a 409 means someone else moved the order first.
function errorText(error: unknown) {
  if (error instanceof ApiError && error.code === "INVALID_TRANSITION") return CHANGED_MESSAGE;
  if (error instanceof ApiError && error.status < 500 && error.status !== 0) return error.message;
  return failureMessage(error, "We could not update the order. Try again.");
}

// The one status step this role can take on the order now, with its pending state and failure message.
export function StatusActions({ order, roleCode, className }: { order: Order; roleCode: string; className?: string }) {
  const change = useChangeStatus(order.orderId);
  const step = ACTION_FOR_STATUS[roleCode]?.[order.status];
  return (
    <div className="flex flex-col gap-3">
      {step ? (
        <Button className={className} disabled={change.isPending} onClick={() => change.mutate(step.action)}>
          {change.isPending ? step.pending : step.label}
        </Button>
      ) : null}
      {change.isError ? <Alert tone="error">{errorText(change.error)}</Alert> : null}
    </div>
  );
}
