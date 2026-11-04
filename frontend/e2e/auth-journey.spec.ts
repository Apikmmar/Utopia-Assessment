import { expect, test, type Page, type Route } from "@playwright/test";

type MockUser = { userId: string; name: string; email: string; phone: string | null; age: number | null; roleCode: string; createdAt: string };

const ADMIN: MockUser = {
  userId: "11111111-1111-4111-8111-111111111111",
  name: "Ada Admin",
  email: "ada@example.com",
  phone: null,
  age: null,
  roleCode: "admin",
  createdAt: "2026-11-01T08:00:00Z",
};

// Answers a route with a JSON body and status.
function json(route: Route, status: number, body: unknown) {
  return route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

// Answers a route with the backend's {detail, code} error body.
function fail(route: Route, status: number, code: string, detail: string) {
  return json(route, status, { detail, code });
}

// Mocks the whole backend in the browser with a tiny in-memory session and user store (no real server).
async function mockBackend(page: Page) {
  const users: MockUser[] = [ADMIN];
  const passwords: Record<string, string> = { [ADMIN.email]: "admin-secret-123" };
  let sessionEmail: string | null = null;

  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace(/^\/api/, "");
    const method = request.method();
    const current = users.find((candidate) => candidate.email === sessionEmail);
    const authUser = current && { userId: current.userId, name: current.name, email: current.email, roleCode: current.roleCode };
    const deny = () => fail(route, 401, "NOT_AUTHENTICATED", "Not authenticated.");

    if (method === "POST" && path === "/auth/login") {
      const body = request.postDataJSON() as { email: string; password: string };
      const match = users.find((candidate) => candidate.email === body.email);
      if (!match || passwords[body.email] !== body.password) {
        return fail(route, 401, "INVALID_CREDENTIALS", "Invalid email or password.");
      }
      sessionEmail = match.email;
      return json(route, 200, { user: { userId: match.userId, name: match.name, email: match.email, roleCode: match.roleCode } });
    }
    if (method === "GET" && path === "/auth/me") return authUser ? json(route, 200, { user: authUser }) : deny();
    if (method === "POST" && path === "/auth/logout") {
      sessionEmail = null;
      return route.fulfill({ status: 204 });
    }
    if (!authUser) return deny();
    if (path.startsWith("/users") && authUser.roleCode !== "admin") {
      return fail(route, 403, "FORBIDDEN", "You do not have access to this resource.");
    }
    if (method === "GET" && path === "/users") {
      return json(route, 200, { items: users, total: users.length, page: 1, pageSize: 20 });
    }
    if (method === "POST" && path === "/users") {
      const body = request.postDataJSON() as Omit<MockUser, "userId" | "createdAt"> & { password: string };
      const created: MockUser = {
        userId: `22222222-2222-4222-8222-${String(users.length).padStart(12, "0")}`,
        name: body.name,
        email: body.email,
        phone: body.phone ?? null,
        age: body.age ?? null,
        roleCode: body.roleCode,
        createdAt: "2026-11-04T09:00:00Z",
      };
      users.push(created);
      passwords[created.email] = body.password;
      return json(route, 201, created);
    }
    return fail(route, 404, "NOT_FOUND", "Not Found");
  });
}

test.describe("mocked-backend UI journey (page.route stands in for FastAPI; not a real-backend test)", () => {
  test("admin registers a technician, the technician logs in, is refused admin pages, and logs out", async ({ page }) => {
    await mockBackend(page);
    const technicianPassword = "technician-secret-1";

    await page.goto("/users");
    await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

    await page.getByLabel("Email").fill(ADMIN.email);
    await page.getByLabel("Password").fill("admin-secret-123");
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("heading", { name: "Users" })).toBeVisible();

    await page.getByRole("link", { name: "New user" }).click();
    await page.getByLabel("Name").fill("Tom Tech");
    await page.getByLabel("Email").fill("tom@example.com");
    await page.getByLabel("Phone").fill("+60 12-345 6789");
    await page.getByLabel("Password").fill(technicianPassword);
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByText("User created.")).toBeVisible();
    await expect(page.getByRole("cell", { name: "tom@example.com" })).toBeVisible();

    await page.getByLabel("Role").selectOption("technician");
    await expect(page).toHaveURL(/\?roleCode=technician$/);
    await page.reload();
    await expect(page.getByLabel("Role")).toHaveValue("technician");

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

    await page.getByLabel("Email").fill("tom@example.com");
    await page.getByLabel("Password").fill(technicianPassword);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(page.getByRole("heading", { name: "My jobs" })).toBeVisible();

    await page.goto("/users");
    await expect(page.getByRole("heading", { name: "Not allowed" })).toBeVisible();

    await page.getByRole("button", { name: "Log out" }).click();
    await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  });
});
