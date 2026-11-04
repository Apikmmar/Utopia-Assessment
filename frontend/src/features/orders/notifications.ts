import type { OrderNotification } from "./schemas";

export const NOTIFICATION_TABS = ["pending", "sent"] as const;
export type NotificationTab = (typeof NOTIFICATION_TABS)[number];

export const NOTIFICATION_TYPES = ["job_assigned", "job_done"] as const;
export type NotificationType = (typeof NOTIFICATION_TYPES)[number];

export const NOTIFICATION_TYPE_LABELS: Record<NotificationType, string> = {
  job_assigned: "Job assigned",
  job_done: "Job done",
};

const NOTIFICATION_STATUS_LABELS: Record<string, string> = {
  queued: "Preparing",
  ready: "Ready to send",
  opened: "Opened in WhatsApp",
  sent: "Sent",
  failed: "Failed",
};

export const POLL_INTERVAL_MS = 2000;
export const PREPARE_TIMEOUT_MS = 30_000;
export const SEARCH_MAX_LENGTH = 100;
export const PAGE_SIZE = 20;

const WHATSAPP_LINK_PREFIX = "https://wa.me/";
const FIRST_PAGE = 1;
const timeFormatter = new Intl.DateTimeFormat("en-MY", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kuala_Lumpur" });

export type NotificationFilters = {
  state?: NotificationTab;
  orderId?: string;
  notificationType?: string;
  search?: string;
  sendable?: boolean;
  page?: number;
  pageSize?: number;
};

export type NotificationPageFilters = { tab: NotificationTab; search: string; notificationType: string; page: number };

// Returns the display label for a notification type, or the raw code for one this client does not know.
export function notificationTypeLabel(code: string) {
  return (NOTIFICATION_TYPES as readonly string[]).includes(code) ? NOTIFICATION_TYPE_LABELS[code as NotificationType] : code;
}

// Returns the display label for a notification status, or the raw status for one this client does not know.
export function notificationStatusLabel(status: string) {
  return NOTIFICATION_STATUS_LABELS[status] ?? status;
}

// Returns the deep link only when it is a WhatsApp link, so an unexpected value is never rendered as a link.
export function safeWhatsappLink(notification: OrderNotification) {
  const link = notification.deepLink;
  return link && link.startsWith(WHATSAPP_LINK_PREFIX) ? link : null;
}

// Formats an API timestamp in Malaysian time for display.
export function formatDateTime(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : timeFormatter.format(date);
}

// Returns whether any notification in a list is still being prepared by the worker.
export function hasQueued(items: OrderNotification[] | undefined) {
  return Boolean(items?.some((item) => item.status === "queued"));
}

// Reads the notifications page filters from URL search params, replacing anything invalid with its default.
export function readNotificationFilters(params: URLSearchParams): NotificationPageFilters {
  const tab = params.get("tab");
  const notificationType = params.get("type") ?? "";
  const page = Number(params.get("page"));
  return {
    tab: tab === "sent" ? "sent" : "pending",
    search: (params.get("search") ?? "").slice(0, SEARCH_MAX_LENGTH),
    notificationType: (NOTIFICATION_TYPES as readonly string[]).includes(notificationType) ? notificationType : "",
    page: Number.isInteger(page) && page >= 1 ? page : FIRST_PAGE,
  };
}

// Writes the notifications page filters back to search params, leaving out defaults.
export function toNotificationFilterParams(filters: NotificationPageFilters) {
  const params = new URLSearchParams();
  if (filters.tab !== "pending") params.set("tab", filters.tab);
  if (filters.search) params.set("search", filters.search);
  if (filters.notificationType) params.set("type", filters.notificationType);
  if (filters.page !== FIRST_PAGE) params.set("page", String(filters.page));
  return params;
}
