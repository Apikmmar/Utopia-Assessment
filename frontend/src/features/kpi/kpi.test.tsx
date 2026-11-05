import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { adminUser, errorReply, mockBackend, technicianUser, type MockCall, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";
import { readWeekDate, shiftWeek } from "./week";

const managerUser = { userId: "33333333-3333-4333-8333-333333333333", name: "Max Manager", email: "max@example.com", roleCode: "manager" };

// Builds one leaderboard row.
function row(rank: number, userId: string, name: string, jobsCompleted: number, totalAmount: string, postponed = 0) {
  return { rank, technician: { userId, name }, jobsCompleted, totalAmount, postponed };
}

const THIS_WEEK = {
  week: { label: "2 to 8 Nov 2026", startDate: "2026-11-02", endDate: "2026-11-08", isCurrent: true },
  team: { jobsCompleted: 5, totalAmount: "1250.50", postponed: 2 },
  leaderboard: [
    row(1, "a1", "Ali", 2, "500.00", 1),
    row(1, "b2", "Bala", 2, "500.00"),
    row(3, "c3", "Chong", 1, "250.50", 1),
    row(4, "d4", "Dev", 0, "0.00"),
  ],
};

const LAST_WEEK = {
  week: { label: "26 Oct to 1 Nov 2026", startDate: "2026-10-26", endDate: "2026-11-01", isCurrent: false },
  team: { jobsCompleted: 0, totalAmount: "0.00", postponed: 0 },
  leaderboard: [row(1, "a1", "Ali", 0, "0.00"), row(1, "b2", "Bala", 0, "0.00")],
};

// Answers the dashboard by the requested date: last week for 2026-10-26, a refusal for a future one, else this week.
function dashboard(call: MockCall) {
  const date = call.query.get("date");
  if (date === "2026-10-26") return { status: 200, body: LAST_WEEK };
  if (date === "2027-01-04") return errorReply(422, "INVALID_PERIOD", "Choose a week from 2020 up to this week.");
  return { status: 200, body: THIS_WEEK };
}

// Registers the session user and the dashboard.
function backend(user: object, handlers: Record<string, MockHandler> = {}) {
  return mockBackend({
    "GET /auth/me": { status: 200, body: { user } },
    "GET /notifications": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } },
    "GET /kpi/dashboard": dashboard,
    ...handlers,
  });
}

// Returns the dates the dashboard was requested with.
function dashboardDates(calls: MockCall[]) {
  return calls.filter((call) => call.path === "/kpi/dashboard").map((call) => call.query.get("date"));
}

describe("KPI dashboard (mocked backend: fetch is stubbed)", () => {
  it("shows the team cards, the leaderboard with shared ranks, and the chart table", async () => {
    backend(managerUser);
    renderApp("/kpi");
    expect(await screen.findByText("2 to 8 Nov 2026")).toBeInTheDocument();
    expect(screen.getByText("Jobs completed", { selector: "p" }).nextElementSibling).toHaveTextContent("5");
    expect(screen.getByText("Total amount", { selector: "p" }).nextElementSibling).toHaveTextContent("RM 1,250.50");
    expect(screen.getByText("Postponed", { selector: "p" }).nextElementSibling).toHaveTextContent("2");
    const table = screen.getByRole("table", { name: "Technician leaderboard" });
    const rows = within(table).getAllByRole("row").slice(1).map((item) => within(item).getAllByRole("cell").map((cell) => cell.textContent?.replace(/\s/g, " ")));
    expect(rows).toEqual([
      ["1 (tied)", "Ali", "2", "RM 500.00", "1"],
      ["1 (tied)", "Bala", "2", "RM 500.00", "0"],
      ["3", "Chong", "1", "RM 250.50", "1"],
      ["4", "Dev", "0", "RM 0.00", "0"],
    ]);
    expect(screen.getByText("Ali and Bala completed the most jobs: 2.")).toBeInTheDocument();
    const chartTable = screen.getByRole("table", { name: "Jobs completed per technician" });
    expect(within(chartTable).getAllByRole("row")).toHaveLength(5);
    expect(within(chartTable).getByRole("rowheader", { name: "Chong" }).nextElementSibling).toHaveTextContent("1");
  });

  it("keeps the week in the URL and disables next at the current week", async () => {
    const calls = backend(adminUser);
    const { router } = renderApp("/kpi");
    const next = await screen.findByRole("button", { name: "Next →" });
    expect(next).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "← Previous" }));
    expect(await screen.findByText("26 Oct to 1 Nov 2026")).toBeInTheDocument();
    expect(router.state.location.search).toBe("?date=2026-10-26");
    expect(screen.getByRole("button", { name: "Next →" })).toBeEnabled();
    expect(screen.getByText("No jobs were completed or postponed this week.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "This week" }));
    expect(await screen.findByText("2 to 8 Nov 2026")).toBeInTheDocument();
    expect(router.state.location.search).toBe("");
    expect(dashboardDates(calls)).toEqual([null, "2026-10-26", null]);
  });

  it("opens the week in the URL and falls back to this week when the server refuses it", async () => {
    backend(managerUser);
    const { router } = renderApp("/kpi?date=2027-01-04");
    expect(await screen.findByText("2 to 8 Nov 2026")).toBeInTheDocument();
    expect(router.state.location.search).toBe("");
  });

  it("rejects a response that does not match the schema", async () => {
    backend(managerUser, { "GET /kpi/dashboard": { status: 200, body: { ...THIS_WEEK, team: { jobsCompleted: 1, totalAmount: 12, postponed: 0 } } } });
    renderApp("/kpi");
    expect(await screen.findByText("We could not load the dashboard. Try again.", {}, { timeout: 5000 })).toBeInTheDocument();
  });

  it("shows the Performance entry only to admins and managers, and refuses technicians", async () => {
    backend(managerUser);
    const manager = renderApp("/kpi");
    expect(await screen.findByRole("link", { name: "Performance" })).toBeInTheDocument();
    manager.unmount();
    const calls = backend(technicianUser, { "GET /orders": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } } });
    renderApp("/kpi");
    await waitFor(() => expect(screen.queryByText("Loading your session...")).not.toBeInTheDocument());
    expect(screen.queryByRole("link", { name: "Performance" })).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Performance" })).not.toBeInTheDocument();
    expect(dashboardDates(calls)).toEqual([]);
  });

  it("reads only real dates from the URL and moves weeks across months", () => {
    expect(readWeekDate(new URLSearchParams("date=2026-11-04"))).toBe("2026-11-04");
    expect(readWeekDate(new URLSearchParams("date=2026-02-30"))).toBeUndefined();
    expect(readWeekDate(new URLSearchParams("date=last-week"))).toBeUndefined();
    expect(shiftWeek("2026-12-28", 1)).toBe("2027-01-04");
    expect(shiftWeek("2026-11-02", -1)).toBe("2026-10-26");
  });
});
