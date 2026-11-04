import { isKnownRole } from "@/features/auth/roles";
import type { UserListFilters } from "./types";

export const PAGE_SIZE_OPTIONS = [10, 20, 50, 100] as const;
export const DEFAULT_PAGE_SIZE = 20;
export const SEARCH_MAX_LENGTH = 100;

const FIRST_PAGE = 1;

// Reads a positive integer query value, or null when it is missing or malformed.
function readPositiveInt(value: string | null) {
  if (value === null || !/^[0-9]+$/.test(value)) return null;
  const parsed = Number(value);
  return parsed >= 1 ? parsed : null;
}

// Reads the users list filters from URL search params, replacing anything invalid with its default.
export function readUserFilters(params: URLSearchParams): UserListFilters {
  const roleCode = params.get("roleCode") ?? "";
  const pageSize = readPositiveInt(params.get("pageSize"));
  return {
    search: (params.get("search") ?? "").slice(0, SEARCH_MAX_LENGTH),
    roleCode: isKnownRole(roleCode) ? roleCode : "",
    page: readPositiveInt(params.get("page")) ?? FIRST_PAGE,
    pageSize: pageSize !== null && (PAGE_SIZE_OPTIONS as readonly number[]).includes(pageSize) ? pageSize : DEFAULT_PAGE_SIZE,
  };
}

// Writes filters back to search params, leaving out values that equal their defaults.
export function toUserFilterParams(filters: UserListFilters) {
  const params = new URLSearchParams();
  if (filters.search) params.set("search", filters.search);
  if (filters.roleCode) params.set("roleCode", filters.roleCode);
  if (filters.page !== FIRST_PAGE) params.set("page", String(filters.page));
  if (filters.pageSize !== DEFAULT_PAGE_SIZE) params.set("pageSize", String(filters.pageSize));
  return params;
}
