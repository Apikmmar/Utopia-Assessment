import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { failureMessage } from "@/lib/failure-message";
import { formatDateTime, notificationStatusLabel, notificationTypeLabel } from "../notifications";
import { useNotifications, useRetryNotification } from "../queries";
import type { OrderNotification } from "../schemas";
import { WhatsappButton } from "./whatsapp-button";

const STATUS_CLASSES: Record<string, string> = {
  queued: "",
  ready: "border-sky-200 bg-sky-50 text-sky-800",
  opened: "border-emerald-200 bg-emerald-50 text-emerald-800",
  sent: "border-emerald-200 bg-emerald-50 text-emerald-800",
  failed: "border-red-200 bg-danger-soft text-danger",
};

type NotificationItemProps = { notification: OrderNotification; roleCode: string; showOrder?: boolean };

// Returns the page an order number links to for this role: technicians open their job page, others the order page.
export function orderPathFor(roleCode: string, orderId: string) {
  return roleCode === "technician" ? `/jobs/${orderId}` : `/orders/${orderId}`;
}

// One notification as a card on phones and a row on wider screens, with its send or retry action.
export function NotificationItem({ notification, roleCode, showOrder = true }: NotificationItemProps) {
  const retry = useRetryNotification();
  const canRetry = roleCode === "admin" && notification.status === "failed";
  return (
    <li className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="flex min-w-0 flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {showOrder ? (
            <Link to={orderPathFor(roleCode, notification.orderId)} className="font-medium underline-offset-4 hover:underline">
              {notification.orderNo}
            </Link>
          ) : null}
          <Badge>{notificationTypeLabel(notification.notificationType)}</Badge>
          <Badge className={STATUS_CLASSES[notification.status] ?? ""}>{notificationStatusLabel(notification.status)}</Badge>
        </div>
        <p className="text-sm">
          To {notification.recipientName} <span className="text-muted">· {notification.recipientPhone}</span>
        </p>
        <p className="text-xs text-muted">
          {notification.openedAt
            ? `Opened ${formatDateTime(notification.openedAt)}${notification.openedBy ? ` by ${notification.openedBy.name}` : ""}`
            : `Created ${formatDateTime(notification.createdAt)}`}
        </p>
      </div>
      <div className="flex flex-col gap-2 sm:items-end">
        <WhatsappButton notification={notification} className="w-full sm:w-auto" showLaterLink={false} />
        {canRetry ? (
          <Button
            variant="outline"
            className="w-full sm:w-auto"
            disabled={retry.isPending}
            onClick={() => retry.mutate(notification.notificationId)}
          >
            {retry.isPending ? "Retrying…" : "Retry"}
          </Button>
        ) : null}
        {retry.isError ? (
          <p role="alert" className="text-xs text-danger">
            {failureMessage(retry.error, "We could not retry this message. Try again.")}
          </p>
        ) : null}
      </div>
    </li>
  );
}

type NotificationListProps = { orderId: string; roleCode: string };

// The WhatsApp notifications of one order, for the order and job pages.
export function NotificationList({ orderId, roleCode }: NotificationListProps) {
  const notifications = useNotifications({ orderId });
  if (notifications.isPending) {
    return (
      <p role="status" className="text-sm text-muted">
        Loading messages…
      </p>
    );
  }
  if (notifications.isError) {
    return (
      <div role="alert" className="flex items-center gap-3 text-sm text-danger">
        <p>{failureMessage(notifications.error, "We could not load messages.")}</p>
        <Button variant="outline" onClick={() => void notifications.refetch()}>
          Retry
        </Button>
      </div>
    );
  }
  if (notifications.data.items.length === 0) {
    return <p className="text-sm text-muted">No WhatsApp messages for this order yet.</p>;
  }
  return (
    <ul aria-label="WhatsApp messages" className="divide-y divide-border rounded-xl border border-border bg-card">
      {notifications.data.items.map((notification) => (
        <NotificationItem key={notification.notificationId} notification={notification} roleCode={roleCode} showOrder={false} />
      ))}
    </ul>
  );
}
