import { vi } from "vitest";

export type MockReply = { status: number; body?: unknown };
export type MockCall = { method: string; path: string; query: URLSearchParams; body: unknown };
export type MockHandler = MockReply | ((call: MockCall) => MockReply | Promise<MockReply>);

export const adminUser = { userId: "11111111-1111-4111-8111-111111111111", name: "Ada Admin", email: "ada@example.com", roleCode: "admin" };
export const technicianUser = { userId: "22222222-2222-4222-8222-222222222222", name: "Tom Tech", email: "tom@example.com", roleCode: "technician" };

type ErrorExtras = { fields?: Record<string, string>; correlationId?: string };

// Builds an error reply in the backend's {detail, code, fields?, correlationId?} shape.
export function errorReply(status: number, code: string, detail: string, extras: ErrorExtras = {}): MockReply {
  return { status, body: { detail, code, ...extras } };
}

// Replaces global fetch with a mocked backend keyed by "METHOD /path" and returns the recorded calls.
export function mockBackend(handlers: Record<string, MockHandler>) {
  const calls: MockCall[] = [];
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const method = init?.method ?? "GET";
    const path = url.pathname.replace(/^\/api/, "");
    const call: MockCall = { method, path, query: url.searchParams, body: init?.body ? JSON.parse(String(init.body)) : undefined };
    calls.push(call);
    const handler = handlers[`${method} ${path}`];
    if (!handler) return new Response(JSON.stringify({ detail: `${method} ${path}`, code: "NOT_MOCKED" }), { status: 599 });
    const reply = typeof handler === "function" ? await handler(call) : handler;
    if (reply.status === 204) return new Response(null, { status: 204 });
    return new Response(JSON.stringify(reply.body ?? {}), { status: reply.status, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fetchMock);
  return calls;
}
