import { apiRequest } from "@/lib/api-client";
import type { OrderListFilters } from "./filters";
import type { NotificationFilters } from "./notifications";
import {
  notificationEnvelopeSchema,
  notificationListSchema,
  orderDetailSchema,
  orderEnvelopeSchema,
  orderListSchema,
  orderWithNotificationSchema,
  serviceTypeListSchema,
  technicianListSchema,
  type CreateOrderPayload,
  type NotificationList,
  type Order,
  type OrderDetail,
  type OrderList,
  type OrderNotification,
  type OrderWithNotification,
  type ServiceType,
  type Technician,
  type UpdateOrderPayload,
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

// Fetches one page of orders with the server-side filters; statuses repeat as one parameter each.
export async function listOrders(filters: OrderListFilters, signal?: AbortSignal): Promise<OrderList> {
  const query = {
    search: filters.search.trim(),
    status: filters.status,
    technicianId: filters.technicianId || undefined,
    sort: filters.sort,
    page: filters.page,
    pageSize: filters.pageSize,
  };
  return orderListSchema.parse(await apiRequest("/orders", { query, signal }));
}

// Fetches one order with its event timeline.
export async function getOrder(orderId: string, signal?: AbortSignal): Promise<OrderDetail> {
  return orderDetailSchema.parse(await apiRequest(`/orders/${encodeURIComponent(orderId)}`, { signal }));
}

// Creates an order and returns it with the technician notification, when one was queued.
export async function createOrder(payload: CreateOrderPayload): Promise<OrderWithNotification> {
  return orderWithNotificationSchema.parse(await apiRequest("/orders", { method: "POST", body: payload }));
}

// Edits an order's details and returns the stored order.
export async function updateOrder(orderId: string, payload: UpdateOrderPayload): Promise<Order> {
  return orderEnvelopeSchema.parse(await apiRequest(`/orders/${encodeURIComponent(orderId)}`, { method: "PATCH", body: payload })).order;
}

// Assigns or reassigns the technician and returns the order with the queued notification.
export async function assignTechnician(orderId: string, technicianId: string): Promise<OrderWithNotification> {
  const body = await apiRequest(`/orders/${encodeURIComponent(orderId)}/assign`, { method: "POST", body: { technicianId } });
  return orderWithNotificationSchema.parse(body);
}

// Runs one status step (start, review, or close) and returns the order.
export async function changeStatus(orderId: string, action: "start" | "review" | "close"): Promise<Order> {
  return orderEnvelopeSchema.parse(await apiRequest(`/orders/${encodeURIComponent(orderId)}/${action}`, { method: "POST" })).order;
}

// Fetches the technicians an admin can assign, from the admin-only users endpoint.
export async function listTechnicians(signal?: AbortSignal): Promise<Technician[]> {
  const body = await apiRequest("/users", { query: { roleCode: "technician", pageSize: 100 }, signal });
  return technicianListSchema.parse(body).items;
}
