import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";

import { App } from "../App";
import type { Todo } from "../api/todos";
import { AuthProvider } from "../auth/AuthProvider";
import { FakeAuth } from "../auth/fakeAuth";

// The Todos page against a fake API that keeps its own list, like the real one.

const TODAY = "2026-11-22";

function todo(id: string, title: string, fields: Partial<Todo> = {}): Todo {
  return {
    todoId: id,
    title,
    notes: null,
    dueDate: null,
    priority: null,
    completed: false,
    completedAt: null,
    createdAt: "2026-11-22T06:00:00.000Z",
    updatedAt: "2026-11-22T06:00:00.000Z",
    ...fields,
  };
}

interface Deferred {
  release: () => void;
  gate: Promise<void>;
}

class FakeApi {
  todos: Todo[] = [];
  calls: { method: string; path: string; body?: unknown }[] = [];
  /** The next call with this method answers with this status instead. */
  failNext: Partial<Record<string, number>> = {};
  /** The next call with this method waits until released. */
  holdNext: Partial<Record<string, Deferred>> = {};
  pageSize = 50;
  nextId = 1;

  constructor() {
    vi.stubGlobal("fetch", (url: string, init: RequestInit = {}) => this.handle(url, init));
  }

  hold(method: string): Deferred {
    let release: () => void = () => undefined;
    const gate = new Promise<void>((resolve) => {
      release = resolve;
    });
    const deferred = { release, gate };
    this.holdNext[method] = deferred;
    return deferred;
  }

  private async handle(url: string, init: RequestInit): Promise<Response> {
    const method = init.method ?? "GET";
    const body = typeof init.body === "string" ? (JSON.parse(init.body) as unknown) : undefined;
    const [path = "", query = ""] = url.split("?");
    this.calls.push({ method, path, body });

    if (path === "/api/v1/health") return Response.json({ status: "ok" });
    if (path === "/api/v1/me") {
      return Response.json({ userId: "alice", timeZone: "Asia/Kolkata", createdAt: null });
    }

    const held = this.holdNext[method];
    if (held && path.startsWith("/api/v1/todos")) {
      this.holdNext[method] = undefined;
      await held.gate;
    }
    const status = this.failNext[method];
    if (status && path.startsWith("/api/v1/todos")) {
      this.failNext[method] = undefined;
      return Response.json(
        { error: { code: "x", message: `Refused with ${String(status)}.` } },
        { status },
      );
    }

    if (path === "/api/v1/todos" && method === "GET") return this.list(new URLSearchParams(query));
    if (path === "/api/v1/todos" && method === "POST") {
      const created = todo(
        `01JD${String(this.nextId++).padStart(22, "0")}`,
        "",
        body as Partial<Todo>,
      );
      this.todos.push(created);
      return Response.json(created, { status: 201 });
    }
    const id = path.replace("/api/v1/todos/", "");
    const found = this.todos.find((t) => t.todoId === id);
    if (!found)
      return Response.json(
        { error: { code: "not_found", message: "Not found." } },
        { status: 404 },
      );
    if (method === "GET") return Response.json(found);
    if (method === "PATCH") {
      const changes = body as Partial<Todo>;
      // Field by field, like the real API: only these can change.
      if (changes.title !== undefined) found.title = changes.title;
      if (changes.notes !== undefined) found.notes = changes.notes;
      if (changes.dueDate !== undefined) found.dueDate = changes.dueDate;
      if (changes.priority !== undefined) found.priority = changes.priority;
      if (changes.completed !== undefined) found.completed = changes.completed;
      if ("completed" in changes)
        found.completedAt = changes.completed ? "2026-11-22T07:00:00.000Z" : null;
      return Response.json(found);
    }
    this.todos = this.todos.filter((t) => t.todoId !== id);
    return new Response(null, { status: 204 });
  }

  private list(params: URLSearchParams): Response {
    const view = params.get("view");
    const open = this.todos.filter((t) => !t.completed);
    const items =
      view === "completed"
        ? this.todos.filter((t) => t.completed)
        : view === "today"
          ? open.filter((t) => t.dueDate !== null && t.dueDate <= TODAY)
          : view === "upcoming"
            ? open.filter((t) => t.dueDate !== null && t.dueDate > TODAY)
            : open;
    const start = Number(params.get("cursor") ?? 0);
    const page = items.slice(start, start + this.pageSize);
    const more = start + this.pageSize < items.length;
    return Response.json({
      items: page.map((t) => ({
        todoId: t.todoId,
        title: t.title,
        dueDate: t.dueDate,
        priority: t.priority,
        completed: t.completed,
        completedAt: t.completedAt,
      })),
      nextCursor: more ? String(start + this.pageSize) : null,
      today: TODAY,
    });
  }
}

function renderTodos(path = "/todos") {
  render(
    <AuthProvider service={new FakeAuth()}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </AuthProvider>,
  );
}

