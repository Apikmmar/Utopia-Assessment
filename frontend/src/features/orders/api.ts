import { apiRequest } from "@/lib/api-client";
import type { AttachmentKind } from "./attachments";
import type { OrderListFilters } from "./filters";
import type { NotificationFilters } from "./notifications";
import {
  attachmentListSchema,
  completionEnvelopeSchema,
  submitCompletionResponseSchema,
  uploadResponseSchema,
  type Completion,
  type SubmitCompletionPayload,
  type SubmitCompletionResult,
  type Attachment,
  type UploadTicket,
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

export type PostponePayload = { reasonCode: string; newDate?: string };

// Records a postponed visit; the order keeps its status.
export async function postponeOrder(orderId: string, payload: PostponePayload): Promise<Order> {
  return orderEnvelopeSchema.parse(await apiRequest(`/orders/${encodeURIComponent(orderId)}/postpone`, { method: "POST", body: payload })).order;
}

// Fetches the technicians an admin can assign, from the admin-only users endpoint.
export async function listTechnicians(signal?: AbortSignal): Promise<Technician[]> {
  const body = await apiRequest("/users", { query: { roleCode: "technician", pageSize: 100 }, signal });
  return technicianListSchema.parse(body).items;
}

export type UploadRequestPayload = { kind: AttachmentKind; fileName: string; contentType: string; sizeBytes: number };

// Records a pending file on the job and returns it with the signed URL the browser uploads to.
export async function requestUpload(orderId: string, payload: UploadRequestPayload): Promise<UploadTicket> {
  const body = await apiRequest(`/orders/${encodeURIComponent(orderId)}/attachments`, { method: "POST", body: payload });
  return uploadResponseSchema.parse(body);
}

// Removes a pending file from the job.
export async function deleteAttachment(orderId: string, attachmentId: string): Promise<void> {
  await apiRequest(`/orders/${encodeURIComponent(orderId)}/attachments/${encodeURIComponent(attachmentId)}`, { method: "DELETE" });
}

// Fetches an order's files with short-lived view links.
export async function listAttachments(orderId: string, signal?: AbortSignal): Promise<Attachment[]> {
  return attachmentListSchema.parse(await apiRequest(`/orders/${encodeURIComponent(orderId)}/attachments`, { signal })).items;
}

// Uploads a file straight to storage with a signed URL, reporting progress from 0 to 1; rejects on failure or abort.
export function uploadFile(uploadUrl: string, file: Blob, contentType: string, onProgress: (fraction: number) => void, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("PUT", uploadUrl);
    request.setRequestHeader("Content-Type", contentType);
    request.setRequestHeader("x-upsert", "false");
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total);
    };
    request.onload = () => (request.status >= 200 && request.status < 300 ? resolve() : reject(new Error(`Upload failed with status ${request.status}`)));
    request.onerror = () => reject(new Error("Upload failed"));
    request.onabort = () => reject(new DOMException("Upload aborted", "AbortError"));
    signal?.addEventListener("abort", () => request.abort(), { once: true });
    request.send(file);
  });
}

// Fetches an order's completion record; the server answers COMPLETION_NOT_FOUND until the job is done.
export async function getCompletion(orderId: string, signal?: AbortSignal): Promise<Completion> {
  return completionEnvelopeSchema.parse(await apiRequest(`/orders/${encodeURIComponent(orderId)}/completion`, { signal })).completion;
}

// Submits the completion record and returns it with the job_done order and the queued customer notification.
export async function submitCompletion(orderId: string, payload: SubmitCompletionPayload): Promise<SubmitCompletionResult> {
  const body = await apiRequest(`/orders/${encodeURIComponent(orderId)}/completion`, { method: "POST", body: payload });
  return submitCompletionResponseSchema.parse(body);
}
