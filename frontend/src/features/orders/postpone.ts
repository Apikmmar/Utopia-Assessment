import type { OrderStatus } from "./statuses";

export const POSTPONE_REASONS = ["customer_unavailable", "parts_needed", "access_problem", "weather", "technician_unavailable", "other"] as const;
export type PostponeReason = (typeof POSTPONE_REASONS)[number];

export const POSTPONE_REASON_LABELS: Record<PostponeReason, string> = {
  customer_unavailable: "Customer unavailable",
  parts_needed: "Parts needed",
  access_problem: "Access problem",
  weather: "Weather",
  technician_unavailable: "Technician unavailable",
  other: "Other",
};

export const POSTPONABLE_STATUSES: readonly OrderStatus[] = ["assigned", "in_progress"];
export const POSTPONE_MAX_DAYS_AHEAD = 90;

const BUSINESS_TIME_ZONE = "Asia/Kuala_Lumpur";
const DAY_MS = 24 * 60 * 60 * 1000;
const ISO_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;
const isoDateFormatter = new Intl.DateTimeFormat("en-CA", { timeZone: BUSINESS_TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit" });
const plainDateFormatter = new Intl.DateTimeFormat("en-MY", { timeZone: "UTC", day: "numeric", month: "short", year: "numeric" });

// Returns the display label for a reason code, or the raw code for one this client does not know.
export function postponeReasonLabel(code: string) {
  return (POSTPONE_REASONS as readonly string[]).includes(code) ? POSTPONE_REASON_LABELS[code as PostponeReason] : code;
}

// Returns whether a status still allows a visit to be postponed.
export function isPostponable(status: string) {
  return (POSTPONABLE_STATUSES as readonly string[]).includes(status);
}

// Returns today's date in business time as YYYY-MM-DD.
export function businessToday(now = new Date()) {
  return isoDateFormatter.format(now);
}

// Returns a YYYY-MM-DD date moved by a number of days.
export function addDays(isoDate: string, days: number) {
  return new Date(Date.parse(`${isoDate}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10);
}

// Formats a YYYY-MM-DD date such as "10 Nov 2026", or returns null for anything else.
export function formatPlainDate(value: unknown) {
  if (typeof value !== "string" || !ISO_DATE_PATTERN.test(value)) return null;
  const time = Date.parse(`${value}T00:00:00Z`);
  return Number.isNaN(time) ? null : plainDateFormatter.format(new Date(time));
}
