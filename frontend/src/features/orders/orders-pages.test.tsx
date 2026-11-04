import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { adminUser, errorReply, mockBackend, technicianUser, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";

const managerUser = { userId: "44444444-4444-4444-8444-444444444444", name: "Max Manager", email: "max@example.com", roleCode: "manager" };
const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const SERVICE_TYPE = { serviceTypeId: "77777777-7777-4777-8777-777777777777", code: "repair", name: "Repair" };
const TECHNICIAN = { userId: technicianUser.userId, name: "Tom Tech", phone: "60111111111" };

// Builds one order in the response shape, with overrides.
function order(overrides: Record<string, unknown> = {}) {
  return {
    orderId: ORDER_ID,
    orderNo: "ORD-000123",
    customerName: "Siti Customer",
    customerPhone: "60123456789",
    address: "No 1, Jalan Damai, KL",
    problemDescription: "Aircond leaking",
    serviceType: SERVICE_TYPE,
    quotedPrice: "150.00",
    technician: TECHNICIAN,
    adminNotes: "Bring a ladder",
    status: "assigned",
    statusChangedAt: "2026-11-04T07:00:00Z",
    startedAt: null,
    jobDoneAt: null,
    reviewedAt: null,
    closedAt: null,
    createdAt: "2026-11-04T07:00:00Z",
    ...overrides,
  };
}

// Builds one order list row from an order.
function listItem(overrides: Record<string, unknown> = {}) {
  const { customerPhone: _phone, problemDescription: _problem, adminNotes: _notes, statusChangedAt: _changed, startedAt: _started, jobDoneAt: _done, reviewedAt: _reviewed, closedAt: _closed, ...rest } = order(overrides);
  return { ...rest, technician: rest.technician ? { userId: TECHNICIAN.userId, name: TECHNICIAN.name } : null };
}

// Wraps items in the paginated list shape.
function page(items: unknown[]) {
  return { status: 200, body: { items, total: items.length, page: 1, pageSize: 20 } };
}

// Registers a session for the user plus the handlers every signed-in page needs.
function backend(user: Record<string, unknown>, handlers: Record<string, MockHandler>) {
  return mockBackend({
    "GET /auth/me": { status: 200, body: { user } },
    "GET /notifications": page([]),
    "GET /service-types": { status: 200, body: { items: [SERVICE_TYPE] } },
    "GET /users": { status: 200, body: { items: [{ ...TECHNICIAN, email: "tom@example.com", age: null, roleCode: "technician", createdAt: "2026-11-01T00:00:00Z" }], total: 1, page: 1, pageSize: 100 } },
    ...handlers,
  });
}

describe("orders pages (mocked backend: fetch is stubbed, no real server)", () => {
  it("validates the create form before sending anything", async () => {
    const calls = backend(adminUser, {});
    renderApp("/orders/new");
    await userEvent.click(await screen.findByRole("button", { name: "Create order" }));
    expect(await screen.findByText("Enter the customer's name.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid phone number.")).toBeInTheDocument();
    expect(screen.getByText("Choose a service type.")).toBeInTheDocument();
    expect(screen.getByText("Enter an amount such as 150 or 150.50.")).toBeInTheDocument();
    expect(calls.some((call) => call.method === "POST")).toBe(false);
  });

  it("shows server field errors next to their inputs and keeps the input", async () => {
    backend(adminUser, {
      "POST /orders": errorReply(422, "VALIDATION_FAILED", "One or more fields are invalid.", { fields: { customerPhone: "Enter a valid phone number from the server." } }),
    });
    renderApp("/orders/new");
    await fillCreateForm();
    await userEvent.click(screen.getByRole("button", { name: "Create order" }));
    expect(await screen.findByText("Enter a valid phone number from the server.")).toBeInTheDocument();
    expect(screen.getByLabelText("Customer name")).toHaveValue("Siti Customer");
  });

  it("creates an order with a technician and opens it with the created notice", async () => {
    const calls = backend(adminUser, {
      "POST /orders": { status: 201, body: { order: order(), notification: null } },
      [`GET /orders/${ORDER_ID}`]: { status: 200, body: { order: order(), events: [] } },
    });
    const { router } = renderApp("/orders/new");
    await fillCreateForm();
    await userEvent.selectOptions(screen.getByLabelText("Technician (optional)"), TECHNICIAN.userId);
    await userEvent.click(screen.getByRole("button", { name: "Create order" }));
    expect(await screen.findByText(/Order ORD-000123 created/)).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(`/orders/${ORDER_ID}`);
    const body = calls.find((call) => call.method === "POST" && call.path === "/orders")!.body as Record<string, unknown>;
    expect(body).toMatchObject({ customerName: "Siti Customer", quotedPrice: "150.50", technicianId: TECHNICIAN.userId, serviceTypeId: SERVICE_TYPE.serviceTypeId });
    expect(body).not.toHaveProperty("adminNotes");
  });

  it("keeps the order filters in the URL and sends them to the server", async () => {
    const calls = backend(adminUser, { "GET /orders": page([listItem()]) });
    const { router } = renderApp("/orders?status=assigned&sort=oldest");
    expect(await screen.findByRole("link", { name: "ORD-000123" })).toBeInTheDocument();
    const listCall = calls.filter((call) => call.path === "/orders").at(-1)!;
    expect(listCall.query.getAll("status")).toEqual(["assigned"]);
    expect(listCall.query.get("sort")).toBe("oldest");
    await userEvent.selectOptions(screen.getByLabelText("Status"), "");
    expect(router.state.location.search).toBe("?sort=oldest");
  });

  it("offers edit and assign only while the order has not started", async () => {
    backend(adminUser, { [`GET /orders/${ORDER_ID}`]: { status: 200, body: { order: order(), events: [] } } });
    renderApp(`/orders/${ORDER_ID}`);
    expect(await screen.findByRole("link", { name: "Edit details" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reassign" })).toBeInTheDocument();
  });

  it("hides edit and assign once the job has started", async () => {
    backend(adminUser, { [`GET /orders/${ORDER_ID}`]: { status: 200, body: { order: order({ status: "in_progress" }), events: [] } } });
    renderApp(`/orders/${ORDER_ID}`);
    expect(await screen.findByText("Job instructions")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Edit details" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /assign/i })).not.toBeInTheDocument();
  });

  it("refreshes the order and explains when a review loses to a status change", async () => {
    let status = "job_done";
    const calls = backend(managerUser, {
      [`GET /orders/${ORDER_ID}`]: () => ({ status: 200, body: { order: order({ status }), events: [] } }),
      [`POST /orders/${ORDER_ID}/review`]: () => {
        status = "reviewed";
        return errorReply(409, "INVALID_TRANSITION", "The order is now reviewed, so this action is not allowed.");
      },
    });
    renderApp(`/orders/${ORDER_ID}`);
    await userEvent.click(await screen.findByRole("button", { name: "Mark reviewed" }));
    expect(await screen.findByText(/status changed in the meantime/)).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Close order" })).toBeInTheDocument();
    expect(calls.filter((call) => call.path === `/orders/${ORDER_ID}` && call.method === "GET").length).toBeGreaterThan(1);
  });

  it("lists the manager's review queue oldest first", async () => {
    const calls = backend(managerUser, { "GET /orders": page([listItem({ status: "job_done" })]) });
    renderApp("/review");
    expect(await screen.findByRole("link", { name: "ORD-000123" })).toBeInTheDocument();
    const listCall = calls.filter((call) => call.path === "/orders").at(-1)!;
    expect(listCall.query.get("sort")).toBe("oldest");
    expect(listCall.query.getAll("status")).toEqual(["job_done"]);
  });
});

describe("technician screens (mocked backend: fetch is stubbed, no real server)", () => {
  it("lists active jobs as large cards linking to the job page", async () => {
    backend(technicianUser, {
      "GET /orders": (call) => page(call.query.getAll("status").includes("assigned") ? [listItem()] : []),
    });
    renderApp("/jobs");
    const card = await screen.findByRole("link", { name: /ORD-000123/ });
    expect(card).toHaveAttribute("href", `/jobs/${ORDER_ID}`);
    expect(card.className).toContain("min-h-11");
    expect(screen.queryByText("No active jobs right now.")).not.toBeInTheDocument();
  });

  it("shows the job in visit order with call, maps, instructions, and a full-width Start job button", async () => {
    let status = "assigned";
    const calls = backend(technicianUser, {
      [`GET /orders/${ORDER_ID}`]: () => ({ status: 200, body: { order: order({ status }), events: [] } }),
      [`POST /orders/${ORDER_ID}/start`]: () => {
        status = "in_progress";
        return { status: 200, body: { order: order({ status }) } };
      },
    });
    renderApp(`/jobs/${ORDER_ID}`);
    expect(await screen.findByRole("link", { name: "Call 60123456789" })).toHaveAttribute("href", "tel:+60123456789");
    expect(screen.getByRole("link", { name: "Open in Maps" })).toHaveAttribute("href", expect.stringContaining(encodeURIComponent("No 1, Jalan Damai, KL")));
    expect(screen.getByText("Bring a ladder")).toBeInTheDocument();
    const start = screen.getByRole("button", { name: "Start job" });
    expect(start.className).toContain("min-h-11");
    expect(start.className).toContain("w-full");
    await userEvent.click(start);
    await waitFor(() => expect(calls.some((call) => call.method === "POST" && call.path.endsWith("/start"))).toBe(true));
    await waitFor(() => expect(screen.queryByRole("button", { name: "Start job" })).not.toBeInTheDocument());
  });

  it("refuses a job assigned to someone else", async () => {
    backend(technicianUser, { [`GET /orders/${ORDER_ID}`]: errorReply(404, "ORDER_NOT_FOUND", "Order not found.") });
    renderApp(`/jobs/${ORDER_ID}`);
    expect(await screen.findByText("This job is not assigned to you.")).toBeInTheDocument();
  });
});

// Fills every required create field with valid values.
async function fillCreateForm() {
  await userEvent.type(await screen.findByLabelText("Customer name"), "Siti Customer");
  await userEvent.type(screen.getByLabelText("Customer phone"), "012-345 6789");
  await userEvent.type(screen.getByLabelText("Service address"), "No 1, Jalan Damai, KL");
  await userEvent.type(screen.getByLabelText("Problem description"), "Aircond leaking");
  await waitFor(() => expect(screen.getByRole("option", { name: "Repair" })).toBeInTheDocument());
  await userEvent.selectOptions(screen.getByLabelText("Service type"), SERVICE_TYPE.serviceTypeId);
  await userEvent.type(screen.getByLabelText("Quoted price (RM)"), "150.50");
}
