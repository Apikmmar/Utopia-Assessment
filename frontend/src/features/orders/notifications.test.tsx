import { act, renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { adminUser, mockBackend, technicianUser, type MockCall, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";
import { usePrepareTimeout } from "./hooks/use-prepare-timeout";
import { PREPARE_TIMEOUT_MS, POLL_INTERVAL_MS } from "./notifications";

const managerUser = { userId: "44444444-4444-4444-8444-444444444444", name: "Max Manager", email: "max@example.com", roleCode: "manager" };
const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const DEEP_LINK = "https://wa.me/60123456789?text=Hi%20Siti";

// Builds one notification in the response shape, with overrides.
function notification(overrides: Record<string, unknown> = {}) {
  return {
    notificationId: "66666666-6666-4666-8666-666666666666",
    orderId: ORDER_ID,
    orderNo: "ORD-000123",
    notificationType: "job_done",
    channel: "whatsapp",
    recipientType: "customer",
    recipientName: "Siti",
    recipientPhone: "60123456789",
    message: "Hi Siti",
    deepLink: DEEP_LINK,
    status: "ready",
    readyAt: "2026-11-04T07:45:00Z",
    openedAt: null,
    openedBy: null,
    canSend: true,
    createdAt: "2026-11-04T07:44:00Z",
    ...overrides,
  };
}

// Wraps items in the paginated list shape.
function page(items: unknown[]) {
  return { status: 200, body: { items, total: items.length, page: 1, pageSize: 20 } };
}

// Registers a session for the user and the given handlers.
function backend(user: Record<string, unknown>, handlers: Record<string, MockHandler>) {
  return mockBackend({ "GET /auth/me": { status: 200, body: { user } }, ...handlers });
}

// Returns whether a call is the page list rather than the navigation count.
function isPageList(call: MockCall) {
  return call.method === "GET" && call.path === "/notifications" && !call.query.has("sendable");
}

afterEach(() => {
  vi.useRealTimers();
});

describe("notifications page (mocked backend: fetch is stubbed, no real server)", () => {
  it("shows a ready notification as a WhatsApp link that records the opening", async () => {
    const calls = backend(technicianUser, {
      "GET /notifications": page([notification()]),
      "POST /notifications/66666666-6666-4666-8666-666666666666/open": { status: 200, body: { notification: notification({ status: "opened" }) } },
    });
    renderApp("/notifications");
    const link = await screen.findByRole("link", { name: "Send WhatsApp to Siti" });
    expect(link).toHaveAttribute("href", DEEP_LINK);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
    await userEvent.click(link);
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.path.endsWith("/open"))).toBe(true));
  });

  it("moves a row from Pending to Sent after it is sent", async () => {
    let opened = false;
    backend(technicianUser, {
      "GET /notifications": (call) => {
        if (call.query.get("state") === "sent") return page(opened ? [notification({ status: "opened", openedAt: "2026-11-04T08:00:00Z", openedBy: { userId: technicianUser.userId, name: "Tom Tech" } })] : []);
        return page(opened ? [] : [notification()]);
      },
      "POST /notifications/66666666-6666-4666-8666-666666666666/open": () => {
        opened = true;
        return { status: 200, body: { notification: notification({ status: "opened" }) } };
      },
    });
    renderApp("/notifications");
    await userEvent.click(await screen.findByRole("link", { name: "Send WhatsApp to Siti" }));
    expect(await screen.findByText("Nothing waiting to be sent.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Sent" }));
    expect(await screen.findByRole("link", { name: "Send again" })).toBeInTheDocument();
    expect(screen.getByText(/by Tom Tech/)).toBeInTheDocument();
    expect(screen.getByText(/cannot confirm it was delivered/)).toBeInTheDocument();
  });

  it("shows a preparing state while queued and stops polling once ready", async () => {
    let listCalls = 0;
    const calls = backend(technicianUser, {
      "GET /notifications": (call) => {
        if (!isPageList(call)) return page([]);
        listCalls += 1;
        return page([notification(listCalls === 1 ? { status: "queued", message: null, deepLink: null } : {})]);
      },
    });
    renderApp("/notifications");
    expect(await screen.findByRole("button", { name: "Preparing WhatsApp message…" })).toBeDisabled();
    expect(await screen.findByRole("link", { name: "Send WhatsApp to Siti" }, { timeout: POLL_INTERVAL_MS + 2000 })).toBeInTheDocument();
    const settled = calls.filter(isPageList).length;
    await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS + 500));
    expect(calls.filter(isPageList).length).toBe(settled);
  }, 10_000);

  it("explains a failed message and offers Retry only to admins", async () => {
    const failed = notification({ status: "failed", message: null, deepLink: null, canSend: false });
    const calls = backend(adminUser, {
      "GET /notifications": page([failed]),
      "POST /notifications/66666666-6666-4666-8666-666666666666/retry": { status: 200, body: { notification: notification({ status: "queued", message: null, deepLink: null }) } },
    });
    renderApp("/notifications");
    expect(await screen.findByText(/could not be prepared yet/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(calls.some((call) => call.path.endsWith("/retry"))).toBe(true));
  });

  it("does not offer Retry to a technician", async () => {
    backend(technicianUser, { "GET /notifications": page([notification({ status: "failed", message: null, deepLink: null, canSend: false })]) });
    renderApp("/notifications");
    expect(await screen.findByText(/could not be prepared yet/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });

  it("shows managers every message without send buttons and without a navigation count", async () => {
    const calls = backend(managerUser, { "GET /notifications": page([notification({ canSend: false })]) });
    renderApp("/notifications");
    expect(await screen.findByText("ORD-000123")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Send/ })).not.toBeInTheDocument();
    expect(calls.some((call) => call.query.has("sendable"))).toBe(false);
  });

  it("never renders a link that is not a WhatsApp link", async () => {
    backend(adminUser, { "GET /notifications": page([notification({ deepLink: "javascript:alert(1)" })]) });
    renderApp("/notifications");
    expect(await screen.findByText("ORD-000123")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Send WhatsApp/ })).not.toBeInTheDocument();
  });

  it("keeps the tab, search, and type in the URL and sends them as filters", async () => {
    const calls = backend(adminUser, { "GET /notifications": page([]) });
    const { router } = renderApp("/notifications?tab=sent&search=ORD-0001&type=job_assigned");
    expect(await screen.findByRole("tab", { name: "Sent" })).toHaveAttribute("aria-selected", "true");
    await waitFor(() => expect(calls.some((call) => isPageList(call) && call.query.get("state") === "sent")).toBe(true));
    const listCall = calls.filter(isPageList).at(-1)!;
    expect(listCall.query.get("search")).toBe("ORD-0001");
    expect(listCall.query.get("notificationType")).toBe("job_assigned");
    await userEvent.click(screen.getByRole("tab", { name: "Pending" }));
    expect(router.state.location.search).toBe("?search=ORD-0001&type=job_assigned");
  });

  it("shows the count of messages the user is to send in the navigation", async () => {
    backend(technicianUser, {
      "GET /notifications": (call) => (call.query.has("sendable") ? { status: 200, body: { items: [notification()], total: 3, page: 1, pageSize: 1 } } : page([])),
    });
    renderApp("/notifications");
    const nav = await screen.findByRole("navigation", { name: "Main" });
    const link = within(nav).getByRole("link", { name: /Notifications/ });
    await waitFor(() => expect(link).toHaveTextContent("Notifications3 to send"));
  });
});

describe("prepare timeout", () => {
  it("expires only after the message stays queued for 30 seconds", () => {
    vi.useFakeTimers();
    const { result, rerender } = renderHook(({ queued }) => usePrepareTimeout(queued), { initialProps: { queued: true } });
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(PREPARE_TIMEOUT_MS - 1));
    expect(result.current).toBe(false);
    act(() => vi.advanceTimersByTime(1));
    expect(result.current).toBe(true);
    rerender({ queued: false });
    expect(result.current).toBe(false);
  });
});