async function list() {
  return within(await screen.findByRole("list", { name: /todos$/ }));
}

describe("Todos page: views (US-13)", () => {
  it("opens on Today, with overdue todos marked in words", async () => {
    const api = new FakeApi();
    api.todos = [
      todo("01JD01", "Water the plants", { dueDate: "2026-11-20", priority: "high" }),
      todo("01JD02", "Call the bank", { dueDate: TODAY }),
      todo("01JD03", "Next week", { dueDate: "2026-11-29" }),
    ];
    renderTodos();

    const rows = await list();
    expect(rows.getAllByRole("listitem")).toHaveLength(2);
    const [first, second] = rows.getAllByRole("listitem") as [HTMLElement, HTMLElement];
    expect(within(first).getByText("Overdue")).toBeInTheDocument();
    expect(within(first).getByText("High")).toBeInTheDocument();
    expect(within(first).getByText("20 Nov")).toBeInTheDocument();
    expect(within(second).queryByText("Overdue")).toBeNull();
    expect(screen.getByRole("link", { name: "Today" })).toHaveAttribute("aria-current", "page");
  });

  it("moves between views with the tabs, each with its own address", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Someday"), todo("01JD02", "Done one", { completed: true })];
    const user = userEvent.setup();
    renderTodos();

    expect(await screen.findByText("Nothing due today or overdue.")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: "All" }));
    expect((await list()).getByText("Someday")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "All" })).toHaveAttribute("aria-current", "page");

    await user.click(screen.getByRole("link", { name: "Completed" }));
    expect((await list()).getByText("Done one")).toBeInTheDocument();
    expect(api.calls.filter((c) => c.method === "GET" && c.path === "/api/v1/todos")).toHaveLength(
      3,
    );
  });

  it("loads more when there are more than one page", async () => {
    const api = new FakeApi();
    api.pageSize = 2;
    api.todos = [todo("01JD01", "one"), todo("01JD02", "two"), todo("01JD03", "three")];
    const user = userEvent.setup();
    renderTodos("/todos?view=all");

    expect((await list()).getAllByRole("listitem")).toHaveLength(2);
    await user.click(screen.getByRole("button", { name: "Load more" }));

    expect((await list()).getByText("three")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  });

  it("explains a list that could not load, and tries again", async () => {
    const api = new FakeApi();
    api.failNext.GET = 503;
    api.todos = [todo("01JD01", "Back again")];
    const user = userEvent.setup();
    renderTodos("/todos?view=all");

    expect(await screen.findByRole("alert")).toHaveTextContent("Your todos could not be loaded");
    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect((await list()).getByText("Back again")).toBeInTheDocument();
  });
});

