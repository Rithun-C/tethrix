import { useCallback, useEffect, useRef, useState, type SyntheticEvent } from "react";
import { Link, useSearchParams } from "react-router";

import { ApiError } from "../api/client";
import {
  createTodo,
  deleteTodo,
  fitsView,
  getTodo,
  isView,
  listTodos,
  sortForView,
  updateTodo,
  type Priority,
  type Todo,
  type TodoChanges,
  type TodoSummary,
  type View,
} from "../api/todos";
import { Alert } from "../ui/Alert";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { Checkbox } from "../ui/Checkbox";
import { Field } from "../ui/Field";
import { useToast } from "../ui/Toast";

// The Todos page (B5, US-10 to US-13). Changes are optimistic (B5 decision 4): the list
// changes at once, and if the server refuses, the old copy is put back and a toast
// says why. Every piece of user text is rendered as React text, never as HTML (SR-35).

const VIEW_LABELS: Record<View, string> = {
  today: "Today",
  upcoming: "Upcoming",
  all: "All",
  completed: "Completed",
};

const EMPTY_TEXT: Record<View, string> = {
  today: "Nothing due today or overdue.",
  upcoming: "Nothing due after today.",
  all: "No open todos. Add one above.",
  completed: "Nothing completed yet.",
};

const PRIORITY_LABEL: Record<Priority, string> = { high: "High", medium: "Medium", low: "Low" };

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  timeZone: "UTC",
});

/** "2026-11-20" -> "20 Nov". The date has no time zone, so it is read and shown as UTC. */
function shortDate(isoDate: string): string {
  return dateFormat.format(new Date(`${isoDate}T00:00:00Z`));
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  return "Something went wrong.";
}

