import { describe, expect, it, vi } from "vitest";
import { ApiError, NETWORK_ERROR_CODE, apiRequest, parseApiError } from "./api-client";
import { failureMessage } from "./failure-message";

describe("parseApiError", () => {
  it("reads detail, code, and camelCase fields from the backend error body", () => {
    const error = parseApiError(422, {
      detail: "Choose a stronger password.",
      code: "WEAK_PASSWORD",
      fields: { newPassword: "too_common" },
    });
    expect(error).toMatchObject({ status: 422, code: "WEAK_PASSWORD", message: "Choose a stronger password.", fields: { newPassword: "too_common" } });
    expect(error.correlationId).toBeNull();
  });

  it("keeps the correlation id of a 500", () => {
    const error = parseApiError(500, { detail: "Internal server error.", code: "INTERNAL_ERROR", correlationId: "req-123" });
    expect(error.correlationId).toBe("req-123");
  });

  it("falls back to an HTTP code and a generic message for a body that is not the contract", () => {
    const error = parseApiError(502, "<html>Bad gateway</html>");
    expect(error).toMatchObject({ status: 502, code: "HTTP_502", message: "Something went wrong. Please try again.", fields: {} });
  });

  it("drops non-string field messages", () => {
    const error = parseApiError(422, { detail: "x", code: "VALIDATION_FAILED", fields: { email: "Bad email.", age: 7, nested: { a: "b" } } });
    expect(error.fields).toEqual({ email: "Bad email." });
  });
});

describe("apiRequest failures", () => {
  it("turns a network failure into a status-0 ApiError", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const error = await apiRequest("/users").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 0, code: NETWORK_ERROR_CODE });
  });

  it("rethrows a cancellation unchanged", async () => {
    const controller = new AbortController();
    controller.abort();
    const abort = new DOMException("Aborted", "AbortError");
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(abort));
    await expect(apiRequest("/users", { signal: controller.signal })).rejects.toBe(abort);
  });

  it("parses a non-JSON error response without throwing a parse error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("gateway down", { status: 503 })));
    await expect(apiRequest("/users")).rejects.toMatchObject({ status: 503, code: "HTTP_503" });
  });
});

describe("failureMessage", () => {
  it("adds the correlation id to the generic text only for a server error that has one", () => {
    expect(failureMessage(new ApiError(500, "INTERNAL_ERROR", "x", {}, "req-9"), "Failed.")).toBe("Failed. Reference: req-9");
    expect(failureMessage(new ApiError(500, "INTERNAL_ERROR", "x"), "Failed.")).toBe("Failed.");
    expect(failureMessage(new ApiError(409, "EMAIL_TAKEN", "x", {}, "req-9"), "Failed.")).toBe("Failed.");
    expect(failureMessage(new Error("boom"), "Failed.")).toBe("Failed.");
  });
});
