import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { errorReply, mockBackend, technicianUser, type MockCall, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";

const managerUser = { userId: "33333333-3333-4333-8333-333333333333", name: "Max Manager", email: "max@example.com", roleCode: "manager" };
const LAST_WEEK = { label: "26 Oct to 1 Nov 2026", startDate: "2026-10-26", endDate: "2026-11-01" };

const JOBS_ANSWER = {
  status: "answered",
  answer: "Ali completed 1 job last week: ORD-000123, Aircond cleaning.",
  summarySource: "ai",
  notice: null,
  period: LAST_WEEK,
  result: {
    kind: "technician_jobs",
    technician: { userId: "a1", name: "Ali" },
    total: 1,
    items: [{ orderId: "55555555-5555-4555-8555-555555555555", orderNo: "ORD-000123", serviceType: "Aircond cleaning", completedAt: "2026-10-30T03:00:00Z" }],
    truncated: false,
  },
};

// Registers the session user and the AI endpoint.
function backend(user: object, ai: MockHandler = { status: 200, body: JOBS_ANSWER }) {
  return mockBackend({
    "GET /auth/me": { status: 200, body: { user } },
    "GET /notifications": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } },
    "GET /orders": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } },
    "POST /ai/query": ai,
  });
}

// Returns the questions sent to the AI endpoint.
function questions(calls: MockCall[]) {
  return calls.filter((call) => call.path === "/ai/query").map((call) => (call.body as { question: string }).question);
}

describe("AI assistant (mocked backend: fetch is stubbed)", () => {
  it("fills an example, sends it once on a double click, and shows the answer with linked records", async () => {
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    const calls = backend(managerUser, async () => {
      await held;
      return { status: 200, body: JOBS_ANSWER };
    });
    renderApp("/ai");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "What jobs did technician Ali complete last week?" }));
    await user.dblClick(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Looking up the records…")).toBeInTheDocument();
    release();
    expect(await screen.findByText(JOBS_ANSWER.answer)).toBeInTheDocument();
    expect(screen.getByText("Period: 26 Oct to 1 Nov 2026")).toBeInTheDocument();
    expect(screen.getByText("Worded by AI from the records below.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "ORD-000123" })).toHaveAttribute("href", "/orders/55555555-5555-4555-8555-555555555555");
    expect(questions(calls)).toEqual(["What jobs did technician Ali complete last week?"]);
  });

  it("asks for a question before sending and shows guidance for an unsupported one", async () => {
    const guidance = { status: "unsupported", answer: "I can answer only these questions for now.", summarySource: null, notice: null, period: null, result: null };
    const calls = backend(managerUser, { status: 200, body: guidance });
    renderApp("/ai");
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Ask" }));
    expect(screen.getByText("Type a question or pick an example.")).toBeInTheDocument();
    expect(questions(calls)).toEqual([]);
    await user.type(screen.getByLabelText("Question"), "Tell me a joke");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(guidance.answer)).toBeInTheDocument();
    expect(screen.queryByText("Database records")).not.toBeInTheDocument();
  });

  it("shows the fallback notice and the template source when the AI summary failed", async () => {
    const fallback = { ...JOBS_ANSWER, summarySource: "template", notice: "AI summary unavailable. Showing database results." };
    backend(managerUser, { status: 200, body: fallback });
    renderApp("/ai");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Question"), "What jobs did Ali complete last week?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("AI summary unavailable. Showing database results.")).toBeInTheDocument();
    expect(screen.getByText("Written from the records below.")).toBeInTheDocument();
  });

  it("keeps the question and explains the daily limit", async () => {
    backend(managerUser, errorReply(429, "AI_USAGE_LIMIT", "The AI assistant reached today's limit of 50 answers."));
    renderApp("/ai");
    const user = userEvent.setup();
    await user.type(await screen.findByLabelText("Question"), "How many jobs were completed today?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("The AI assistant reached today's limit of 50 answers.")).toBeInTheDocument();
    expect(screen.getByLabelText("Question")).toHaveValue("How many jobs were completed today?");
  });

  it("is not offered to technicians", async () => {
    const calls = backend(technicianUser);
    renderApp("/ai");
    await waitFor(() => expect(screen.queryByText("Loading your session...")).not.toBeInTheDocument());
    expect(screen.queryByRole("link", { name: "AI assistant" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "AI assistant" })).not.toBeInTheDocument();
    expect(questions(calls)).toEqual([]);
  });
});
