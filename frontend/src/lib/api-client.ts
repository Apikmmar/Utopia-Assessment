export const API_BASE_PATH = "/api";

export const NETWORK_ERROR_CODE = "NETWORK_ERROR";

const NETWORK_ERROR_MESSAGE = "We could not reach the server. Check your connection and try again.";
const UNKNOWN_ERROR_MESSAGE = "Something went wrong. Please try again.";

export type ApiFields = Record<string, string>;

export class ApiError extends Error {
  status: number;
  code: string;
  fields: ApiFields;
  correlationId: string | null;

  // Builds a typed failure from the backend error body; status 0 means the request never got an answer.
  constructor(status: number, code: string, message: string, fields: ApiFields = {}, correlationId: string | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.correlationId = correlationId;
  }
}

export type RequestOptions = {
  method?: "GET" | "POST" | "PATCH";
  body?: unknown;
  query?: Record<string, string | number | readonly string[] | undefined>;
  signal?: AbortSignal;
  skipUnauthorizedHandler?: boolean;
};

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

// Registers the callback run when a protected request answers 401.
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  unauthorizedHandler = handler;
}

// Builds the request URL with only the query values that are set, repeating the key for each value of a list.
function buildUrl(path: string, query: RequestOptions["query"]) {
  const params = new URLSearchParams();
  Object.entries(query ?? {}).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((item: string) => params.append(key, item));
      return;
    }
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const queryString = params.toString();
  return `${API_BASE_PATH}${path}${queryString ? `?${queryString}` : ""}`;
}

// Keeps only the string entries of an untrusted fields map.
function readFields(value: unknown): ApiFields {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === "string"));
}

// Parses the backend error body {detail, code, fields?, correlationId?} into an ApiError, tolerating other bodies.
export function parseApiError(status: number, payload: unknown) {
  const body = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const code = typeof body.code === "string" && body.code ? body.code : `HTTP_${status}`;
  const message = typeof body.detail === "string" && body.detail ? body.detail : UNKNOWN_ERROR_MESSAGE;
  const correlationId = typeof body.correlationId === "string" && body.correlationId ? body.correlationId : null;
  return new ApiError(status, code, message, readFields(body.fields), correlationId);
}

// Converts a failed response into a typed ApiError, tolerating non-JSON bodies.
async function toApiError(response: Response) {
  const payload = await response.json().catch(() => null);
  return parseApiError(response.status, payload);
}

// Runs fetch and turns a transport failure into a status-0 ApiError, leaving cancellations untouched.
async function send(url: string, init: RequestInit) {
  try {
    return await fetch(url, init);
  } catch (error) {
    if (init.signal?.aborted) throw error;
    throw new ApiError(0, NETWORK_ERROR_CODE, NETWORK_ERROR_MESSAGE);
  }
}

// Sends one JSON request with the session cookie and returns the parsed body.
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const hasBody = options.body !== undefined;
  const response = await send(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    credentials: "include",
    signal: options.signal,
    headers: hasBody ? { "Content-Type": "application/json", Accept: "application/json" } : { Accept: "application/json" },
    body: hasBody ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    const error = await toApiError(response);
    if (response.status === 401 && !options.skipUnauthorizedHandler) unauthorizedHandler?.();
    throw error;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
