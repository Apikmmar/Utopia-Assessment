import { apiRequest } from "@/lib/api-client";
import {
  userListSchema,
  userSchema,
  type CreateUserPayload,
  type UpdateUserPayload,
  type User,
  type UserList,
} from "./schemas";
import type { UserListFilters } from "./types";

// Fetches one page of users using the server-side search and role filter.
export async function listUsers(filters: UserListFilters, signal?: AbortSignal): Promise<UserList> {
  const body = await apiRequest("/users", { query: { ...filters, search: filters.search.trim() }, signal });
  return userListSchema.parse(body);
}

// Fetches one user by id.
export async function getUser(userId: string, signal?: AbortSignal): Promise<User> {
  return userSchema.parse(await apiRequest(`/users/${encodeURIComponent(userId)}`, { signal }));
}

// Creates a user and returns the stored record.
export async function createUser(payload: CreateUserPayload): Promise<User> {
  return userSchema.parse(await apiRequest("/users", { method: "POST", body: payload }));
}

// Updates a user's details or role and returns the stored record.
export async function updateUser(userId: string, payload: UpdateUserPayload): Promise<User> {
  return userSchema.parse(await apiRequest(`/users/${encodeURIComponent(userId)}`, { method: "PATCH", body: payload }));
}
