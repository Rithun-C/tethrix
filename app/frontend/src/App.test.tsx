import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthProvider";
import { FakeAuth } from "./auth/fakeAuth";

/** Answers the API like the backend would for alice. */
function backend(overrides: Record<string, Response> = {}) {
  const fetchMock = vi.fn((url: string) => {
    if (url in overrides) return Promise.resolve(overrides[url]);
    if (url === "/api/v1/health") return Promise.resolve(Response.json({ status: "ok" }));
    if (url === "/api/v1/me") {
      return Promise.resolve(
        Response.json({ userId: "alice", timeZone: "Asia/Kolkata", createdAt: null }),
      );
    }
    return Promise.reject(new Error(`unexpected request ${url}`));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function renderAt(path: string, auth = new FakeAuth(), idleLimitMs?: number) {
  render(
    <AuthProvider service={auth} idleLimitMs={idleLimitMs}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </AuthProvider>,
  );
  return auth;
}

describe("App, signed in", () => {
  it("shows that the API is up and who is signed in", async () => {
    backend();
    renderAt("/");

    expect(await screen.findByText("API: ok")).toBeInTheDocument();
    expect(screen.getByText("alice@example.com")).toBeInTheDocument();
    expect(await screen.findByText("Your time zone: Asia/Kolkata")).toBeInTheDocument();
  });

  it("sends the access token with API calls", async () => {
    const fetchMock = backend();
    renderAt("/");
    await screen.findByText("Your time zone: Asia/Kolkata");

    const meCall = fetchMock.mock.calls.find(([url]) => url === "/api/v1/me") as unknown as [
      string,
      RequestInit,
    ];
    expect(meCall[1].headers).toEqual({ Authorization: "Bearer test-access-token" });
  });

  it("shows that the API is unreachable when it answers with an error", async () => {
    backend({ "/api/v1/health": new Response("bad gateway", { status: 502 }) });
    renderAt("/");

    expect(await screen.findByText("API: unreachable")).toBeInTheDocument();
  });

  it("moves between pages through the menu", async () => {
    backend();
    const user = userEvent.setup();
    renderAt("/");

    await user.click(await screen.findByRole("link", { name: "Journal" }));

    expect(screen.getByRole("heading", { name: "Journal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Journal" })).toHaveClass("active");
  });

  it("shows the not-found page for an unknown address", async () => {
    backend();
    renderAt("/no-such-page");

    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("signs out with the button", async () => {
    backend();
    const user = userEvent.setup();
    const auth = renderAt("/");

    await user.click(await screen.findByRole("button", { name: "Sign out" }));

    expect(auth.signOut).toHaveBeenCalledOnce();
    expect(screen.queryByText("alice@example.com")).not.toBeInTheDocument();
  });

  it("goes back to sign-in when the API answers 401", async () => {
    backend({
      "/api/v1/me": Response.json(
        { error: { code: "unauthorized", message: "x" } },
        { status: 401 },
      ),
    });
    const auth = renderAt("/");

    await vi.waitFor(() => {
      expect(auth.signIn).toHaveBeenCalledWith("/");
    });
    expect(auth.forget).toHaveBeenCalledOnce();
  });

  it("goes back to sign-in when the session ends by itself", async () => {
    backend();
    const auth = renderAt("/habits");
    await screen.findByRole("heading", { name: "Habits" });

    act(() => {
      auth.endSession();
    });

    expect(auth.signIn).toHaveBeenCalledWith("/habits");
    expect(screen.queryByRole("heading", { name: "Habits" })).not.toBeInTheDocument();
  });
});

describe("App, signed out", () => {
  it("sends the user to sign-in, remembering the page", async () => {
    backend();
    const auth = renderAt("/journal?day=2026-11-20", new FakeAuth(null));

    await vi.waitFor(() => {
      expect(auth.signIn).toHaveBeenCalledWith("/journal?day=2026-11-20");
    });
    expect(screen.queryByRole("heading", { name: "Journal" })).not.toBeInTheDocument();
  });

  it("shows a message when sign-in cannot start", async () => {
    backend();
    const auth = new FakeAuth(null);
    auth.init.mockRejectedValueOnce(new Error("down"));
    renderAt("/", auth);

    expect(
      await screen.findByRole("heading", { name: "Sign-in is not available" }),
    ).toBeInTheDocument();
  });
});

describe("Callback page", () => {
  it("finishes sign-in and goes to the page the user wanted", async () => {
    backend();
    const auth = new FakeAuth(null);
    auth.returnTo = "/habits";
    const original = window.location.pathname;
    window.history.replaceState(null, "", "/auth/callback?code=abc&state=xyz");
    renderAt("/auth/callback?code=abc&state=xyz", auth);

    expect(await screen.findByRole("heading", { name: "Habits" })).toBeInTheDocument();
    expect(auth.completeSignIn).toHaveBeenCalledOnce();
    expect(auth.init).not.toHaveBeenCalled();
    window.history.replaceState(null, "", original);
  });

  it("explains a failed sign-in", async () => {
    backend();
    const auth = new FakeAuth(null);
    auth.completeSignIn.mockRejectedValueOnce(new Error("No matching state"));
    window.history.replaceState(null, "", "/auth/callback?code=old");
    renderAt("/auth/callback?code=old", auth);

    expect(
      await screen.findByRole("heading", { name: "Sign-in did not finish" }),
    ).toBeInTheDocument();
    window.history.replaceState(null, "", "/");
  });
});

describe("Idle sign-out (SR-05)", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("signs out after the idle limit without activity", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    backend();
    const auth = renderAt("/", new FakeAuth(), 5 * 60 * 1000);
    await screen.findByText("alice@example.com");

    await act(async () => {
      await vi.advanceTimersByTimeAsync(6 * 60 * 1000);
    });

    expect(auth.signOut).toHaveBeenCalledOnce();
  });

  it("stays signed in while the user is active", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    backend();
    const auth = renderAt("/", new FakeAuth(), 5 * 60 * 1000);
    await screen.findByText("alice@example.com");

    for (let minute = 0; minute < 8; minute++) {
      await act(async () => {
        await vi.advanceTimersByTimeAsync(60 * 1000);
        window.dispatchEvent(new Event("keydown"));
      });
    }

    expect(auth.signOut).not.toHaveBeenCalled();
  });
});
