import { act, fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { adminUser, errorReply, mockBackend, type MockHandler } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";

const meAdmin = { status: 200, body: { user: adminUser } };
const technicianRow = {
  userId: "33333333-3333-4333-8333-333333333333",
  name: "Tom Tech",
  email: "tom@example.com",
  phone: "60123456789",
  age: 30,
  roleCode: "technician",
  createdAt: "2026-11-03T10:00:00Z",
};
const page = (items: unknown[], total = items.length) => ({ status: 200, body: { items, total, page: 1, pageSize: 20 } });

// Registers the admin session plus extra handlers for a users-feature test.
function adminBackend(extra: Record<string, MockHandler>) {
  return mockBackend({ "GET /auth/me": meAdmin, ...extra });
}

describe("users list (mocked backend: fetch is stubbed, no real server)", () => {
  it("shows a loading state, then the rows", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    adminBackend({
      "GET /users": async () => {
        await gate;
        return page([technicianRow]);
      },
    });
    renderApp("/users");

    expect(await screen.findByText("Loading users...")).toBeInTheDocument();
    release();
    expect(await screen.findByRole("cell", { name: "tom@example.com" })).toBeInTheDocument();
    expect(screen.getByText("Page 1 of 1 (1 user)")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    adminBackend({ "GET /users": page([]) });
    renderApp("/users");

    expect(await screen.findByText("No users match your search.")).toBeInTheDocument();
  });

  it("shows a 500 at once with its correlation id, and a manual retry recovers", async () => {
    let attempts = 0;
    adminBackend({
      "GET /users": () =>
        ++attempts === 1 ? errorReply(500, "INTERNAL_ERROR", "Internal server error.", { correlationId: "req-7f3a" }) : page([technicianRow]),
    });
    const user = userEvent.setup();
    renderApp("/users");

    expect(await screen.findByText("We could not load users. Try again. Reference: req-7f3a")).toBeInTheDocument();
    expect(attempts).toBe(1);
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("cell", { name: "tom@example.com" })).toBeInTheDocument();
  });

  it("retries a 503 automatically and shows the rows without an error", async () => {
    let attempts = 0;
    adminBackend({
      "GET /users": () => (++attempts === 1 ? errorReply(503, "SERVICE_UNAVAILABLE", "Service temporarily unavailable.") : page([technicianRow])),
    });
    renderApp("/users");

    expect(await screen.findByRole("cell", { name: "tom@example.com" }, { timeout: 3000 })).toBeInTheDocument();
    expect(attempts).toBe(2);
    expect(screen.queryByText(/could not load users/)).not.toBeInTheDocument();
  });

  it("restores search, role, page, and page size from the URL into the request and the controls", async () => {
    const calls = adminBackend({ "GET /users": { status: 200, body: { items: [technicianRow], total: 120, page: 2, pageSize: 50 } } });
    renderApp("/users?search=tom&roleCode=technician&page=2&pageSize=50");

    expect(await screen.findByText("Page 2 of 3 (120 users)")).toBeInTheDocument();
    const first = calls.find((call) => call.path === "/users")!;
    expect(Object.fromEntries(first.query)).toEqual({ search: "tom", roleCode: "technician", page: "2", pageSize: "50" });
    expect(screen.getByLabelText("Search by name or email")).toHaveValue("tom");
    expect(screen.getByLabelText("Role")).toHaveValue("technician");
    expect(screen.getByLabelText("Rows per page")).toHaveValue("50");
  });

  it("writes filter changes to the URL and restores the previous filters on back", async () => {
    adminBackend({ "GET /users": { status: 200, body: { items: [technicianRow], total: 45, page: 1, pageSize: 20 } } });
    const user = userEvent.setup();
    const { router } = renderApp("/users");
    await screen.findByRole("cell", { name: "tom@example.com" });

    await user.selectOptions(screen.getByLabelText("Role"), "technician");
    await waitFor(() => expect(router.state.location.search).toBe("?roleCode=technician"));
    await user.type(screen.getByLabelText("Search by name or email"), "tom");
    await waitFor(() => expect(router.state.location.search).toBe("?search=tom&roleCode=technician"));

    await act(() => router.navigate(-1));
    expect(router.state.location.search).toBe("");
    await waitFor(() => expect(screen.getByLabelText("Search by name or email")).toHaveValue(""));
    expect(screen.getByLabelText("Role")).toHaveValue("");
  });

  it("labels an unknown role code in the table instead of failing the list", async () => {
    adminBackend({ "GET /users": page([{ ...technicianRow, roleCode: "auditor" }]) });
    renderApp("/users");

    expect(await screen.findByRole("cell", { name: "Unknown role (auditor)" })).toBeInTheDocument();
  });

  it("sends the debounced search and the role filter to the backend and resets to page 1", async () => {
    const calls = adminBackend({ "GET /users": page([technicianRow]) });
    const user = userEvent.setup();
    renderApp("/users");
    await screen.findByRole("cell", { name: "tom@example.com" });

    await user.type(screen.getByLabelText("Search by name or email"), "tom");
    await user.selectOptions(screen.getByLabelText("Role"), "technician");

    await waitFor(() => {
      const last = calls.filter((call) => call.path === "/users").at(-1)!;
      expect(last.query.get("search")).toBe("tom");
      expect(last.query.get("roleCode")).toBe("technician");
      expect(last.query.get("page")).toBe("1");
      expect(last.query.get("pageSize")).toBe("20");
    });
    const partial = calls.filter((call) => call.query.get("search") === "t" || call.query.get("search") === "to");
    expect(partial).toHaveLength(0);
  });

  it("offers no delete control anywhere on the list", async () => {
    adminBackend({ "GET /users": page([technicianRow]) });
    renderApp("/users");
    await screen.findByRole("cell", { name: "tom@example.com" });

    expect(screen.queryByRole("button", { name: /delete|remove/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /delete|remove/i })).not.toBeInTheDocument();
  });
});

