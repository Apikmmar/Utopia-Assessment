import { expect, test, type BrowserContext, type Page, type Route } from "@playwright/test";

type Role = "admin" | "technician" | "manager";
type Json = Record<string, unknown>;

const USERS: Record<Role, { userId: string; name: string; email: string; roleCode: Role }> = {
  admin: { userId: "11111111-1111-4111-8111-111111111111", name: "Ada Admin", email: "ada@example.com", roleCode: "admin" },
  technician: { userId: "22222222-2222-4222-8222-222222222222", name: "Tom Tech", email: "tom@example.com", roleCode: "technician" },
  manager: { userId: "44444444-4444-4444-8444-444444444444", name: "Max Manager", email: "max@example.com", roleCode: "manager" },
};
const ORDER_ID = "55555555-5555-4555-8555-555555555555";
const ORDER_NO = "ORD-000123";
const SERVICE_TYPE = { serviceTypeId: "77777777-7777-4777-8777-777777777777", code: "repair", name: "Repair" };
const TECHNICIAN_PHONE = "60111111111";
const PHONE_VIEWPORT = { width: 390, height: 844 };
const DESKTOP_VIEWPORT = { width: 1280, height: 800 };
const STORAGE_PREFIX = "/fake-storage/upload/";
const WORKER_DELAY_MS = 3000;
const NOW = "2026-11-04T07:45:00Z";
const JPEG_BYTES = Buffer.from([0xff, 0xd8, 0xff, 0xe0, ...new Array(60).fill(0)]);

// Answers a route with a JSON body and status.
function json(route: Route, status: number, body: unknown) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

// An in-memory stand-in for the FastAPI backend, storage, and worker, covering one order from creation to close.
// The worker is simulated by turning a queued notification ready a few seconds after it was queued.
class FakeBackend {
  role: Role = "admin";
  order: Json | null = null;
  events: Json[] = [];
  notifications: (Json & { queuedAt: number })[] = [];
  attachments: Json[] = [];
  completion: Json | null = null;
  uploads = 0;

  // Records one event on the timeline as the current user.
  event(eventType: string, fromStatus: string | null, toStatus: string | null) {
    this.events.push({ eventType, fromStatus, toStatus, actor: { userId: USERS[this.role].userId, name: USERS[this.role].name }, detail: {}, createdAt: NOW });
  }

  // Queues one WhatsApp notification the way the order and completion services do.
  queue(notificationType: string, recipientType: string, recipientName: string, recipientPhone: string, senderRole: Role | null) {
    const notification = {
      notificationId: `66666666-6666-4666-8666-00000000000${this.notifications.length + 1}`, orderId: ORDER_ID, orderNo: ORDER_NO,
      notificationType, channel: "whatsapp", recipientType, recipientName, recipientPhone, message: null, deepLink: null, status: "queued",
      readyAt: null, openedAt: null, openedBy: null, canSend: false, createdAt: NOW, queuedAt: Date.now(), senderRole,
    };
    this.notifications.push(notification);
    this.event("notification_queued", null, null);
    return this.present(notification);
  }

  // Returns a notification as the current user sees it: who may send it now, without the fake's own bookkeeping.
  present(notification: Json & { queuedAt: number }) {
    const { queuedAt: _queuedAt, senderRole, ...rest } = notification;
    const openable = rest.status === "ready" || rest.status === "opened";
    return { ...rest, canSend: openable && (this.role === "admin" || senderRole === this.role) };
  }

  // Lists notifications for the current user, letting the simulated worker finish any that waited long enough.
  listNotifications(query: URLSearchParams) {
    for (const notification of this.notifications) {
      if (notification.status === "queued" && Date.now() - notification.queuedAt >= WORKER_DELAY_MS) {
        Object.assign(notification, { status: "ready", readyAt: NOW, message: "Hi", deepLink: `https://wa.me/${notification.recipientPhone}?text=Hi` });
      }
    }
    const state = query.get("state");
    const visible = this.notifications.filter((item) => this.role !== "technician" || item.senderRole === "technician" || item.recipientType === "technician")
      .filter((item) => !state || (state === "sent" ? item.status === "opened" : item.status !== "opened"))
      .filter((item) => query.get("sendable") !== "true" || (item.status !== "opened" && (this.role === "admin" || item.senderRole === this.role)));
    return { items: visible.map((item) => this.present(item)), total: visible.length, page: 1, pageSize: 20 };
  }

  // Moves the order to a new status with its step timestamp and event.
  transition(toStatus: string, stamp: string) {
    const fromStatus = this.order!.status as string;
    Object.assign(this.order!, { status: toStatus, statusChangedAt: NOW, [stamp]: NOW });
    this.event(({ in_progress: "started", job_done: "completed", reviewed: "reviewed", closed: "closed" } as Json)[toStatus] as string, fromStatus, toStatus);
    return { order: this.order };
  }

