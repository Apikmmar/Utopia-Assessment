import { expect, test, type Page } from "@playwright/test";

const PASSWORD = "correct-horse-battery-staple";
const TECH_EMAIL = "created.live@example.com";
const TECH_NAME = "Live Created Technician";
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=", "base64");
let orderId = "";
let orderNo = "";

// Signs in through the actual browser form and waits for the role's home page.
async function login(page: Page, email: string, heading: string, password = PASSWORD) {
  await page.goto("/login");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
}

// Logs out through the real mutation and checks the login screen.
async function logout(page: Page) {
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Log in", exact: true })).toBeVisible();
}

// Asserts that the current layout fits the selected viewport without sideways scrolling.
async function fits(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0);
}

test.describe.serial("real non-AI browser flows with PostgreSQL and Supabase", () => {
  test("admin manages users, creates/edits an order, assigns and reassigns it", async ({ page }) => {
    await login(page, "admin.live@example.com", "Orders");
    await page.getByRole("link", { name: "Users", exact: true }).click();
    await page.getByRole("link", { name: "New user", exact: true }).click();
    await page.getByLabel("Name", { exact: true }).fill("Created Technician");
    await page.getByLabel("Email", { exact: true }).fill(TECH_EMAIL);
    await page.getByLabel("Phone", { exact: true }).fill("+60 12-345 6789");
    await page.getByLabel("Age", { exact: true }).fill("30");
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Create user", exact: true }).click();
    await expect(page.getByText("User created.", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Edit Created Technician", exact: true }).click();
    await page.getByLabel("Name", { exact: true }).fill(TECH_NAME);
    await page.getByLabel("Role", { exact: true }).selectOption("manager");
    await page.getByRole("button", { name: "Save changes", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Users", exact: true })).toBeVisible();
    await page.getByRole("link", { name: `Edit ${TECH_NAME}`, exact: true }).click();
    await page.getByLabel("Role", { exact: true }).selectOption("technician");
    await page.getByRole("button", { name: "Save changes", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Users", exact: true })).toBeVisible();
    await page.getByLabel("Search by name or email").fill("created.live");
    await expect(page.getByRole("cell", { name: TECH_EMAIL, exact: true })).toBeVisible();
    await page.getByLabel("Role", { exact: true }).selectOption("technician");
    await page.reload();
    await expect(page.getByLabel("Role", { exact: true })).toHaveValue("technician");
    await page.getByRole("link", { name: "Orders", exact: true }).click();
    await page.getByRole("link", { name: "New order", exact: true }).click();
    await page.getByLabel("Customer name", { exact: true }).fill("Live Synthetic Customer");
    await page.getByLabel("Customer phone", { exact: true }).fill("012-345 6789");
    await page.getByLabel("Service address", { exact: true }).fill("Synthetic address for end-to-end verification");
    await page.getByLabel("Problem description", { exact: true }).fill("Air conditioner needs cleaning");
    await page.getByLabel("Service type", { exact: true }).selectOption({ label: "Repair" });
    await page.getByLabel("Quoted price (RM)", { exact: true }).fill("150.00");
    await page.getByLabel("Job instructions (optional)", { exact: true }).fill("Synthetic job instructions");
    await page.getByRole("button", { name: "Create order", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(/^ORD-/);
    orderNo = (await page.getByRole("heading", { level: 1 }).innerText()).trim();
    orderId = new URL(page.url()).pathname.split("/").pop()!;
    await page.getByRole("link", { name: "Edit details", exact: true }).click();
    await page.getByLabel("Customer name", { exact: true }).fill("Live Edited Customer");
    await page.getByRole("button", { name: "Save changes", exact: true }).click();
    await expect(page.getByText("Live Edited Customer", { exact: true })).toBeVisible();
    await page.getByLabel("Assign a technician", { exact: true }).selectOption({ label: "Other Technician" });
    await page.getByRole("button", { name: "Assign", exact: true }).click();
    await expect(page.getByLabel("Change technician", { exact: true })).toBeVisible();
    await page.getByLabel("Change technician", { exact: true }).selectOption({ label: TECH_NAME });
    await page.getByRole("button", { name: "Reassign", exact: true }).click();
    await expect(page.getByRole("link", { name: `Send WhatsApp to ${TECH_NAME}`, exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Orders", exact: true }).click();
    await page.getByLabel("Search by order number or customer").fill(orderNo);
    await page.getByLabel("Status", { exact: true }).selectOption("assigned");
    await expect(page.getByRole("link", { name: orderNo, exact: true })).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Status", { exact: true })).toHaveValue("assigned");
    await logout(page);
    await login(page, "other.live@example.com", "My jobs");
    await expect(page.getByText("No active jobs right now.", { exact: true })).toBeVisible();
    await page.goto(`/jobs/${orderId}`);
    await expect(page.getByText("This job is not assigned to you.", { exact: true })).toBeVisible();
    await logout(page);
  });

  test("technician completes a mobile visit with real uploads, payment, and WhatsApp tracking", async ({ page, context }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await login(page, TECH_EMAIL, "My jobs");
    await page.goto("/users");
    await expect(page.getByRole("heading", { name: "Not allowed", exact: true })).toBeVisible();
    await page.goto(`/jobs/${orderId}`);
    await expect(page.getByRole("link", { name: /^Call / })).toBeVisible();
    await expect(page.getByRole("link", { name: "Open in Maps", exact: true })).toBeVisible();
    await fits(page);
    await page.getByRole("button", { name: "Postpone visit", exact: true }).click();
    await page.getByLabel("Reason", { exact: true }).selectOption("parts_needed");
    await page.getByRole("button", { name: "Save postponement", exact: true }).click();
    await expect(page.getByText("Visit postponed. It is recorded in the order activity.", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Start job", exact: true }).click();
    await page.getByLabel("Work done", { exact: true }).fill("Cleaned and repaired the synthetic test unit");
    await page.getByLabel("Extra charges (RM)", { exact: true }).fill("20.50");
    await expect(page.getByTestId("final-amount-preview")).toContainText("170.50");
    await page.getByLabel("Remarks (optional)", { exact: true }).fill("Synthetic completion remarks");
    await page.getByLabel("Photos, videos, or PDFs", { exact: true }).setInputFiles({ name: "job-photo.png", mimeType: "image/png", buffer: PNG });
    const files = page.getByRole("list", { name: "Photos, videos, or PDFs files", exact: true });
    await expect(files.getByText("Uploaded", { exact: true })).toBeVisible();
    await files.getByRole("button", { name: "Remove job-photo.png", exact: true }).click();
    await expect(files).toHaveCount(0);
    await page.getByLabel("Photos, videos, or PDFs", { exact: true }).setInputFiles({ name: "job-photo.png", mimeType: "image/png", buffer: PNG });
    await expect(files.getByText("Uploaded", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Record a payment", exact: true }).click();
    await page.getByLabel("Amount paid (RM)", { exact: true }).fill("170.50");
    await page.getByLabel("Payment method", { exact: true }).selectOption("cash");
    await page.getByLabel("Receipt (optional)", { exact: true }).setInputFiles({ name: "receipt.png", mimeType: "image/png", buffer: PNG });
    await expect(page.getByRole("list", { name: "Receipt (optional) files", exact: true }).getByText("Uploaded", { exact: true })).toBeVisible();
    await fits(page);
    await page.getByRole("button", { name: "Submit completion", exact: true }).click();
    await expect(page.getByText("Job completed. Let the customer know on WhatsApp.", { exact: true })).toBeVisible();
    await expect(page.getByText("RM 170.50 by Cash, receipt attached", { exact: true })).toBeVisible();
    await context.route("https://wa.me/**", (route) => route.abort());
    const send = page.getByRole("link", { name: "Send WhatsApp to Live Edited Customer", exact: true }).first();
    await expect(send).toHaveAttribute("href", /^https:\/\/wa\.me\/60123456789\?text=/);
    const opened = page.waitForResponse((response) => /\/api\/notifications\/[^/]+\/open$/.test(response.url()) && response.status() === 200);
    const popup = page.waitForEvent("popup");
    await send.click();
    await opened;
    await (await popup).close();
    await page.getByRole("link", { name: /^Notifications/ }).click();
    await page.getByRole("tab", { name: "Sent", exact: true }).click();
    await expect(page.getByText("Opened in WhatsApp", { exact: true })).toBeVisible();
    await fits(page);
    await logout(page);
  });

  test("manager reviews files, closes the job, verifies KPI, and password reset works", async ({ page }) => {
    await login(page, "manager.live@example.com", "Review");
    await page.getByRole("link", { name: orderNo, exact: true }).click();
    await expect(page.getByText("Cleaned and repaired the synthetic test unit", { exact: true })).toBeVisible();
    await expect(page.getByText("Parts needed", { exact: false }).first()).toBeVisible();
    for (const name of ["job-photo.png", "receipt.png"]) {
      const image = page.getByRole("img", { name, exact: true });
      await expect(image).toBeVisible();
      await expect.poll(() => image.evaluate((element) => (element as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
    }
    await expect(page.getByRole("link", { name: "Edit details", exact: true })).toHaveCount(0);
    await page.getByRole("button", { name: "Mark reviewed", exact: true }).click();
    await page.getByRole("button", { name: "Close order", exact: true }).click();
    await expect(page.getByText("Closed", { exact: true }).first()).toBeVisible();
    await page.getByRole("link", { name: "Performance", exact: true }).click();
    await expect(page.getByText("RM 170.50", { exact: true }).first()).toBeVisible();
    const leaderboard = page.getByLabel("Technician leaderboard").locator("visible=true");
    await expect(leaderboard).toContainText(TECH_NAME);
    await expect(page.getByText(`${TECH_NAME} completed the most jobs: 1.`, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: /Previous/ }).click();
    await expect(page.getByText("No jobs were completed or postponed this week.", { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "This week", exact: true }).click();
    await expect(page.getByText("RM 170.50", { exact: true }).first()).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    await fits(page);
    await expect(page.getByLabel("Technician leaderboard").locator("visible=true")).toContainText(TECH_NAME);
    await page.getByRole("link", { name: "Notifications", exact: true }).click();
    await expect(page.getByRole("link", { name: /^Send WhatsApp/ })).toHaveCount(0);
    await logout(page);
    await page.getByRole("link", { name: "Forgot your password?", exact: true }).click();
    await page.getByLabel("Email", { exact: true }).fill(TECH_EMAIL);
    await page.getByLabel("New password", { exact: true }).fill("new-storage-test-password-123");
    await page.getByRole("button", { name: "Reset password", exact: true }).click();
    await expect(page.getByText("If the account exists, the password was updated.", { exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Back to log in", exact: true }).click();
    await page.getByLabel("Email", { exact: true }).fill(TECH_EMAIL);
    await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
    await page.getByRole("button", { name: "Log in", exact: true }).click();
    await expect(page.getByText("Invalid email or password.", { exact: true })).toBeVisible();
    await login(page, TECH_EMAIL, "My jobs", "new-storage-test-password-123");
    await expect(page.getByRole("list", { name: "Recently finished jobs", exact: true })).toContainText(orderNo);
    await logout(page);
  });
});
