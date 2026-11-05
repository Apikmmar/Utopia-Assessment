import { expect, test, type Page, type Route } from "@playwright/test";

const MANAGER = { userId: "44444444-4444-4444-8444-444444444444", name: "Max Manager", email: "max@example.com", roleCode: "manager" };
const TECHNICIAN = { userId: "22222222-2222-4222-8222-222222222222", name: "Tom Tech", email: "tom@example.com", roleCode: "technician" };
const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const PHONE_VIEWPORT = { width: 390, height: 844 };
const DESKTOP_VIEWPORT = { width: 1280, height: 800 };
const MIN_TOUCH_TARGET_PX = 44;

// Builds one leaderboard row.
function row(rank: number, userId: string, name: string, jobsCompleted: number, totalAmount: string, postponed: number) {
  return { rank, technician: { userId, name }, jobsCompleted, totalAmount, postponed };
}

const WEEKS: Record<string, unknown> = {
  current: {
    week: { label: "2 to 8 Nov 2026", startDate: "2026-11-02", endDate: "2026-11-08", isCurrent: true },
    team: { jobsCompleted: 9, totalAmount: "2390.00", postponed: 2 },
    leaderboard: [
      row(1, "a1", "Ali", 4, "1100.00", 1),
      row(2, "b2", "Bala Subramaniam a/l Krishnan", 3, "760.00", 0),
      row(3, "c3", "Chong", 2, "530.00", 1),
      row(4, "d4", "Devi", 0, "0.00", 0),
    ],
  },
  "2026-10-26": {
    week: { label: "26 Oct to 1 Nov 2026", startDate: "2026-10-26", endDate: "2026-11-01", isCurrent: false },
    team: { jobsCompleted: 25, totalAmount: "6060.00", postponed: 6 },
    leaderboard: [
      row(1, "a1", "Ali", 10, "2260.00", 3),
      row(2, "b2", "Bala Subramaniam a/l Krishnan", 6, "1050.00", 2),
      row(3, "c3", "Chong", 5, "1670.00", 1),
      row(4, "d4", "Devi", 4, "1080.00", 0),
    ],
  },
};

const ORDER = {
  orderId: ORDER_ID, orderNo: "ORD-000123", customerName: "Siti Customer", customerPhone: "60123456789", address: "No 1, Jalan Damai, KL",
  problemDescription: "Aircond leaking", serviceType: { serviceTypeId: "77777777-7777-4777-8777-777777777777", code: "repair", name: "Repair" },
  quotedPrice: "150.00", technician: { userId: TECHNICIAN.userId, name: TECHNICIAN.name, phone: "60111111111" }, adminNotes: null, status: "assigned",
  statusChangedAt: "2026-11-04T07:00:00Z", startedAt: null, jobDoneAt: null, reviewedAt: null, closedAt: null, createdAt: "2026-11-04T07:00:00Z",
};

// Answers a route with a JSON body and status.
function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

// Mocks the backend for the given user (no real server): the dashboard by week, one assigned job, and postponing it.
async function mockBackend(page: Page, user: typeof MANAGER) {
  const events: unknown[] = [];
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^\/api/, "");
    const method = route.request().method();
    if (path === "/auth/me") return json(route, { user });
    if (path === "/notifications") return json(route, { items: [], total: 0, page: 1, pageSize: 20 });
    if (path === "/kpi/dashboard") {
      if (user.roleCode === "technician") return json(route, { detail: "Only admins and managers can view the KPI dashboard.", code: "FORBIDDEN" }, 403);
      return json(route, WEEKS[url.searchParams.get("date") ?? "current"] ?? WEEKS.current);
    }
    if (path === `/orders/${ORDER_ID}` && method === "GET") return json(route, { order: ORDER, events });
    if (path === `/orders/${ORDER_ID}/postpone` && method === "POST") {
      const body = route.request().postDataJSON() as { reasonCode: string; newDate?: string };
      events.push({
        eventType: "postponed", fromStatus: "assigned", toStatus: "assigned", actor: { userId: user.userId, name: user.name },
        detail: { reasonCode: body.reasonCode, newDate: body.newDate ?? null, technicianId: TECHNICIAN.userId }, createdAt: "2026-11-04T08:00:00Z",
      });
      return json(route, { order: ORDER });
    }
    return json(route, { detail: "Not Found", code: "NOT_FOUND" }, 404);
  });
}

// Fails when the page scrolls sideways at the current viewport.
async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

test.describe("KPI dashboard and postpone (mocked backend; page.route stands in for FastAPI)", () => {
  for (const viewport of [DESKTOP_VIEWPORT, PHONE_VIEWPORT]) {
    test(`a manager reads this week and last week at ${viewport.width} px`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await mockBackend(page, MANAGER);
      await page.goto("/kpi");
      await expect(page.getByRole("heading", { name: "Performance" })).toBeVisible();
      await expect(page.getByText("2 to 8 Nov 2026")).toBeVisible();
      await expect(page.getByText("RM 2,390.00").first()).toBeVisible();
      await expect(page.getByRole("button", { name: "Next →" })).toBeDisabled();
      await expect(page.getByText("Ali completed the most jobs: 4.")).toBeVisible();
      const leaderboard = page.getByLabel("Technician leaderboard").locator("visible=true");
      await expect(leaderboard).toHaveCount(1);
      await expect(leaderboard).toContainText("Bala Subramaniam a/l Krishnan");
      await expectNoHorizontalScroll(page);
      await page.getByRole("button", { name: "← Previous" }).click();
      await expect(page.getByText("26 Oct to 1 Nov 2026")).toBeVisible();
      await expect(page).toHaveURL(/\/kpi\?date=2026-10-26$/);
      await expect(page.getByText("RM 6,060.00").first()).toBeVisible();
      await expectNoHorizontalScroll(page);
      await page.getByRole("button", { name: "This week" }).click();
      await expect(page.getByText("2 to 8 Nov 2026")).toBeVisible();
    });
  }

  test("a technician postpones a visit at 390 px and cannot open the dashboard", async ({ page }) => {
    await page.setViewportSize(PHONE_VIEWPORT);
    await mockBackend(page, TECHNICIAN);
    await page.goto(`/jobs/${ORDER_ID}`);
    const open = page.getByRole("button", { name: "Postpone visit" });
    expect((await open.boundingBox())!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    await open.click();
    await page.getByLabel("Reason").selectOption("parts_needed");
    await page.getByRole("button", { name: "Save postponement" }).click();
    await expect(page.getByText("Visit postponed. It is recorded in the order activity.")).toBeVisible();
    await expectNoHorizontalScroll(page);
    await page.goto("/kpi");
    await expect(page.getByRole("link", { name: "Performance" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Performance" })).toHaveCount(0);
  });
});
