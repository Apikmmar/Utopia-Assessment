import { useQuery } from "@tanstack/react-query";
import * as api from "./api";
import type { OrderListFilters } from "./filters";

const SERVICE_TYPES_STALE_MS = 10 * 60 * 1000;

export type NotificationFilters = {
  state?: string;
  orderId?: string;
  notificationType?: string;
  search?: string;
  page?: number;
  pageSize?: number;
};

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