describe("Todos page: add (US-10)", () => {
  it("shows the new todo at once, before the server answers", async () => {
    const api = new FakeApi();
    const user = userEvent.setup();
    renderTodos("/todos?view=all");
    await screen.findByText("No open todos. Add one above.");

    const gate = api.hold("POST");
    await user.type(screen.getByLabelText("Add a todo"), "Buy milk");
    await user.click(screen.getByRole("button", { name: "Add" }));

    // Optimistic: on screen, but its controls wait for the server.
    const rows = await list();
    expect(rows.getByText("Buy milk")).toBeInTheDocument();
    expect(rows.getByRole("checkbox", { name: "Done: Buy milk" })).toBeDisabled();
    expect(screen.getByLabelText("Add a todo")).toHaveValue("");

    await act(async () => {
      gate.release();
      await Promise.resolve();
    });
    expect(await rows.findByRole("checkbox", { name: "Done: Buy milk" })).toBeEnabled();
    expect(api.calls.find((c) => c.method === "POST")?.body).toEqual({ title: "Buy milk" });
  });

  it("takes the todo away again if the server refuses, and keeps the text", async () => {
    const api = new FakeApi();
    api.failNext.POST = 400;
    const user = userEvent.setup();
    renderTodos("/todos?view=all");
    await screen.findByText("No open todos. Add one above.");

    await user.type(screen.getByLabelText("Add a todo"), "Too much");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The todo was not added");
    expect(screen.getByText("No open todos. Add one above.")).toBeInTheDocument();
    expect(screen.getByLabelText("Add a todo")).toHaveValue("Too much");
  });

  it("says where a todo went when it is not in this view", async () => {
    new FakeApi();
    const user = userEvent.setup();
    renderTodos("/todos?view=today");
    await screen.findByText("Nothing due today or overdue.");

    await user.type(screen.getByLabelText("Add a todo"), "Later");
    await user.type(screen.getByLabelText(/Due/), "2026-12-01");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(await screen.findByText("It is in Upcoming.")).toBeInTheDocument();
  });

  it("asks for a title instead of sending an empty one", async () => {
    const api = new FakeApi();
    const user = userEvent.setup();
    renderTodos("/todos?view=all");
    await screen.findByText("No open todos. Add one above.");

    await user.type(screen.getByLabelText("Add a todo"), "   ");
    await user.click(screen.getByRole("button", { name: "Add" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Write a title first.");
    expect(api.calls.some((c) => c.method === "POST")).toBe(false);
  });
});

describe("Todos page: tick and untick (US-11)", () => {
  it("ticks at once and tells the server", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Tick me", { dueDate: TODAY })];
    const user = userEvent.setup();
    renderTodos();

    const box = (await list()).getByRole("checkbox", { name: "Done: Tick me" });
    await user.click(box);

    expect(box).toBeChecked();
    expect(api.calls.find((c) => c.method === "PATCH")).toEqual({
      method: "PATCH",
      path: "/api/v1/todos/01JD01",
      body: { completed: true },
    });
    // It stays in place, so a mistake can be unticked right there.
    await user.click(await screen.findByRole("checkbox", { name: "Done: Tick me" }));
    expect(screen.getByRole("checkbox", { name: "Done: Tick me" })).not.toBeChecked();
  });

  it("puts the tick back if the server refuses", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Stubborn", { dueDate: TODAY })];
    const user = userEvent.setup();
    renderTodos();

    const box = (await list()).getByRole("checkbox", { name: "Done: Stubborn" });
    api.failNext.PATCH = 500;
    await user.click(box);

    expect(await screen.findByRole("alert")).toHaveTextContent("The todo was not ticked off");
    expect(screen.getByRole("checkbox", { name: "Done: Stubborn" })).not.toBeChecked();
  });
});

describe("Todos page: edit and delete (US-12)", () => {
  it("edits in place, loads the notes, and sends only what changed", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Old title", { notes: "Some notes", dueDate: TODAY })];
    const user = userEvent.setup();
    renderTodos();

    await user.click((await list()).getByRole("button", { name: "Old title" }));
    const form = await screen.findByRole("form", { name: "Edit Old title" });
    expect(await within(form).findByDisplayValue("Some notes")).toBeInTheDocument();

    const title = within(form).getByLabelText("Title");
    await user.clear(title);
    await user.type(title, "New title");
    await user.click(within(form).getByRole("button", { name: "Save" }));

    expect((await list()).getByText("New title")).toBeInTheDocument();
    expect(api.calls.find((c) => c.method === "PATCH")?.body).toEqual({ title: "New title" });
  });

  it("puts the old version back if a save is refused", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Keep me", { dueDate: TODAY })];
    const user = userEvent.setup();
    renderTodos();

    await user.click((await list()).getByRole("button", { name: "Keep me" }));
    const form = await screen.findByRole("form", { name: "Edit Keep me" });
    const title = within(form).getByLabelText("Title");
    await user.clear(title);
    await user.type(title, "Lost change");
    api.failNext.PATCH = 500;
    await user.click(within(form).getByRole("button", { name: "Save" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Your changes were not saved");
    expect((await list()).getByText("Keep me")).toBeInTheDocument();
  });

  it("deletes only after Yes, in the page", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Delete me", { dueDate: TODAY })];
    const user = userEvent.setup();
    renderTodos();

    await user.click((await list()).getByRole("button", { name: "Delete me" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    const confirm = screen.getByRole("group", { name: "Confirm delete" });
    expect(confirm).toHaveTextContent("Delete this todo for good?");

    await user.click(within(confirm).getByRole("button", { name: "No" }));
    expect(api.calls.some((c) => c.method === "DELETE")).toBe(false);

    await user.click(screen.getByRole("button", { name: "Delete" }));
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));

    expect(await screen.findByText("Nothing due today or overdue.")).toBeInTheDocument();
    expect(api.todos).toHaveLength(0);
  });

  it("puts a todo back if the delete is refused", async () => {
    const api = new FakeApi();
    api.todos = [todo("01JD01", "Survivor", { dueDate: TODAY })];
    const user = userEvent.setup();
    renderTodos();

    await user.click((await list()).getByRole("button", { name: "Survivor" }));
    await user.click(screen.getByRole("button", { name: "Delete" }));
    api.failNext.DELETE = 500;
    await user.click(screen.getByRole("button", { name: "Yes, delete" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("The todo was not deleted");
    expect((await list()).getByText("Survivor")).toBeInTheDocument();
  });
});

describe("Todos page: user text is only ever text (SR-35)", () => {
  it("shows markup in a title as letters, never as HTML", async () => {
    const api = new FakeApi();
    const payload = '<img src=x onerror="window.__xss=1">';
    api.todos = [todo("01JD01", payload, { dueDate: TODAY })];
    renderTodos();

    const rows = await list();
    expect(rows.getByText(payload)).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
    expect((window as unknown as { __xss?: number }).__xss).toBeUndefined();
  });
});