/** The user's date in this browser, until the server says otherwise. */
function localToday(): string {
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${String(now.getFullYear())}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

type LoadState = "loading" | "ready" | "error";

let tempIds = 0;

export function TodosPage() {
  const [params] = useSearchParams();
  const requested = params.get("view");
  const view: View = isView(requested) ? requested : "today";
  const toast = useToast();

  const [items, setItems] = useState<TodoSummary[]>([]);
  const [today, setToday] = useState(localToday);
  const [cursor, setCursor] = useState<string | null>(null);
  // Which load the list on screen belongs to. While it is not the current one, the page
  // shows "loading" (worked out here, not set inside the effect).
  const [loaded, setLoaded] = useState<{ key: string; ok: boolean } | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [reloadCount, setReloadCount] = useState(0);
  // Items the server has not confirmed yet; their controls wait.
  const [pending, setPending] = useState<ReadonlySet<string>>(new Set());

  const reload = useCallback(() => {
    setReloadCount((n) => n + 1);
  }, []);

  const loadKey = `${view}#${String(reloadCount)}`;
  const state: LoadState = loaded?.key !== loadKey ? "loading" : loaded.ok ? "ready" : "error";

  useEffect(() => {
    const controller = new AbortController();
    listTodos(view, undefined, controller.signal).then(
      (page) => {
        setItems(page.items);
        setCursor(page.nextCursor);
        setToday(page.today);
        setEditing(null);
        setLoaded({ key: `${view}#${String(reloadCount)}`, ok: true });
      },
      () => {
        if (!controller.signal.aborted) {
          setLoaded({ key: `${view}#${String(reloadCount)}`, ok: false });
        }
      },
    );
    return () => {
      controller.abort();
    };
  }, [view, reloadCount]);

  const markPending = (id: string, on: boolean) => {
    setPending((current) => {
      const copy = new Set(current);
      if (on) copy.add(id);
      else copy.delete(id);
      return copy;
    });
  };

  /** Shown when the server refuses a change: the change has been undone. */
  const refused = (title: string, error: unknown) => {
    toast({ tone: "danger", title, text: errorText(error) });
    if (error instanceof ApiError && (error.status === 404 || error.status === 409)) reload();
  };

  // ---- Add (US-10) ----

  const add = async (todo: { title: string; dueDate?: string; priority?: Priority }) => {
    tempIds += 1;
    const tempId = `tmp-${String(tempIds)}`;
    const draft: TodoSummary = {
      todoId: tempId,
      title: todo.title.trim(),
      dueDate: todo.dueDate ?? null,
      priority: todo.priority ?? null,
      completed: false,
      completedAt: null,
    };
    const shown = fitsView(draft, view, today);
    if (shown) {
      setItems((current) => sortForView([...current, draft], view));
      markPending(tempId, true);
    }
    try {
      const saved = await createTodo(todo);
      if (shown) {
        setItems((current) =>
          sortForView(
            current.map((t) => (t.todoId === tempId ? saved : t)),
            view,
          ),
        );
      } else {
        const where = (["today", "upcoming", "all"] as const).find((v) =>
          fitsView(saved, v, today),
        );
        toast({
          tone: "info",
          title: "Todo added",
          text: `It is in ${VIEW_LABELS[where ?? "all"]}.`,
        });
      }
    } catch (error) {
      setItems((current) => current.filter((t) => t.todoId !== tempId));
      refused("The todo was not added", error);
      throw error;
    } finally {
      markPending(tempId, false);
    }
  };

  // ---- Tick and untick (US-11) ----

  const toggle = async (todo: TodoSummary) => {
    const flipped: TodoSummary = {
      ...todo,
      completed: !todo.completed,
      completedAt: todo.completed ? null : new Date().toISOString(),
    };
    // The todo stays where it is until the view reloads, so a mistaken tick can be
    // unticked in the same place.
    setItems((current) => current.map((t) => (t.todoId === todo.todoId ? flipped : t)));
    markPending(todo.todoId, true);
    try {
      const saved = await updateTodo(todo.todoId, { completed: flipped.completed });
      setItems((current) => current.map((t) => (t.todoId === todo.todoId ? saved : t)));
    } catch (error) {
      setItems((current) => current.map((t) => (t.todoId === todo.todoId ? todo : t)));
      refused(
        flipped.completed ? "The todo was not ticked off" : "The todo was not unticked",
        error,
      );
    } finally {
      markPending(todo.todoId, false);
    }
  };

  // ---- Edit and delete (US-12) ----

  const save = async (before: TodoSummary, changes: TodoChanges) => {
    const after: TodoSummary = { ...before, ...changes };
    setItems((current) =>
      sortForView(
        current.map((t) => (t.todoId === before.todoId ? after : t)),
        view,
      ),
    );
    setEditing(null);
    markPending(before.todoId, true);
    try {
      const saved = await updateTodo(before.todoId, changes);
      setItems((current) =>
        sortForView(
          current.map((t) => (t.todoId === before.todoId ? saved : t)),
          view,
        ),
      );
    } catch (error) {
      setItems((current) =>
        sortForView(
          current.map((t) => (t.todoId === before.todoId ? before : t)),
          view,
        ),
      );
      refused("Your changes were not saved", error);
    } finally {
      markPending(before.todoId, false);
    }
  };

  const remove = async (todo: TodoSummary) => {
    const index = items.findIndex((t) => t.todoId === todo.todoId);
    setItems((current) => current.filter((t) => t.todoId !== todo.todoId));
    setEditing(null);
    try {
      await deleteTodo(todo.todoId);
      toast({ tone: "info", title: "Todo deleted" });
    } catch (error) {
      setItems((current) => {
        if (current.some((t) => t.todoId === todo.todoId)) return current;
        const copy = [...current];
        copy.splice(Math.max(index, 0), 0, todo);
        return copy;
      });
      refused("The todo was not deleted", error);
    }
  };

  // ---- Load more (SR-32) ----

  const loadMore = async () => {
    if (!cursor) return;
    setLoadingMore(true);
    try {
      const page = await listTodos(view, cursor);
      setItems((current) => {
        const known = new Set(current.map((t) => t.todoId));
        return [...current, ...page.items.filter((t) => !known.has(t.todoId))];
      });
      setCursor(page.nextCursor);
    } catch (error) {
      toast({ tone: "danger", title: "Could not load more", text: errorText(error) });
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="todos">
      <h1>Todos</h1>

      <nav className="view-tabs" aria-label="Todo views">
        {(Object.keys(VIEW_LABELS) as View[]).map((v) => (
          <Link
            key={v}
            to={`/todos?view=${v}`}
            className="view-tab"
            aria-current={v === view ? "page" : undefined}
          >
            {VIEW_LABELS[v]}
          </Link>
        ))}
      </nav>

      {view !== "completed" && <AddTodoForm onAdd={add} />}

      {state === "loading" && (
        <p className="todos-loading" role="status">
          Loading your todos...
        </p>
      )}

      {state === "error" && (
        <Alert
          tone="danger"
          title="Your todos could not be loaded"
          action={
            <Button size="sm" onClick={reload}>
              Try again
            </Button>
          }
        >
          Check your connection, then try again.
        </Alert>
      )}

      {state === "ready" && items.length === 0 && <p className="todos-empty">{EMPTY_TEXT[view]}</p>}

      {state === "ready" && items.length > 0 && (
        <ul className="todo-list" aria-label={`${VIEW_LABELS[view]} todos`}>
          {items.map((todo) =>
            editing === todo.todoId ? (
              <li key={todo.todoId} className="todo-item todo-item-editing">
                <EditTodoForm
                  todo={todo}
                  onSave={(changes) => void save(todo, changes)}
                  onCancel={() => {
                    setEditing(null);
                  }}
                  onDelete={() => void remove(todo)}
                />
              </li>
            ) : (
              <TodoRow
                key={todo.todoId}
                todo={todo}
                today={today}
                busy={pending.has(todo.todoId)}
                onToggle={() => void toggle(todo)}
                onEdit={() => {
                  setEditing(todo.todoId);
                }}
              />
            ),
          )}
        </ul>
      )}

      {state === "ready" && cursor && (
        <Button variant="secondary" onClick={() => void loadMore()} disabled={loadingMore}>
          {loadingMore ? "Loading..." : "Load more"}
        </Button>
      )}
    </div>
  );
}

// ---- One row ----

interface TodoRowProps {
  todo: TodoSummary;
  today: string;
  busy: boolean;
  onToggle: () => void;
  onEdit: () => void;
}

function TodoRow({ todo, today, busy, onToggle, onEdit }: TodoRowProps) {
  const overdue = !todo.completed && todo.dueDate !== null && todo.dueDate < today;
  return (
    <li className={`todo-item${todo.completed ? " todo-item-done" : ""}`}>
      <Checkbox
        checked={todo.completed}
        onChange={onToggle}
        disabled={busy}
        aria-label={`Done: ${todo.title}`}
      />
      <button type="button" className="todo-title" onClick={onEdit} disabled={busy}>
        {todo.title}
      </button>
      <span className="todo-meta">
        {overdue && <Badge tone="danger">Overdue</Badge>}
        {todo.priority && (
          <Badge tone={todo.priority === "high" ? "default" : "outline"}>
            {PRIORITY_LABEL[todo.priority]}
          </Badge>
        )}
        {todo.dueDate && (
          <time className="todo-date" dateTime={todo.dueDate}>
            {shortDate(todo.dueDate)}
          </time>
        )}
      </span>
    </li>
  );
}

// ---- Add form ----

function AddTodoForm({
  onAdd,
}: {
  onAdd: (todo: { title: string; dueDate?: string; priority?: Priority }) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [dueDate, setDueDate] = useState("");
  const [priority, setPriority] = useState<Priority | "">("");
  const [error, setError] = useState<string | null>(null);
  const titleRef = useRef<HTMLInputElement>(null);

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setError("Write a title first.");
      titleRef.current?.focus();
      return;
    }
    setError(null);
    const todo = {
      title: trimmed,
      ...(dueDate ? { dueDate } : {}),
      ...(priority ? { priority } : {}),
    };
    // Optimistic: the form clears at once. If the server refuses, the text comes back.
    setTitle("");
    setDueDate("");
    setPriority("");
    onAdd(todo).catch(() => {
      setTitle(todo.title);
      setDueDate(todo.dueDate ?? "");
      setPriority(todo.priority ?? "");
    });
  };

  return (
    <form className="todo-add" onSubmit={submit} noValidate>
      <Field label="Add a todo" className="todo-add-title">
        {(id) => (
          <input
            id={id}
            ref={titleRef}
            className="input"
            value={title}
            maxLength={200}
            placeholder="What needs doing?"
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? `${id}-error` : undefined}
            onChange={(e) => {
              setTitle(e.target.value);
            }}
          />
        )}
      </Field>
      <Field label="Due" optional>
        {(id) => (
          <input
            id={id}
            className="input"
            type="date"
            min="2000-01-01"
            max="2100-12-31"
            value={dueDate}
            onChange={(e) => {
              setDueDate(e.target.value);
            }}
          />
        )}
      </Field>
      <Field label="Priority" optional>
        {(id) => <PrioritySelect id={id} value={priority} onChange={setPriority} />}
      </Field>
      <Button type="submit" variant="primary" className="todo-add-button">
        Add
      </Button>
      {error && (
        <p className="field-error todo-add-error" role="alert">
          {error}
        </p>
      )}
    </form>
  );
}

