// The one place where the frontend talks to the backend.
//
// Every API call goes through apiFetch, so cross-cutting things are added here once,
// such as the sign-in token from B4 on (ADR-0003, revisited in B4 because of ADR-0007).
//
// Paths are relative ("/api/v1/..."). The browser sends them to the address the page
// came from: the Vite dev server locally, API Gateway in AWS (ADR-0007). No backend address is
// ever built into the frontend.

export const API_PREFIX = "/api/v1";

/** Every failed API call becomes one of these, so screens handle errors one way. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

interface ErrorBody {
  error: { code: string; message: string };
}

function isErrorBody(value: unknown): value is ErrorBody {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  // After the check above, TypeScript knows `value` has an `error` property.
  const error = value.error;
  return (
    typeof error === "object" &&
    error !== null &&
    typeof (error as { code?: unknown }).code === "string" &&
    typeof (error as { message?: unknown }).message === "string"
  );
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

export interface ApiOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

/**
 * Calls the API and returns the parsed JSON body.
 * Throws ApiError for an error response and for a network failure.
 */
export async function apiFetch<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ?? null,
    });
  } catch (cause) {
    // A cancelled request is not an error to report; let the caller see the abort.
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, "network_error", "Could not reach the server.");
  }

  if (response.status === 204) return undefined as T;

  const data = await readJson(response);

  if (!response.ok) {
    // The API always answers errors as { error: { code, message } } (SR-40). Anything
    // else (for example an HTML error page from a proxy) gets a generic message; its
    // content is never shown to the user.
    if (isErrorBody(data)) throw new ApiError(response.status, data.error.code, data.error.message);
    throw new ApiError(response.status, "unexpected_response", "Something went wrong.");
  }

  return data as T;
}