  // Answers one API request from the browser.
  async handle(route: Route) {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api/, "");
    const method = request.method();
    const user = USERS[this.role];
    const key = `${method} ${path}`;
    if (key === "GET /auth/me") return json(route, 200, { user });
    if (key === "GET /service-types") return json(route, 200, { items: [SERVICE_TYPE] });
    if (key === "GET /users") {
      const technician = { ...USERS.technician, phone: TECHNICIAN_PHONE, age: null, createdAt: NOW };
      return json(route, 200, { items: [technician], total: 1, page: 1, pageSize: 100 });
    }
    if (key === "GET /notifications") return json(route, 200, this.listNotifications(url.searchParams));
    if (method === "POST" && path.startsWith("/notifications/") && path.endsWith("/open")) {
      const notification = this.notifications.find((item) => path.includes(item.notificationId as string))!;
      Object.assign(notification, { status: "opened", openedAt: NOW, openedBy: { userId: user.userId, name: user.name } });
      return json(route, 200, { notification: this.present(notification) });
    }
    if (key === "POST /orders") {
      const body = request.postDataJSON() as Json;
      this.order = {
        orderId: ORDER_ID, orderNo: ORDER_NO, customerName: body.customerName, customerPhone: "60123456789", address: body.address,
        problemDescription: body.problemDescription, serviceType: SERVICE_TYPE, quotedPrice: "150.00",
        technician: { userId: USERS.technician.userId, name: USERS.technician.name, phone: TECHNICIAN_PHONE }, adminNotes: body.adminNotes ?? null,
        status: "assigned", statusChangedAt: NOW, startedAt: null, jobDoneAt: null, reviewedAt: null, closedAt: null, createdAt: NOW,
      };
      this.event("created", null, "assigned");
      this.event("assigned", "new", "assigned");
      const notification = this.queue("job_assigned", "technician", USERS.technician.name, TECHNICIAN_PHONE, null);
      return json(route, 201, { order: this.order, notification });
    }
    if (key === "GET /orders") {
      const statuses = url.searchParams.getAll("status");
      const { customerPhone: _phone, problemDescription: _problem, adminNotes: _notes, ...item } = this.order ?? {};
      const items = this.order && (statuses.length === 0 || statuses.includes(this.order.status as string)) ? [{ ...item, technician: { userId: USERS.technician.userId, name: USERS.technician.name } }] : [];
      return json(route, 200, { items, total: items.length, page: 1, pageSize: 100 });
    }
    if (key === `GET /orders/${ORDER_ID}`) return json(route, 200, { order: this.order, events: this.events });
    if (key === `POST /orders/${ORDER_ID}/start`) return json(route, 200, this.transition("in_progress", "startedAt"));
    if (key === `POST /orders/${ORDER_ID}/review`) return json(route, 200, this.transition("reviewed", "reviewedAt"));
    if (key === `POST /orders/${ORDER_ID}/close`) return json(route, 200, this.transition("closed", "closedAt"));
    if (key === `POST /orders/${ORDER_ID}/attachments`) {
      const body = request.postDataJSON() as Json;
      this.uploads += 1;
      const attachment = { attachmentId: `88888888-8888-4888-8888-00000000000${this.uploads}`, kind: body.kind, fileName: body.fileName, contentType: body.contentType, sizeBytes: body.sizeBytes, status: "pending", viewUrl: null };
      this.attachments.push(attachment);
      return json(route, 201, { attachment, uploadUrl: `${url.origin}${STORAGE_PREFIX}${attachment.attachmentId}.jpg?token=t` });
    }
    if (key === `GET /orders/${ORDER_ID}/attachments`) {
      const items = this.attachments.filter((item) => item.status === "uploaded" || this.role === "technician");
      return json(route, 200, { items });
    }
    if (key === `POST /orders/${ORDER_ID}/completion`) {
      const body = request.postDataJSON() as Json;
      for (const attachment of this.attachments) {
        if ((body.attachmentIds as string[]).includes(attachment.attachmentId as string)) Object.assign(attachment, { status: "uploaded", viewUrl: `${url.origin}/fake-storage/view/photo.jpg` });
      }
      this.completion = {
        completionId: "99999999-9999-4999-8999-999999999999", orderId: ORDER_ID, technician: { userId: user.userId, name: user.name },
        workDone: body.workDone, quotedPrice: "150.00", extraCharges: "20.50", finalAmount: "170.50", remarks: body.remarks ?? null, payment: null, completedAt: NOW,
      };
      const { order } = this.transition("job_done", "jobDoneAt");
      const notification = this.queue("job_done", "customer", "Siti Customer", "60123456789", "technician");
      return json(route, 201, { completion: this.completion, order, notification });
    }
    if (key === `GET /orders/${ORDER_ID}/completion`) {
      return this.completion ? json(route, 200, { completion: this.completion }) : json(route, 404, { detail: "No completion.", code: "COMPLETION_NOT_FOUND" });
    }
    return json(route, 404, { detail: `Not mocked: ${key}`, code: "NOT_FOUND" });
  }

  // Routes the API, the direct storage upload, and WhatsApp popups for the whole browser context.
  async install(context: BrowserContext) {
    await context.route("**/api/**", (route) => this.handle(route));
    await context.route(`**${STORAGE_PREFIX}**`, (route) => route.fulfill({ status: 200, body: "" }));
    await context.route("**/fake-storage/view/**", (route) => route.fulfill({ status: 200, contentType: "image/jpeg", body: JPEG_BYTES }));
    await context.route("https://wa.me/**", (route) => route.fulfill({ status: 200, contentType: "text/html", body: "<title>WhatsApp</title>" }));
  }
}

