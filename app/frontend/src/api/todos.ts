// The todos API (B5, docs/bolts/B5-todos.md section 4). Thin wrappers around apiFetch.

import { apiFetch } from "./client";

export const VIEWS = ["today", "upcoming", "all", "completed"] as const;
export type View = (typeof VIEWS)[number];

export type Priority = "low" | "medium" | "high";

/** A todo as lists show it. */
export interface TodoSummary {
  todoId: string;
  title: string;
  dueDate: string | null;
  priority: Priority | null;
  completed: boolean;
  completedAt: string | null;
}

/** One todo with everything, from GET /todos/{id}. */
export interface Todo extends TodoSummary {
  notes: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface TodoPage {
  items: TodoSummary[];
  nextCursor: string | null;
  /** The user's date today, in their time zone (for "Overdue"). */
  today: string;
}

export interface NewTodo {
  title: string;
  notes?: string;
  dueDate?: string;
  priority?: Priority;
}

/** Only the fields sent change; null clears an optional one. */
export interface TodoChanges {
  title?: string;
  notes?: string | null;
  dueDate?: string | null;
  priority?: Priority | null;
  completed?: boolean;
}

export function isView(value: string | null): value is View {
  return value !== null && (VIEWS as readonly string[]).includes(value);
}

export function listTodos(view: View, cursor?: string, signal?: AbortSignal): Promise<TodoPage> {
  const params = new URLSearchParams({ view });
  if (cursor) params.set("cursor", cursor);
  return apiFetch<TodoPage>(`/todos?${params.toString()}`, { signal });
}

export function getTodo(todoId: string, signal?: AbortSignal): Promise<Todo> {
  return apiFetch<Todo>(`/todos/${encodeURIComponent(todoId)}`, { signal });
}

export function createTodo(todo: NewTodo): Promise<Todo> {
  return apiFetch<Todo>("/todos", { method: "POST", body: todo });
}

export function updateTodo(todoId: string, changes: TodoChanges): Promise<Todo> {
  return apiFetch<Todo>(`/todos/${encodeURIComponent(todoId)}`, { method: "PATCH", body: changes });
}

export function deleteTodo(todoId: string): Promise<void> {
  return apiFetch<undefined>(`/todos/${encodeURIComponent(todoId)}`, { method: "DELETE" });
}

/** Does this todo belong in this view, as the server decides it (I-08)? */
export function fitsView(todo: TodoSummary, view: View, today: string): boolean {
  if (view === "completed") return todo.completed;
  if (todo.completed) return false;
  if (view === "all") return true;
  if (!todo.dueDate) return false;
  return view === "today" ? todo.dueDate <= today : todo.dueDate > today;
}

/** The server's order for a view: open ones by due date (undated last), then creation;
 * completed ones newest first. IDs are ULIDs, so they sort by creation time. */
export function sortForView(items: TodoSummary[], view: View): TodoSummary[] {
  const copy = [...items];
  if (view === "completed") {
    return copy.sort((a, b) => (b.completedAt ?? "").localeCompare(a.completedAt ?? ""));
  }
  const key = (t: TodoSummary) => `${t.dueDate ? `D${t.dueDate}` : "N"}#${t.todoId}`;
  return copy.sort((a, b) => key(a).localeCompare(key(b)));
}
