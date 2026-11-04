import { ApiError } from "./api-client";

export const MAX_QUERY_RETRIES = 2;
export const QUERY_STALE_TIME_MS = 30_000;

const RETRYABLE_STATUSES: readonly number[] = [0, 502, 503];
const RETRY_BASE_DELAY_MS = 250;
const RETRY_MAX_DELAY_MS = 1_000;
const RETRY_JITTER_MS = 150;

// Allows a query retry only for transient failures (no answer, 502, 503) and at most twice.
export function shouldRetryQuery(failureCount: number, error: unknown) {
  return failureCount < MAX_QUERY_RETRIES && error instanceof ApiError && RETRYABLE_STATUSES.includes(error.status);
}

// Returns a small exponential backoff with random jitter so clients do not retry in lockstep.
export function queryRetryDelay(failureCount: number, random: () => number = Math.random) {
  return Math.min(RETRY_MAX_DELAY_MS, RETRY_BASE_DELAY_MS * 2 ** failureCount) + Math.floor(random() * RETRY_JITTER_MS);
}