// Fails when the page scrolls sideways at the current viewport.
async function expectNoHorizontalScroll(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(0);
}

// Clicks a WhatsApp link, which opens a new tab, and closes that tab again.
async function sendWhatsapp(page: Page, name: string) {
  const popup = page.waitForEvent("popup");
  await page.getByRole("link", { name }).first().click();
  await (await popup).close();
}

test("an order goes from creation to close (mocked backend, storage, and worker; page.route stands in for FastAPI)", async ({ page, context }) => {
  const backend = new FakeBackend();
  await backend.install(context);

  await test.step("admin creates and assigns the order and sees the technician WhatsApp button", async () => {
    backend.role = "admin";
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await page.goto("/orders/new");
    await page.getByLabel("Customer name").fill("Siti Customer");
    await page.getByLabel("Customer phone").fill("012-345 6789");
    await page.getByLabel("Service address").fill("No 1, Jalan Damai, KL");
    await page.getByLabel("Problem description").fill("Aircond leaking");
    await page.getByLabel("Service type").selectOption(SERVICE_TYPE.serviceTypeId);
    await page.getByLabel("Quoted price (RM)").fill("150");
    await page.getByLabel("Technician (optional)").selectOption(USERS.technician.userId);
    await page.getByRole("button", { name: "Create order" }).click();
    await expect(page.getByText(`Order ${ORDER_NO} created.`)).toBeVisible();
    await expect(page.getByRole("link", { name: "Send WhatsApp to Tom Tech" }).first()).toBeVisible({ timeout: 10_000 });
    await sendWhatsapp(page, "Send WhatsApp to Tom Tech");
  });

  await test.step("technician starts the job, uploads a photo, and completes it at phone width", async () => {
    backend.role = "technician";
    await page.setViewportSize(PHONE_VIEWPORT);
    await page.goto("/jobs");
    await page.getByRole("list", { name: "Active jobs" }).getByRole("link", { name: new RegExp(ORDER_NO) }).click();
    await page.getByRole("button", { name: "Start job" }).click();
    await page.getByLabel("Work done").fill("Cleaned the filter and topped up gas");
    await page.getByLabel("Extra charges (RM)").fill("20.50");
    await expect(page.getByTestId("final-amount-preview")).toHaveText("RM 170.50");
    await page.getByLabel("Photos, videos, or PDFs").setInputFiles({ name: "photo.jpg", mimeType: "image/jpeg", buffer: JPEG_BYTES });
    await expect(page.getByText("Uploaded", { exact: true })).toBeVisible();
    await expectNoHorizontalScroll(page);
    const submit = page.getByRole("button", { name: "Submit completion" });
    expect((await submit.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    await submit.click();
    await expect(page.getByText("Job completed. Let the customer know on WhatsApp.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Preparing WhatsApp message…" }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Send WhatsApp to Siti Customer" }).first()).toBeVisible({ timeout: 10_000 });
    await expectNoHorizontalScroll(page);
  });

  await test.step("technician sends the customer message from the Notifications page", async () => {
    await page.goto("/notifications");
    await expect(page.getByRole("list", { name: "Pending messages" })).toContainText("Siti Customer");
    await expectNoHorizontalScroll(page);
    await sendWhatsapp(page, "Send WhatsApp to Siti Customer");
    await page.getByRole("tab", { name: "Sent" }).click();
    await expect(page.getByRole("list", { name: "Sent messages" })).toContainText("Siti Customer");
  });

  await test.step("manager reviews and closes the order", async () => {
    backend.role = "manager";
    await page.setViewportSize(DESKTOP_VIEWPORT);
    await page.goto("/review");
    await page.getByRole("link", { name: ORDER_NO }).first().click();
    await expect(page.getByText("Cleaned the filter and topped up gas")).toBeVisible();
    await page.getByRole("button", { name: "Mark reviewed" }).click();
    await page.getByRole("button", { name: "Close order" }).click();
    await expect(page.getByText("Closed", { exact: true }).first()).toBeVisible();
    expect(backend.order!.status).toBe("closed");
  });
});
