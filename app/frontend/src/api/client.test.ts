import { ApiError, apiFetch, sha256Hex } from "./client";

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

describe("sha256Hex", () => {
  it("matches the standard test values", async () => {
    // Published test vectors for SHA-256 (empty text and "abc").
    expect(await sha256Hex("")).toBe(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    );
    expect(await sha256Hex("abc")).toBe(
      "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
    );
  });

  it("hashes the UTF-8 bytes, not the characters", async () => {
    // Computed with Python: hashlib.sha256("café".encode()).hexdigest()
    expect(await sha256Hex("café")).toBe(
      "850f7dc43910ff890f8879c0ed26fe697c93a067ad93a7d50f466a7028a9bf4e",
    );
  });
});

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

  it("sends a body as JSON, with the SHA-256 of that exact text", async () => {
    const fetchMock = mockFetch(jsonResponse(201, { todoId: "t1" }));

    await apiFetch("/todos", { method: "POST", body: { title: "Water the plants" } });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/todos",
      expect.objectContaining({
        method: "POST",
        body: '{"title":"Water the plants"}',
        headers: {
          "Content-Type": "application/json",
          // Computed with Python: hashlib.sha256(b'{"title":"Water the plants"}').hexdigest()
          "x-amz-content-sha256":
            "5d5b79effcfb11a89e224ed3d67f7c9b0e5bf988ce2cdcf3b30fdbb188cc86f8",
        },
      }),
    );
  });

  it("sends no body headers when there is no body", async () => {
    const fetchMock = mockFetch(jsonResponse(200, { status: "ok" }));

    await apiFetch("/health");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/health",
      expect.objectContaining({ headers: undefined, body: undefined }),
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
