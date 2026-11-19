// The one place where the frontend talks to the backend.
//
// Every API call goes through apiFetch, so cross-cutting things are added here once:
// - the SHA-256 of the request body in x-amz-content-sha256 (ADR-0002, see sha256Hex)
// - B4: the sign-in token in X-Auth-Token (ADR-0003)
//
// Paths are relative ("/api/v1/..."). The browser sends them to the address the page
// came from: the Vite dev server locally, CloudFront in AWS. No backend address is
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

/**
 * The SHA-256 hash of a text, as 64 lowercase hex characters.
 *
 * Why: in AWS, CloudFront signs each API request before passing it to Lambda (OAC), and
 * Lambda only accepts a signed body if the request also carries the body's hash in
 * x-amz-content-sha256. CloudFront does not compute it, so the browser must. The hash
 * is taken over the exact text that is sent. It proves the body was not changed on the
 * way from CloudFront to Lambda; it is not a protection against the user.
 *
 * Locally the header is simply ignored by the backend.
 */
export async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
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

  // The body is turned into text once, so the hash is computed over exactly what is sent.
  const text = body === undefined ? undefined : JSON.stringify(body);
  const headers =
    text === undefined
      ? undefined
      : { "Content-Type": "application/json", "x-amz-content-sha256": await sha256Hex(text) };

  let response: Response;
  try {
    response = await fetch(`${API_PREFIX}${path}`, {
      method,
      headers,
      body: text,
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
