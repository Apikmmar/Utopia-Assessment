import { describe, expect, it } from "vitest";
import { ApiError } from "./api-client";
import { queryRetryDelay, shouldRetryQuery } from "./query-retry";

// Builds an ApiError with only the status that the retry policy reads.
function failure(status: number) {
  return new ApiError(status, `HTTP_${status}`, "failed");
}

describe("shouldRetryQuery", () => {
  it.each([0, 502, 503])("retries status %i on the first and second failure only", (status) => {
    expect(shouldRetryQuery(0, failure(status))).toBe(true);
    expect(shouldRetryQuery(1, failure(status))).toBe(true);
    expect(shouldRetryQuery(2, failure(status))).toBe(false);
  });

  it.each([400, 401, 403, 404, 409, 422, 500, 504])("never retries status %i", (status) => {
    expect(shouldRetryQuery(0, failure(status))).toBe(false);
  });

  it("never retries a failure that is not an ApiError, such as a contract parse error", () => {
    expect(shouldRetryQuery(0, new Error("bad shape"))).toBe(false);
  });
});

describe("queryRetryDelay", () => {
  it("backs off exponentially with bounded jitter and a one-second cap", () => {
    expect(queryRetryDelay(0, () => 0)).toBe(250);
    expect(queryRetryDelay(1, () => 0)).toBe(500);
    expect(queryRetryDelay(1, () => 0.999)).toBe(649);
    expect(queryRetryDelay(5, () => 0)).toBe(1000);
  });
});