describe("create user form (mocked backend: fetch is stubbed, no real server)", () => {
  // Fills the required create fields for a manager so tests only vary what matters.
  async function fillManager(user: ReturnType<typeof userEvent.setup>) {
    await user.type(screen.getByLabelText("Name"), "Mia Manager");
    await user.type(screen.getByLabelText("Email"), "mia@example.com");
    await user.selectOptions(screen.getByLabelText("Role"), "manager");
    await user.type(screen.getByLabelText("Password"), "a long enough secret");
  }

  it("creates a user, sends the payload, and returns to the list with a confirmation", async () => {
    const calls = adminBackend({
      "POST /users": { status: 201, body: { ...technicianRow, name: "Mia Manager", roleCode: "manager" } },
      "GET /users": page([]),
    });
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await fillManager(user);
    await user.click(screen.getByRole("button", { name: "Create user" }));

    expect(await screen.findByText("User created.")).toBeInTheDocument();
    const post = calls.find((call) => call.method === "POST" && call.path === "/users")!;
    expect(post.body).toEqual({ name: "Mia Manager", email: "mia@example.com", roleCode: "manager", password: "a long enough secret" });
  });

  it("sends one POST when the form is submitted twice before the first request settles", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    const calls = adminBackend({
      "POST /users": async () => {
        await gate;
        return { status: 201, body: { ...technicianRow, name: "Mia Manager", roleCode: "manager" } };
      },
      "GET /users": page([]),
    });
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await fillManager(user);
    const form = (screen.getByRole("button", { name: "Create user" }) as HTMLButtonElement).form!;

    fireEvent.submit(form);
    fireEvent.submit(form);
    await screen.findByRole("button", { name: "Creating..." });
    fireEvent.submit(form);
    release();

    expect(await screen.findByText("User created.")).toBeInTheDocument();
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
  });

  it("does not retry a failed create and shows the correlation id of a 500", async () => {
    const calls = adminBackend({ "POST /users": errorReply(500, "INTERNAL_ERROR", "Internal server error.", { correlationId: "req-create-9" }) });
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await fillManager(user);
    await user.click(screen.getByRole("button", { name: "Create user" }));

    expect(await screen.findByText("We could not save the user. Please try again. Reference: req-create-9")).toBeInTheDocument();
    expect(calls.filter((call) => call.method === "POST")).toHaveLength(1);
    expect(screen.getByLabelText("Name")).toHaveValue("Mia Manager");
  });

  it("shows EMAIL_TAKEN next to the email field and keeps the other input", async () => {
    adminBackend({ "POST /users": errorReply(409, "EMAIL_TAKEN", "A user with this email already exists.") });
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await fillManager(user);
    await user.click(screen.getByRole("button", { name: "Create user" }));

    await waitFor(() => expect(screen.getByLabelText("Email")).toHaveAccessibleDescription("A user with this email already exists."));
    expect(screen.getByLabelText("Name")).toHaveValue("Mia Manager");
    expect(screen.getByLabelText("Name")).not.toHaveAttribute("aria-invalid");
  });

  it("maps 422 field errors, including a password reason code, onto their fields", async () => {
    adminBackend({
      "POST /users": errorReply(422, "VALIDATION_FAILED", "One or more fields are invalid.", {
        fields: { phone: "Phone must be 8 to 15 digits.", age: "Age must be between 16 and 100.", password: "too_common" },
      }),
    });
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await fillManager(user);
    await user.click(screen.getByRole("button", { name: "Create user" }));

    await waitFor(() => expect(screen.getByLabelText("Phone")).toHaveAccessibleDescription(expect.stringContaining("Phone must be 8 to 15 digits.")));
    expect(screen.getByLabelText("Age")).toHaveAccessibleDescription(expect.stringContaining("Age must be between 16 and 100."));
    expect(screen.getByLabelText("Password")).toHaveAccessibleDescription(expect.stringContaining("too common"));
    expect(screen.getByLabelText("Name")).not.toHaveAttribute("aria-invalid");
  });

  it("requires a phone for a technician and validates its format without calling the server", async () => {
    const calls = adminBackend({});
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await user.type(screen.getByLabelText("Name"), "Tom Tech");
    await user.type(screen.getByLabelText("Email"), "tom@example.com");
    await user.type(screen.getByLabelText("Password"), "a long enough secret");
    await user.click(screen.getByRole("button", { name: "Create user" }));

    expect(await screen.findByText("Phone is required for a technician.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Phone"), "12-34");
    await user.click(screen.getByRole("button", { name: "Create user" }));
    expect(await screen.findByText("Phone must be 8 to 15 digits.")).toBeInTheDocument();
    expect(calls.some((call) => call.method === "POST")).toBe(false);
  });

  it("accepts a phone with a plus, spaces, and dashes and validates the age range", async () => {
    const calls = adminBackend({ "POST /users": { status: 201, body: technicianRow }, "GET /users": page([]) });
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    await user.type(screen.getByLabelText("Name"), "Tom Tech");
    await user.type(screen.getByLabelText("Email"), "tom@example.com");
    await user.type(screen.getByLabelText("Phone"), "+60 12-345 6789");
    await user.type(screen.getByLabelText("Age"), "15");
    await user.type(screen.getByLabelText("Password"), "a long enough secret");
    await user.click(screen.getByRole("button", { name: "Create user" }));
    expect(await screen.findByText("Age must be between 16 and 100.")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Age"));
    await user.type(screen.getByLabelText("Age"), "16");
    await user.click(screen.getByRole("button", { name: "Create user" }));
    await screen.findByText("User created.");
    expect(calls.find((call) => call.method === "POST")!.body).toMatchObject({ phone: "+60 12-345 6789", age: 16, roleCode: "technician" });
  });

  it("fills a valid generated password into the visible field", async () => {
    adminBackend({});
    const user = userEvent.setup();
    renderApp("/users/new");
    await screen.findByRole("heading", { name: "New user" });
    const password = screen.getByLabelText("Password");

    await user.click(screen.getByRole("button", { name: "Generate password" }));

    expect((password as HTMLInputElement).value.length).toBeGreaterThanOrEqual(16);
    expect(password).toHaveAttribute("type", "text");
    expect(password).not.toHaveAttribute("aria-invalid", "true");
  });
});

