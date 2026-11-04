import { ApiError, apiRequest } from "@/lib/api-client";
import { messageSchema, sessionSchema, type AuthUser, type LoginValues, type ResetValues } from "./schemas";

// Fetches the current session user, or null when logged out.
export async function fetchMe(): Promise<AuthUser | null> {
  try {
    const body = await apiRequest("/auth/me", { skipUnauthorizedHandler: true });
    return sessionSchema.parse(body).user;
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

// Logs in with email and password and returns the session user.
export async function login(values: LoginValues): Promise<AuthUser> {
  const body = await apiRequest("/auth/login", { method: "POST", body: values, skipUnauthorizedHandler: true });
  return sessionSchema.parse(body).user;
}

// Ends the current session on the server.
export async function logout(): Promise<void> {
  await apiRequest<void>("/auth/logout", { method: "POST", skipUnauthorizedHandler: true });
}

// Resets a password and returns the server's generic confirmation message.
export async function resetPassword(values: ResetValues): Promise<string> {
  const body = await apiRequest("/auth/password/reset", { method: "POST", body: values, skipUnauthorizedHandler: true });
  return messageSchema.parse(body).message;
}
