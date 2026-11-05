import { keepPreviousData, useQuery } from "@tanstack/react-query";
import * as api from "./api";

export const kpiKeys = {
  all: ["kpi"] as const,
  dashboard: (date: string | undefined) => [...kpiKeys.all, "dashboard", date ?? "current"] as const,
};

// Reads the dashboard for a week; it is refetched on every visit and on window focus, so completions and
// postponements made elsewhere show without cross-feature cache invalidation.
export function useDashboard(date: string | undefined) {
  return useQuery({
    queryKey: kpiKeys.dashboard(date),
    queryFn: ({ signal }) => api.getDashboard(date, signal),
    placeholderData: keepPreviousData,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });
}
