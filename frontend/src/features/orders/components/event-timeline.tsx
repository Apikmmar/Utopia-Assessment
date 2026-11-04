import { formatDateTime } from "../notifications";
import type { OrderEvent } from "../schemas";

const EVENT_LABELS: Record<string, string> = {
  created: "Order created",
  edited: "Details edited",
  assigned: "Technician assigned",
  reassigned: "Technician changed",
  started: "Job started",
  completed: "Job completed",
  reviewed: "Reviewed",
  closed: "Closed",
  notification_queued: "WhatsApp message prepared",
};

// Returns the display label for an event type, or the raw type for one this client does not know.
export function eventLabel(eventType: string) {
  return EVENT_LABELS[eventType] ?? eventType;
}

// Who did what to an order and when, oldest first.
export function EventTimeline({ events }: { events: OrderEvent[] }) {
  if (events.length === 0) return <p className="text-sm text-muted">No activity yet.</p>;
  return (
    <ol aria-label="Order activity" className="flex flex-col gap-4 border-l border-border pl-5">
      {events.map((event, index) => (
        <li key={`${event.createdAt}-${index}`} className="relative">
          <span aria-hidden="true" className="absolute top-1.5 -left-[1.4rem] size-2 rounded-full bg-border-strong" />
          <p className="text-sm font-medium">{eventLabel(event.eventType)}</p>
          <p className="text-xs text-muted">
            {event.actor.name} · {formatDateTime(event.createdAt)}
          </p>
        </li>
      ))}
    </ol>
  );
}
