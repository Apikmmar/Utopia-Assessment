import { expect, test, type Page, type Route } from "@playwright/test";

const TECHNICIAN = { userId: "22222222-2222-4222-8222-222222222222", name: "Tom Tech", email: "tom@example.com", roleCode: "technician" };
const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const ORDER = {
  orderId: ORDER_ID,
  orderNo: "ORD-000123",
  customerName: "Siti Customer with a rather long name",
  customerPhone: "60123456789",
  address: "No 1, Jalan Damai 3/4, Taman Sri Kembangan Utama, 43300 Seri Kembangan, Selangor",
  problemDescription: "Aircond leaking water onto the floor near the bedroom door every afternoon.",
  serviceType: { serviceTypeId: "77777777-7777-4777-8777-777777777777", code: "repair", name: "Repair" },
  quotedPrice: "150.00",
  technician: { userId: TECHNICIAN.userId, name: TECHNICIAN.name, phone: "60111111111" },
  adminNotes: "Bring a ladder. Guard house needs the order number.",
  status: "assigned",
  statusChangedAt: "2026-11-04T07:00:00Z",
  startedAt: null,
  jobDoneAt: null,
  reviewedAt: null,
  closedAt: null,
  createdAt: "2026-11-04T07:00:00Z",
};
const NOTIFICATION = {
  notificationId: "66666666-6666-4666-8666-666666666666",
  orderId: ORDER_ID,
  orderNo: "ORD-000123",
  notificationType: "job_done",
  channel: "whatsapp",
  recipientType: "customer",
  recipientName: "Siti Customer",
  recipientPhone: "60123456789",
  message: "Hi Siti",
  deepLink: "https://wa.me/60123456789?text=Hi%20Siti",
  status: "ready",
  readyAt: "2026-11-04T07:45:00Z",
  openedAt: null,
  openedBy: null,
  canSend: true,
  createdAt: "2026-11-04T07:44:00Z",
};
const MIN_TOUCH_TARGET_PX = 44;

// Answers a route with a JSON body.
function json(route: Route, body: unknown) {
  return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
}

// Mocks the backend for a signed-in technician with one assigned job and one ready message (no real server).
async function mockBackend(page: Page) {
  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace(/^\/api/, "");
    if (path === "/auth/me") return json(route, { user: TECHNICIAN });
    if (path === "/orders") {
      const { customerPhone: _phone, problemDescription: _problem, adminNotes: _notes, ...item } = ORDER;
      return json(route, { items: [{ ...item, technician: { userId: TECHNICIAN.userId, name: TECHNICIAN.name } }], total: 1, page: 1, pageSize: 100 });
    }
    if (path === `/orders/${ORDER_ID}`) return json(route, { order: ORDER, events: [] });
    if (path === "/notifications") return json(route, { items: [NOTIFICATION], total: 1, page: 1, pageSize: 20 });
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Not Found", code: "NOT_FOUND" }) });
  });
}

// Fails when the page scrolls sideways at the current viewport.
async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

test.describe("technician screens at phone width (mocked backend; page.route stands in for FastAPI)", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("my jobs, the job page, and notifications fit 390 px with 44 px touch targets", async ({ page }) => {
    await mockBackend(page);

    await page.goto("/jobs");
    const card = page.getByRole("list", { name: "Active jobs" }).getByRole("link", { name: /ORD-000123/ });
    await expect(card).toBeVisible();
    await expectNoHorizontalScroll(page);
    expect((await card.boundingBox())!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    await card.click();
    const start = page.getByRole("button", { name: "Start job" });
    await expect(start).toBeVisible();
    await expectNoHorizontalScroll(page);
    const startBox = (await start.boundingBox())!;
    expect(startBox.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect(startBox.width).toBeGreaterThan(300);
    expect((await page.getByRole("link", { name: "Call 60123456789" }).boundingBox())!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);
    expect((await page.getByRole("link", { name: "Open in Maps" }).boundingBox())!.height).toBeGreaterThanOrEqual(MIN_TOUCH_TARGET_PX);

    await page.goto("/notifications");
    const send = page.getByRole("link", { name: "Send WhatsApp to Siti Customer" });
    await expect(send).toBeVisible();
    await expectNoHorizontalScroll(page);
    expect((await send.boundingBox())!.width).toBeGreaterThan(300);
  });
});
