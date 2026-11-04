import { ApiError } from "./api-client";

// Returns the generic failure text, adding the server's correlation id so support can trace a 500.
export function failureMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError && error.status >= 500 && error.correlationId) return `${fallback} Reference: ${error.correlationId}`;
  return fallback;
}
