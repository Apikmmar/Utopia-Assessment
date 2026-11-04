import { keepPreviousData, useMutation, useQuery, useQueryClient, type Query, type QueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import * as api from "./api";
import type { OrderListFilters } from "./filters";
import { hasQueued, POLL_INTERVAL_MS, PREPARE_TIMEOUT_MS, type NotificationFilters } from "./notifications";
import type { NotificationList, OrderWithNotification, UpdateOrderPayload } from "./schemas";

const SERVICE_TYPES_STALE_MS = 10 * 60 * 1000;
const SENDABLE_COUNT_FILTERS: NotificationFilters = { sendable: true, pageSize: 1 };

export const orderKeys = {
  all: ["orders"] as const,
  lists: () => [...orderKeys.all, "list"] as const,
  list: (filters: OrderListFilters) => [...orderKeys.lists(), filters] as const,
  details: () => [...orderKeys.all, "detail"] as const,
  detail: (orderId: string) => [...orderKeys.details(), orderId] as const,
  completion: (orderId: string) => [...orderKeys.detail(orderId), "completion"] as const,
  attachments: (orderId: string) => [...orderKeys.detail(orderId), "attachments"] as const,
  notificationsAll: () => [...orderKeys.all, "notifications"] as const,
  notifications: (filters: NotificationFilters) => [...orderKeys.notificationsAll(), filters] as const,
  serviceTypes: () => [...orderKeys.all, "service-types"] as const,
  technicians: () => [...orderKeys.all, "technicians"] as const,
};

// Reads the active service types, which rarely change, so they stay fresh for ten minutes.
export function useServiceTypes() {
  return useQuery({
    queryKey: orderKeys.serviceTypes(),
    queryFn: ({ signal }) => api.listServiceTypes(signal),
    staleTime: SERVICE_TYPES_STALE_MS,
  });
}

// Reads one filtered page of orders, keeping the previous page visible while the next loads.
export function useOrders(filters: OrderListFilters, options: { refetchOnWindowFocus?: boolean } = {}) {
  return useQuery({
    queryKey: orderKeys.list(filters),
    queryFn: ({ signal }) => api.listOrders(filters, signal),
    placeholderData: keepPreviousData,
    refetchOnWindowFocus: options.refetchOnWindowFocus ?? false,
  });
}

// Reads one order with its event timeline.
export function useOrder(orderId: string) {
  return useQuery({ queryKey: orderKeys.detail(orderId), queryFn: ({ signal }) => api.getOrder(orderId, signal) });
}

// Reads the technicians an admin can assign; only admins may call it.
export function useTechnicians(enabled = true) {
  return useQuery({ queryKey: orderKeys.technicians(), queryFn: ({ signal }) => api.listTechnicians(signal), enabled });
}

// Refreshes everything one order change can affect: its detail, every list, and every notification list.
function invalidateOrder(queryClient: QueryClient, orderId: string) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: orderKeys.detail(orderId) }),
    queryClient.invalidateQueries({ queryKey: orderKeys.lists() }),
    queryClient.invalidateQueries({ queryKey: orderKeys.notificationsAll() }),
  ]);
}

// Creates an order and refreshes the order and notification lists.
export function useCreateOrder() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.createOrder,
    onSuccess: (result: OrderWithNotification) => invalidateOrder(queryClient, result.order.orderId),
  });
}

// Edits an order and refreshes what it affects.
export function useUpdateOrder(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: UpdateOrderPayload) => api.updateOrder(orderId, payload),
    onSuccess: () => invalidateOrder(queryClient, orderId),
  });
}

// Assigns a technician and refreshes what it affects.
export function useAssignTechnician(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (technicianId: string) => api.assignTechnician(orderId, technicianId),
    onSuccess: () => invalidateOrder(queryClient, orderId),
  });
}

// Runs one status step; any outcome, including a 409 from a status that changed underneath, refreshes the order.
export function useChangeStatus(orderId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (action: "start" | "review" | "close") => api.changeStatus(orderId, action),
    onSettled: () => invalidateOrder(queryClient, orderId),
  });
}

// Reads one page of notifications, polling every two seconds while any is still being prepared, for at most 30 seconds.
export function useNotifications(filters: NotificationFilters, enabled = true) {
  const pollingSince = useRef<number | null>(null);
  return useQuery({
    queryKey: orderKeys.notifications(filters),
    queryFn: ({ signal }) => api.listNotifications(filters, signal),
    placeholderData: keepPreviousData,
    enabled,
    refetchInterval: (query: Query<NotificationList>) => {
      if (!hasQueued(query.state.data?.items)) {
        pollingSince.current = null;
        return false;
      }
      pollingSince.current ??= Date.now();
      return Date.now() - pollingSince.current < PREPARE_TIMEOUT_MS ? POLL_INTERVAL_MS : false;
    },
  });
}

// Reads how many pending notifications this user is expected to send, for the navigation badge; managers send none.
export function useSendableCount(enabled: boolean) {
  const notifications = useNotifications(SENDABLE_COUNT_FILTERS, enabled);
  return enabled ? (notifications.data?.total ?? 0) : 0;
}

// Marks a notification opened in WhatsApp and refreshes every cached notification list.
export function useOpenNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.openNotification,
    onSettled: () => queryClient.invalidateQueries({ queryKey: orderKeys.notificationsAll() }),
  });
}

// Queues a failed notification again and refreshes every cached notification list.
export function useRetryNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.retryNotification,
    onSettled: () => queryClient.invalidateQueries({ queryKey: orderKeys.notificationsAll() }),
  });
}

const ATTACHMENTS_STALE_MS = 4 * 60 * 1000;

// Reads an order's files; view links expire after five minutes, so the list goes stale after four.
export function useAttachments(orderId: string, enabled = true) {
  return useQuery({
    queryKey: orderKeys.attachments(orderId),
    queryFn: ({ signal }) => api.listAttachments(orderId, signal),
    staleTime: ATTACHMENTS_STALE_MS,
    enabled,
  });
}
