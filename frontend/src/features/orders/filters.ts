import { isKnownStatus, type OrderStatus } from "./statuses";

export const ORDER_SORTS = ["newest", "oldest"] as const;
export type OrderSort = (typeof ORDER_SORTS)[number];

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 20;
export const SEARCH_MAX_LENGTH = 100;
export const DEFAULT_SORT: OrderSort = "newest";

const FIRST_PAGE = 1;
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export type OrderListFilters = {
  search: string;
  status: OrderStatus[];
  technicianId: string;
  sort: OrderSort;
  page: number;
  pageSize: number;
};

// Reads a positive integer query value, or null when it is missing or malformed.
function readPositiveInt(value: string | null) {
  if (value === null || !/^[0-9]+$/.test(value)) return null;
  const parsed = Number(value);
  return parsed >= 1 ? parsed : null;
}

// Reads the order list filters from URL search params, dropping unknown statuses and replacing anything invalid with its default.
export function readOrderFilters(params: URLSearchParams): OrderListFilters {
  const statuses = params.getAll("status").filter(isKnownStatus);
  const technicianId = params.get("technicianId") ?? "";
  const sort = params.get("sort") ?? "";
  const pageSize = readPositiveInt(params.get("pageSize"));
  return {
    search: (params.get("search") ?? "").slice(0, SEARCH_MAX_LENGTH),
    status: [...new Set(statuses)],
    technicianId: UUID_PATTERN.test(technicianId) ? technicianId : "",
    sort: (ORDER_SORTS as readonly string[]).includes(sort) ? (sort as OrderSort) : DEFAULT_SORT,
    page: readPositiveInt(params.get("page")) ?? FIRST_PAGE,
    pageSize: pageSize !== null && (PAGE_SIZE_OPTIONS as readonly number[]).includes(pageSize) ? pageSize : DEFAULT_PAGE_SIZE,
  };
}

// Writes filters back to search params, leaving out values that equal their defaults.
export function toOrderFilterParams(filters: OrderListFilters) {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  filters.status.forEach((status) => params.append("status", status));
  if (filters.technicianId) params.set("technicianId", filters.technicianId);
  if (filters.sort !== DEFAULT_SORT) params.set("sort", filters.sort);
  if (filters.page !== FIRST_PAGE) params.set("page", String(filters.page));
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) params.set("pageSize", String(filters.pageSize));
  return params;
}
