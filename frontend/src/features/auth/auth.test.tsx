import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { adminUser, errorReply, mockBackend, technicianUser } from "@/test-support/mock-backend";
import { renderApp } from "@/test-support/render-app";

const notAuthenticated = errorReply(401, "NOT_AUTHENTICATED", "Not authenticated.");

describe("auth screens (mocked backend: fetch is stubbed, no real server)", () => {
  it("shows validation messages for an empty and a malformed login", async () => {
    mockBackend({ "GET /auth/me": notAuthenticated });
    const user = userEvent.setup();
    renderApp("/login");

    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Enter your email.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();

    await user.type(screen.getByLabelText("Email"), "not-an-email");
    await user.type(screen.getByLabelText("Password"), "x");
    await user.click(screen.getByRole("button", { name: "Log in" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
  });

  it("disables submit while pending and exposes autocomplete hints", async () => {
    let release: () => void = () => {};
    const gate = new Promise<void>((resolve) => (release = resolve));
    mockBackend({
      "POST /auth/login": async () => {
        await gate;
        return { status: 200, body: { user: adminUser } };
      },
      "GET /auth/me": { status: 200, body: { user: adminUser } },
      "GET /users": { status: 200, body: { items: [], total: 0, page: 1, pageSize: 20 } },
    });
    const user = userEvent.setup();
    renderApp("/login");

    expect(screen.getByLabelText("Email")).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    const pending = await screen.findByRole("button", { name: "Signing in..." });
    expect(pending).toBeDisabled();
    release();
    expect(await screen.findByRole("heading", { name: "Orders" })).toBeInTheDocument();
  });

  it("keeps the typed input and shows one generic message after a 401", async () => {
    mockBackend({
      "GET /auth/me": notAuthenticated,
      "POST /auth/login": errorReply(401, "INVALID_CREDENTIALS", "Invalid email or password."),
    });
    const user = userEvent.setup();
    renderApp("/login");

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong password!");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    const alerts = await screen.findAllByText("Invalid email or password.");
    expect(alerts).toHaveLength(1);
    expect(screen.getByLabelText("Email")).toHaveValue("ada@example.com");
    expect(screen.getByLabelText("Password")).toHaveValue("wrong password!");
    expect(screen.getByRole("button", { name: "Log in" })).toBeEnabled();
  });

  it("shows the correlation id with the generic message when login answers 500", async () => {
    mockBackend({
      "GET /auth/me": notAuthenticated,
      "POST /auth/login": errorReply(500, "INTERNAL_ERROR", "Internal server error.", { correlationId: "req-login-42" }),
    });
    const user = userEvent.setup();
    renderApp("/login");

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct horse battery");
    await user.click(screen.getByRole("button", { name: "Log in" }));

    expect(await screen.findByText("We could not sign you in right now. Please try again. Reference: req-login-42")).toBeInTheDocument();
  });

  it("redirects to /login when a protected request answers 401", async () => {
    mockBackend({
      "GET /auth/me": { status: 200, body: { user: adminUser } },
      "GET /users": notAuthenticated,
    });
    renderApp("/users");

    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("redirects a logged-out visitor from a protected route to /login", async () => {
    mockBackend({ "GET /auth/me": notAuthenticated });
    renderApp("/users");

    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
  });

  it("shows the not-allowed page and no Users navigation for a technician on an admin URL", async () => {
    mockBackend({ "GET /auth/me": { status: 200, body: { user: technicianUser } } });
    renderApp("/users");

    expect(await screen.findByRole("heading", { name: "Not allowed" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Users" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "My jobs" })).toBeInTheDocument();
  });

  it("sends a technician home to My jobs and logs out back to /login", async () => {
    const calls = mockBackend({
      "GET /auth/me": { status: 200, body: { user: technicianUser } },
      "POST /auth/logout": { status: 204 },
    });
    const user = userEvent.setup();
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "My jobs" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Log out" }));
    expect(await screen.findByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(calls.some((call) => call.method === "POST" && call.path === "/auth/logout")).toBe(true);
  });

  it("shows the generic success message after a password reset", async () => {
    const message = "If the account exists, the password was updated.";
    const calls = mockBackend({ "POST /auth/password/reset": { status: 200, body: { message } } });
    const user = userEvent.setup();
    renderApp("/reset-password");

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("New password"), "a long enough secret");
    await user.click(screen.getByRole("button", { name: "Reset password" }));

    expect(await screen.findByText(message)).toBeInTheDocument();
    expect(calls[0].body).toEqual({ email: "ada@example.com", newPassword: "a long enough secret" });
    expect(screen.getByRole("link", { name: "Back to log in" })).toHaveAttribute("href", "/login");
  });

  it("shows the weak-password message from a 422 and the client length rule", async () => {
    mockBackend({
      "POST /auth/password/reset": errorReply(422, "WEAK_PASSWORD", "Choose a stronger password.", { fields: { newPassword: "too_common" } }),
    });
    const user = userEvent.setup();
    renderApp("/reset-password");

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("New password"), "short");
    await user.click(screen.getByRole("button", { name: "Reset password" }));
    expect(await screen.findByText("Password must be at least 10 characters.")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("New password"));
    await user.type(screen.getByLabelText("New password"), "password123");
    await user.click(screen.getByRole("button", { name: "Reset password" }));
    await waitFor(() => expect(screen.getByText("That password is too common. Choose a less guessable one.")).toBeInTheDocument());
  });
});
