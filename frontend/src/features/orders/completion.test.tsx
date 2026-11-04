import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { FakeXhr } from "@/test-support/fake-xhr";
import { errorReply, mockBackend, technicianUser, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";

const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const ATTACHMENT_ID = "88888888-8888-4888-8888-888888888888";
const NOTIFICATION_ID = "99999999-9999-4999-8999-999999999999";
const JOB_PATH = `/jobs/${ORDER_ID}`;
const COMPLETION_PATH = `/orders/${ORDER_ID}/completion`;

// Builds the job in the order response shape.
function order(status: string) {
  return {
    orderId: ORDER_ID, orderNo: "ORD-000123", customerName: "Siti Customer", customerPhone: "60123456789", address: "No 1, Jalan Damai, KL",
    problemDescription: "Aircond leaking", serviceType: { serviceTypeId: "77777777-7777-4777-8777-777777777777", code: "repair", name: "Repair" },
    quotedPrice: "150.00", technician: { userId: technicianUser.userId, name: "Tom Tech", phone: "60111111111" }, adminNotes: null, status,
    statusChangedAt: "2026-11-04T07:00:00Z", startedAt: "2026-11-04T07:10:00Z", jobDoneAt: status === "in_progress" ? null : "2026-11-04T07:45:00Z",
    reviewedAt: null, closedAt: null, createdAt: "2026-11-04T07:00:00Z",
  };
}

const COMPLETION = {
  completionId: "66666666-6666-4666-8666-666666666666", orderId: ORDER_ID, technician: { userId: technicianUser.userId, name: "Tom Tech" },
  workDone: "Cleaned the filter", quotedPrice: "150.00", extraCharges: "20.50", finalAmount: "170.50", remarks: null, payment: null,
  completedAt: "2026-11-04T07:45:00Z",
};

// Builds the customer's job_done notification in the given status.
function customerNotification(status: string) {
  const ready = status !== "queued";
  return {
    notificationId: NOTIFICATION_ID, orderId: ORDER_ID, orderNo: "ORD-000123", notificationType: "job_done", channel: "whatsapp",
    recipientType: "customer", recipientName: "Siti Customer", recipientPhone: "60123456789", message: ready ? "Hi Siti" : null,
    deepLink: ready ? "https://wa.me/60123456789?text=Hi%20Siti" : null, status, readyAt: null, openedAt: null, openedBy: null,
    canSend: ready, createdAt: "2026-11-04T07:45:00Z",
  };
}

// Registers the technician session, the in-progress job, and the given extra handlers.
function backend(handlers: Record<string, MockHandler> = {}) {
  return mockBackend({
    "GET /auth/me": { status: 200, body: { user: technicianUser } },
    "GET /notifications": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } },
    [`GET /orders/${ORDER_ID}`]: { status: 200, body: { order: order("in_progress"), events: [] } },
    [`GET /orders/${ORDER_ID}/attachments`]: { status: 200, body: { items: [] } },
    ...handlers,
  });
}

// Opens the job page and types the required work done.
async function openForm(workDone = "Cleaned the filter") {
  renderApp(JOB_PATH);
  await userEvent.type(await screen.findByLabelText("Work done"), workDone);
}

// Returns the completion submit calls recorded so far.
function submits(calls: { method: string; path: string }[]) {
  return calls.filter((call) => call.method === "POST" && call.path === COMPLETION_PATH);
}

