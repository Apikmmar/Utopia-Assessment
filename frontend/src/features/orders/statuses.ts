export const ORDER_STATUSES = ["new", "assigned", "in_progress", "job_done", "reviewed", "closed"] as const;

export type OrderStatus = (typeof ORDER_STATUSES)[number];

export type StatusTone = "neutral" | "info" | "progress" | "attention" | "success" | "muted";

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  new: "New",
  assigned: "Assigned",
  in_progress: "In progress",
  job_done: "Job done",
  reviewed: "Reviewed",
  closed: "Closed",
};

export const ORDER_STATUS_TONES: Record<OrderStatus, StatusTone> = {
  new: "neutral",
  assigned: "info",
  in_progress: "progress",
  job_done: "attention",
  reviewed: "success",
  closed: "muted",
};

const UNKNOWN_STATUS_LABEL = "Unknown status";

// Narrows a server status to one this client knows.
export function isKnownStatus(status: string): status is OrderStatus {
  return (ORDER_STATUSES as readonly string[]).includes(status);
}

// Returns the display label for a status, falling back for statuses this client does not know yet.
export function statusLabel(status: string) {
  if (isKnownStatus(status)) return ORDER_STATUS_LABELS[status];
  return status ? `${UNKNOWN_STATUS_LABEL} (${status})` : UNKNOWN_STATUS_LABEL;
}

// Returns the badge tone for a status, neutral for one this client does not know.
export function statusTone(status: string): StatusTone {
  return isKnownStatus(status) ? ORDER_STATUS_TONES[status] : "neutral";
}

export const EDITABLE_STATUSES: readonly OrderStatus[] = ["new", "assigned"];
export const ACTIVE_JOB_STATUSES: OrderStatus[] = ["assigned", "in_progress"];
export const FINISHED_JOB_STATUSES: OrderStatus[] = ["job_done", "reviewed", "closed"];
