import { apiRequest } from "@/lib/api-client";
import type { NotificationFilters } from "./notifications";
import {
  notificationEnvelopeSchema,
  notificationListSchema,
  serviceTypeListSchema,
  type NotificationList,
  type OrderNotification,
  type ServiceType,
} from "./schemas";

// Fetches the active service types in display order.
export async function listServiceTypes(signal?: AbortSignal): Promise<ServiceType[]> {
  return serviceTypeListSchema.parse(await apiRequest("/service-types", { signal })).items;
}

// Fetches one page of notifications scoped by the server to what this user may see.
export async function listNotifications(filters: NotificationFilters, signal?: AbortSignal): Promise<NotificationList> {
  const query = { ...filters, search: filters.search?.trim(), sendable: filters.sendable ? "true" : undefined };
  return notificationListSchema.parse(await apiRequest("/notifications", { query, signal }));
}

// Records that the user opened a ready notification in WhatsApp and returns its new state.
export async function openNotification(notificationId: string): Promise<OrderNotification> {
  const body = await apiRequest(`/notifications/${encodeURIComponent(notificationId)}/open`, { method: "POST" });
  return notificationEnvelopeSchema.parse(body).notification;
}

// Queues a failed notification again and returns its new state.
export async function retryNotification(notificationId: string): Promise<OrderNotification> {
  const body = await apiRequest(`/notifications/${encodeURIComponent(notificationId)}/retry`, { method: "POST" });
  return notificationEnvelopeSchema.parse(body).notification;
}