beforeEach(() => {
  FakeXhr.instances = [];
  vi.stubGlobal("XMLHttpRequest", FakeXhr);
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("completion form (mocked backend and storage: fetch and XMLHttpRequest are stubbed)", () => {
  it("previews the final amount as quoted price plus extra charges", async () => {
    backend();
    await openForm();
    expect(screen.getByTestId("final-amount-preview")).toHaveTextContent("150.00");
    await userEvent.type(screen.getByLabelText("Extra charges (RM)"), "20.50");
    expect(screen.getByTestId("final-amount-preview")).toHaveTextContent("170.50");
    await userEvent.clear(screen.getByLabelText("Extra charges (RM)"));
    await userEvent.type(screen.getByLabelText("Extra charges (RM)"), "abc");
    expect(screen.getByTestId("final-amount-preview")).toHaveTextContent("—");
  });

  it("disables submit while a file uploads and sends the uploaded file with the completion", async () => {
    const calls = backend({
      [`POST /orders/${ORDER_ID}/attachments`]: {
        status: 201,
        body: { attachment: { attachmentId: ATTACHMENT_ID, kind: "completion", fileName: "photo.jpg", contentType: "image/jpeg", sizeBytes: 1000, status: "pending", viewUrl: null }, uploadUrl: "https://storage.test/upload/x?token=t" },
      },
      [`POST ${COMPLETION_PATH}`]: { status: 201, body: { completion: COMPLETION, order: order("job_done"), notification: customerNotification("queued") } },
    });
    await openForm();
    fireEvent.change(screen.getByLabelText("Photos, videos, or PDFs"), { target: { files: [new File(["x"], "photo.jpg", { type: "image/jpeg" })] } });
    await waitFor(() => expect(FakeXhr.instances).toHaveLength(1));
    expect(screen.getByRole("button", { name: "Waiting for files…" })).toBeDisabled();
    FakeXhr.instances[0].respond(200);
    const submit = await screen.findByRole("button", { name: "Submit completion" });
    expect(submit).toBeEnabled();
    await userEvent.click(submit);
    await waitFor(() => expect(submits(calls)).toHaveLength(1));
    expect(submits(calls)[0]).toMatchObject({ body: { workDone: "Cleaned the filter", extraCharges: "0", attachmentIds: [ATTACHMENT_ID] } });
  });

  it("sends one request when submit is clicked twice", async () => {
    let release: (reply: { status: number; body: unknown }) => void = () => undefined;
    const calls = backend({ [`POST ${COMPLETION_PATH}`]: () => new Promise((resolve) => (release = resolve)) });
    await openForm();
    const submit = screen.getByRole("button", { name: "Submit completion" });
    fireEvent.click(submit);
    fireEvent.click(submit);
    await waitFor(() => expect(submits(calls)).toHaveLength(1));
    expect(await screen.findByRole("button", { name: "Submitting…" })).toBeDisabled();
    release({ status: 201, body: { completion: COMPLETION, order: order("job_done"), notification: customerNotification("queued") } });
    await waitFor(() => expect(screen.queryByRole("button", { name: "Submitting…" })).not.toBeInTheDocument());
    expect(submits(calls)).toHaveLength(1);
  });

  it("shows server field errors next to the right inputs, including payment ones", async () => {
    backend({
      [`POST ${COMPLETION_PATH}`]: errorReply(422, "VALIDATION_FAILED", "One or more fields are invalid.", {
        fields: { workDone: "Describe the work from the server.", "payment.amount": "Amount from the server." },
      }),
    });
    await openForm();
    await userEvent.click(screen.getByRole("button", { name: "Record a payment" }));
    await userEvent.type(screen.getByLabelText("Amount paid (RM)"), "170.50");
    await userEvent.selectOptions(screen.getByLabelText("Payment method"), "cash");
    await userEvent.click(screen.getByRole("button", { name: "Submit completion" }));
    expect(await screen.findByText("Describe the work from the server.")).toBeInTheDocument();
    expect(screen.getByLabelText("Work done")).toHaveAccessibleDescription("Describe the work from the server.");
    expect(screen.getByLabelText("Amount paid (RM)")).toHaveAccessibleDescription("Amount from the server.");
  });

  it("checks the payment fields before sending", async () => {
    const calls = backend();
    await openForm();
    await userEvent.click(screen.getByRole("button", { name: "Record a payment" }));
    await userEvent.click(screen.getByRole("button", { name: "Submit completion" }));
    expect(await screen.findByText("Choose how the customer paid.")).toBeInTheDocument();
    expect(submits(calls)).toHaveLength(0);
  });

  it("keeps the input after a 503 so the technician can try again", async () => {
    backend({ [`POST ${COMPLETION_PATH}`]: errorReply(503, "STORAGE_UNAVAILABLE", "Storage is unavailable.") });
    await openForm("Replaced the capacitor");
    await userEvent.type(screen.getByLabelText("Extra charges (RM)"), "20");
    await userEvent.click(screen.getByRole("button", { name: "Submit completion" }));
    expect(await screen.findByText(/We could not save the completion/)).toBeInTheDocument();
    expect(screen.getByLabelText("Work done")).toHaveValue("Replaced the capacitor");
    expect(screen.getByLabelText("Extra charges (RM)")).toHaveValue("20");
    expect(screen.getByRole("button", { name: "Submit completion" })).toBeEnabled();
  });

  it("shows the result panel with the final amount and the customer's WhatsApp button", async () => {
    let done = false;
    backend({
      [`GET /orders/${ORDER_ID}`]: () => ({ status: 200, body: { order: order(done ? "job_done" : "in_progress"), events: [] } }),
      [`POST ${COMPLETION_PATH}`]: () => {
        done = true;
        return { status: 201, body: { completion: COMPLETION, order: order("job_done"), notification: customerNotification("queued") } };
      },
      [`GET ${COMPLETION_PATH}`]: { status: 200, body: { completion: COMPLETION } },
      "GET /notifications": () => ({ status: 200, body: { items: done ? [customerNotification("ready")] : [], total: done ? 1 : 0, page: 1, pageSize: 20 } }),
    });
    await openForm();
    await userEvent.click(screen.getByRole("button", { name: "Submit completion" }));
    expect(await screen.findByText("Job completed. Let the customer know on WhatsApp.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Work done")).not.toBeInTheDocument();
    expect(screen.getAllByText("RM 170.50").length).toBeGreaterThan(0);
    const links = await screen.findAllByRole("link", { name: "Send WhatsApp to Siti Customer" });
    expect(links[0]).toHaveAttribute("href", "https://wa.me/60123456789?text=Hi%20Siti");
  });
});
