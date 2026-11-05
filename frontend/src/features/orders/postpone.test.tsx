import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { adminUser, errorReply, mockBackend, technicianUser, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";
import { eventNote } from "./components/event-timeline";

const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const POSTPONE_PATH = `/orders/${ORDER_ID}/postpone`;
const managerUser = { userId: "33333333-3333-4333-8333-333333333333", name: "Max Manager", email: "max@example.com", roleCode: "manager" };

// Builds the order in the given status, assigned to the test technician.
function order(status: string) {
  return {
    orderId: ORDER_ID, orderNo: "ORD-000123", customerName: "Siti Customer", customerPhone: "60123456789", address: "No 1, Jalan Damai, KL",
    problemDescription: "Aircond leaking", serviceType: { serviceTypeId: "77777777-7777-4777-8777-777777777777", code: "repair", name: "Repair" },
    quotedPrice: "150.00", technician: { userId: technicianUser.userId, name: "Tom Tech", phone: "60111111111" }, adminNotes: null, status,
    statusChangedAt: "2026-11-04T07:00:00Z", startedAt: null, jobDoneAt: null, reviewedAt: null, closedAt: null, createdAt: "2026-11-04T07:00:00Z",
  };
}

const POSTPONED_EVENT = {
  eventType: "postponed", fromStatus: "assigned", toStatus: "assigned", actor: { userId: technicianUser.userId, name: "Tom Tech" },
  detail: { reasonCode: "parts_needed", newDate: "2026-11-10", technicianId: technicianUser.userId }, createdAt: "2026-11-04T08:00:00Z",
};

// Registers the session user, the order in a status, and extra handlers.
function backend(user: object, status: string, handlers: Record<string, MockHandler> = {}) {
  return mockBackend({
    "GET /auth/me": { status: 200, body: { user } },
    "GET /notifications": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } },
    [`GET /orders/${ORDER_ID}`]: { status: 200, body: { order: order(status), events: [] } },
    [`GET /orders/${ORDER_ID}/attachments`]: { status: 200, body: { items: [] } },
    [`GET /orders/${ORDER_ID}/completion`]: errorReply(404, "COMPLETION_NOT_FOUND", "No completion."),
    ...handlers,
  });
}

// Returns the postpone calls recorded so far.
function postpones(calls: { method: string; path: string }[]) {
  return calls.filter((call) => call.method === "POST" && call.path === POSTPONE_PATH);
}

// Opens the job page as the technician and the postpone form.
async function openForm() {
  renderApp(`/jobs/${ORDER_ID}`);
  await userEvent.click(await screen.findByRole("button", { name: "Postpone visit" }));
  return screen.getByRole("form", { name: "Postpone visit" });
}

describe("postpone visit (mocked backend: fetch is stubbed)", () => {
  it("asks for a reason before sending, then sends the reason and date once", async () => {
    let release: (reply: { status: number; body: unknown }) => void = () => undefined;
    const calls = backend(technicianUser, "assigned", { [`POST ${POSTPONE_PATH}`]: () => new Promise((resolve) => (release = resolve)) });
    const form = await openForm();
    await userEvent.click(within(form).getByRole("button", { name: "Save postponement" }));
    expect(await within(form).findByText("Choose a reason.")).toBeInTheDocument();
    expect(postpones(calls)).toHaveLength(0);
    await userEvent.selectOptions(within(form).getByLabelText("Reason"), "parts_needed");
    fireEvent.change(within(form).getByLabelText("New date (optional)"), { target: { value: "2026-11-10" } });
    const save = within(form).getByRole("button", { name: "Save postponement" });
    fireEvent.click(save);
    fireEvent.click(save);
    await waitFor(() => expect(postpones(calls)).toHaveLength(1));
    expect(postpones(calls)[0]).toMatchObject({ body: { reasonCode: "parts_needed", newDate: "2026-11-10" } });
    release({ status: 200, body: { order: order("assigned") } });
    expect(await screen.findByText("Visit postponed. It is recorded in the order activity.")).toBeInTheDocument();
    expect(postpones(calls)).toHaveLength(1);
  });

  it("shows a server date error on the date field", async () => {
    backend(technicianUser, "in_progress", {
      [`POST ${POSTPONE_PATH}`]: errorReply(422, "VALIDATION_FAILED", "One or more fields are invalid.", { fields: { newDate: "Choose today or a later date." } }),
    });
    const form = await openForm();
    await userEvent.selectOptions(within(form).getByLabelText("Reason"), "weather");
    await userEvent.click(within(form).getByRole("button", { name: "Save postponement" }));
    await waitFor(() => expect(within(form).getByLabelText("New date (optional)")).toHaveAccessibleDescription(/Choose today or a later date\./));
  });

  it("explains a 409 and refreshes the order", async () => {
    const calls = backend(technicianUser, "assigned", {
      [`POST ${POSTPONE_PATH}`]: errorReply(409, "INVALID_TRANSITION", "The order is now job_done, so this action is not allowed."),
    });
    const form = await openForm();
    await userEvent.selectOptions(within(form).getByLabelText("Reason"), "weather");
    await userEvent.click(within(form).getByRole("button", { name: "Save postponement" }));
    expect(await screen.findByText(/status changed in the meantime/)).toBeInTheDocument();
    await waitFor(() => expect(calls.filter((call) => call.method === "GET" && call.path === `/orders/${ORDER_ID}`).length).toBeGreaterThan(1));
  });

  it("is hidden once the job is done and for managers", async () => {
    backend(technicianUser, "job_done");
    renderApp(`/jobs/${ORDER_ID}`);
    expect(await screen.findByRole("heading", { name: "ORD-000123" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Postpone visit" })).not.toBeInTheDocument();
  });

  it("is hidden for managers on the order page and shown for admins", async () => {
    backend(managerUser, "assigned");
    const manager = renderApp(`/orders/${ORDER_ID}`);
    expect(await screen.findByRole("heading", { name: "ORD-000123" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Postpone visit" })).not.toBeInTheDocument();
    manager.unmount();
    backend(adminUser, "assigned", { "GET /users": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 100 } } });
    renderApp(`/orders/${ORDER_ID}`);
    expect(await screen.findByRole("button", { name: "Postpone visit" })).toBeInTheDocument();
  });

  it("describes a postponement on the timeline", () => {
    expect(eventNote(POSTPONED_EVENT)).toBe("Parts needed, new date 10 Nov 2026");
    expect(eventNote({ ...POSTPONED_EVENT, detail: { reasonCode: "weather", newDate: null } })).toBe("Weather");
    expect(eventNote({ ...POSTPONED_EVENT, eventType: "started" })).toBeNull();
  });
});