describe("edit user form (mocked backend: fetch is stubbed, no real server)", () => {
  const editPath = `/users/${technicianRow.userId}/edit`;

  it("shows editable details only: no email, no password, no delete", async () => {
    adminBackend({ [`GET /users/${technicianRow.userId}`]: { status: 200, body: technicianRow } });
    renderApp(editPath);

    expect(await screen.findByLabelText("Name")).toHaveValue("Tom Tech");
    expect(screen.getByLabelText("Phone")).toHaveValue("60123456789");
    expect(screen.getByLabelText("Role")).toHaveValue("technician");
    expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
    expect(screen.queryByText("tom@example.com")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete|remove/i })).not.toBeInTheDocument();
  });

  it("omits an unchanged role from the PATCH and returns to the list", async () => {
    const calls = adminBackend({
      [`GET /users/${technicianRow.userId}`]: { status: 200, body: technicianRow },
      [`PATCH /users/${technicianRow.userId}`]: { status: 200, body: { ...technicianRow, name: "Tom T" } },
      "GET /users": page([technicianRow]),
    });
    const user = userEvent.setup();
    renderApp(editPath);
    const name = await screen.findByLabelText("Name");
    await user.clear(name);
    await user.type(name, "Tom T");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("User updated.")).toBeInTheDocument();
    const patch = calls.find((call) => call.method === "PATCH")!;
    expect(patch.body).toEqual({ name: "Tom T", phone: "60123456789", age: 30 });
  });

  it("shows the SELF_DEMOTE message next to the role select", async () => {
    const self = { ...technicianRow, userId: adminUser.userId, roleCode: "admin" };
    adminBackend({
      [`GET /users/${self.userId}`]: { status: 200, body: self },
      [`PATCH /users/${self.userId}`]: errorReply(409, "SELF_DEMOTE", "You cannot change your own role."),
    });
    const user = userEvent.setup();
    renderApp(`/users/${self.userId}/edit`);
    await user.selectOptions(await screen.findByLabelText("Role"), "manager");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(screen.getByLabelText("Role")).toHaveAccessibleDescription("You cannot change your own role."));
    expect(within(screen.getByLabelText("Role")).getAllByRole("option")).toHaveLength(3);
  });
});
