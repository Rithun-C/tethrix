import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { App } from "./App";

function healthy() {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => Promise.resolve(new Response(JSON.stringify({ status: "ok" }), { status: 200 }))),
  );
}

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("App", () => {
  it("shows that the API is up", async () => {
    healthy();
    renderAt("/");

    expect(screen.getByRole("status")).toHaveTextContent("API: checking...");
    expect(await screen.findByText("API: ok")).toBeInTheDocument();
  });

  it("shows that the API is unreachable when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("Failed to fetch"))),
    );
    renderAt("/");

    expect(await screen.findByText("API: unreachable")).toBeInTheDocument();
  });

  it("shows that the API is unreachable when it answers with an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(new Response("bad gateway", { status: 502 }))),
    );
    renderAt("/");

    expect(await screen.findByText("API: unreachable")).toBeInTheDocument();
  });

  it("moves between pages through the menu", async () => {
    healthy();
    const user = userEvent.setup();
    renderAt("/");

    await user.click(screen.getByRole("link", { name: "Journal" }));

    expect(screen.getByRole("heading", { name: "Journal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Journal" })).toHaveClass("active");
  });

  it("shows the not-found page for an unknown address", () => {
    renderAt("/no-such-page");

    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Back to the dashboard" })).toHaveAttribute(
      "href",
      "/",
    );
  });
});
