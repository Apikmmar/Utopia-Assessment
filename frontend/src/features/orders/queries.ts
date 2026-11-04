import { keepPreviousData, useMutation, useQuery, useQueryClient, type Query } from "@tanstack/react-query";
import { useRef } from "react";
import * as api from "./api";
import type { OrderListFilters } from "./filters";
import { hasQueued, POLL_INTERVAL_MS, PREPARE_TIMEOUT_MS, type NotificationFilters } from "./notifications";
import type { NotificationList } from "./schemas";

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
};

// Reads the active service types, which rarely change, so they stay fresh for ten minutes.
export function useServiceTypes() {
  return useQuery({
    queryKey: orderKeys.serviceTypes(),
    queryFn: ({ signal }) => api.listServiceTypes(signal),
    staleTime: SERVICE_TYPES_STALE_MS,
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