function PrioritySelect({
  id,
  value,
  onChange,
}: {
  id: string;
  value: Priority | "";
  onChange: (value: Priority | "") => void;
}) {
  return (
    <select
      id={id}
      className="input select"
      value={value}
      onChange={(e) => {
        onChange(e.target.value as Priority | "");
      }}
    >
      <option value="">None</option>
      <option value="high">High</option>
      <option value="medium">Medium</option>
      <option value="low">Low</option>
    </select>
  );
}

// ---- Edit form ----

interface EditTodoFormProps {
  todo: TodoSummary;
  onSave: (changes: TodoChanges) => void;
  onCancel: () => void;
  onDelete: () => void;
}

function EditTodoForm({ todo, onSave, onCancel, onDelete }: EditTodoFormProps) {
  const [detail, setDetail] = useState<Todo | null>(null);
  const [failed, setFailed] = useState(false);
  const [title, setTitle] = useState(todo.title);
  const [notes, setNotes] = useState("");
  const [dueDate, setDueDate] = useState(todo.dueDate ?? "");
  const [priority, setPriority] = useState<Priority | "">(todo.priority ?? "");
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const titleRef = useRef<HTMLInputElement>(null);

  // The list has no notes (I-08), so the form fetches the one todo (B5 decision 1).
  useEffect(() => {
    const controller = new AbortController();
    getTodo(todo.todoId, controller.signal).then(
      (full) => {
        setDetail(full);
        setNotes(full.notes ?? "");
      },
      () => {
        if (!controller.signal.aborted) setFailed(true);
      },
    );
    titleRef.current?.focus();
    return () => {
      controller.abort();
    };
  }, [todo.todoId]);

  const submit = (event: SyntheticEvent) => {
    event.preventDefault();
    const trimmed = title.trim();
    if (!trimmed) {
      setError("A todo needs a title.");
      titleRef.current?.focus();
      return;
    }
    const changes: TodoChanges = {};
    if (trimmed !== todo.title) changes.title = trimmed;
    if ((dueDate || null) !== todo.dueDate) changes.dueDate = dueDate || null;
    if ((priority || null) !== todo.priority) changes.priority = priority || null;
    if (detail && notes !== (detail.notes ?? "")) changes.notes = notes || null;
    if (Object.keys(changes).length === 0) {
      onCancel();
      return;
    }
    onSave(changes);
  };

  return (
    <form className="todo-edit" onSubmit={submit} noValidate aria-label={`Edit ${todo.title}`}>
      <Field label="Title">
        {(id) => (
          <input
            id={id}
            ref={titleRef}
            className="input"
            value={title}
            maxLength={200}
            aria-invalid={error ? true : undefined}
            onChange={(e) => {
              setTitle(e.target.value);
            }}
          />
        )}
      </Field>
      <Field label="Notes" optional>
        {(id) => (
          <textarea
            id={id}
            className="input textarea"
            value={notes}
            maxLength={2000}
            rows={3}
            disabled={!detail}
            placeholder={detail ? undefined : failed ? "Notes could not be loaded." : "Loading..."}
            onChange={(e) => {
              setNotes(e.target.value);
            }}
          />
        )}
      </Field>
      <div className="todo-edit-row">
        <Field label="Due" optional>
          {(id) => (
            <input
              id={id}
              className="input"
              type="date"
              min="2000-01-01"
              max="2100-12-31"
              value={dueDate}
              onChange={(e) => {
                setDueDate(e.target.value);
              }}
            />
          )}
        </Field>
        <Field label="Priority" optional>
          {(id) => <PrioritySelect id={id} value={priority} onChange={setPriority} />}
        </Field>
      </div>
      {error && (
        <p className="field-error" role="alert">
          {error}
        </p>
      )}
      {confirming ? (
        <div className="todo-confirm" role="group" aria-label="Confirm delete">
          <span>Delete this todo for good?</span>
          <Button variant="danger" onClick={onDelete}>
            Yes, delete
          </Button>
          <Button
            onClick={() => {
              setConfirming(false);
            }}
          >
            No
          </Button>
        </div>
      ) : (
        <div className="todo-edit-actions">
          <Button type="submit" variant="primary">
            Save
          </Button>
          <Button onClick={onCancel}>Cancel</Button>
          <Button
            variant="ghost"
            className="btn-danger-text"
            onClick={() => {
              setConfirming(true);
            }}
          >
            Delete
          </Button>
        </div>
      )}
    </form>
  );
}
