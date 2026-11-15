import { ApiError, apiFetch } from "./client";

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFetch(result: Response | Error) {
  const mock = vi.fn(() =>
    result instanceof Error ? Promise.reject(result) : Promise.resolve(result),
  );
  vi.stubGlobal("fetch", mock);
  return mock;
}

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    if (error instanceof ApiError) return error;
    throw error;
  }
  throw new Error("expected the call to fail");
}

describe("apiFetch", () => {
  it("adds the API prefix and returns the parsed body", async () => {
    const fetchMock = mockFetch(jsonResponse(200, { status: "ok" }));

    const body = await apiFetch<{ status: string }>("/health");

    expect(body).toEqual({ status: "ok" });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("sends a body as JSON", async () => {
    const fetchMock = mockFetch(jsonResponse(201, { todoId: "t1" }));

    await apiFetch("/todos", { method: "POST", body: { title: "Water the plants" } });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/todos",
      expect.objectContaining({
        method: "POST",
        body: '{"title":"Water the plants"}',
        headers: { "Content-Type": "application/json" },
      }),
    );
  });

  it("turns the API's error format into an ApiError", async () => {
    mockFetch(jsonResponse(404, { error: { code: "not_found", message: "Not found." } }));

    const error = await failure(apiFetch("/todos/nope"));

    expect(error.status).toBe(404);
    expect(error.code).toBe("not_found");
    expect(error.message).toBe("Not found.");
  });

  it("does not show the content of an unexpected error response", async () => {
    mockFetch(new Response("<html>502 Bad Gateway: internal-host-7</html>", { status: 502 }));

    const error = await failure(apiFetch("/health"));

    expect(error.status).toBe(502);
    expect(error.code).toBe("unexpected_response");
    expect(error.message).toBe("Something went wrong.");
  });

  it("turns a network failure into an ApiError", async () => {
    mockFetch(new TypeError("Failed to fetch"));

    const error = await failure(apiFetch("/health"));

    expect(error.status).toBe(0);
    expect(error.code).toBe("network_error");
  });

  it("returns nothing for 204 No Content", async () => {
    mockFetch(new Response(null, { status: 204 }));

    await expect(apiFetch("/todos/t1", { method: "DELETE" })).resolves.toBeUndefined();
  });
});
