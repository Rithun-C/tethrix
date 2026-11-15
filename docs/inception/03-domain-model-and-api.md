# I-03: Domain model and API outline

- Status: Approved 2026-11-15
- Date: 2026-11-15
- Based on: `02-user-stories.md`

This describes what the app stores and how the frontend talks to the backend. It does
not decide how the data sits in the database; that is I-04 (ADR-0001) and I-08.

## 1. Domain model

The domain model is the list of things the app knows about, their fields and how they
relate. It is independent of any database.

```
User 1 ──── * Todo
     1 ──── * Habit 1 ──── * CheckIn
     1 ──── * JournalEntry
     1 ──── * Page
```

Read `1 ──── *` as "one user has many todos". Everything belongs to exactly one user.

### User

| Field | Type | Notes |
|---|---|---|
| userId | string | The `sub` from the Cognito token. Never sent by the browser |
| timeZone | string | For example `Asia/Kolkata`. Used for "today" |
| createdAt | timestamp | |

Email and password live in Cognito only, not in our database.

### Todo

| Field | Type | Rules |
|---|---|---|
| todoId | ID | Created by the server |
| title | text | Required, 1 to 200 characters |
| notes | text | Optional, up to 2,000 characters |
| dueDate | date | Optional |
| priority | low, medium, high | Optional |
| completed | true or false | |
| completedAt | timestamp | Set when completed |
| createdAt, updatedAt | timestamp | |

### Habit and CheckIn

| Habit field | Type | Rules |
|---|---|---|
| habitId | ID | |
| name | text | Required, 1 to 100 characters |
| schedule | "daily", or a list of weekdays | At least one weekday |
| archived | true or false | |
| createdAt, updatedAt | timestamp | |

| CheckIn field | Type | Rules |
|---|---|---|
| habitId | ID | |
| date | date | At most one check-in per habit per date |
| createdAt | timestamp | |

Streaks are not stored. They are calculated from check-ins and the schedule. Storing
them would mean two sources of truth that can disagree.

### JournalEntry

| Field | Type | Rules |
|---|---|---|
| date | date | The identifier: one entry per date |
| text | text | Up to 20,000 characters. Sensitive |
| mood | 1 to 5 | Optional |
| createdAt, updatedAt | timestamp | |

### Page

| Field | Type | Rules |
|---|---|---|
| pageId | ID | |
| title | text | Up to 200 characters |
| content | editor document (JSON) | Must match the editor's format. Size limit set in B8 |
| version | number | Goes up by 1 on every save (see "Auto-save" below) |
| createdAt, updatedAt | timestamp | |

### Things that are calculated, not stored

Dashboard, streaks, the 30-day habit grid, the export file.

## 2. Rules that apply to everything

- IDs are ULIDs, created by the server. A ULID is a random ID that also sorts by
  creation time, so "newest first" needs no extra field. The browser never chooses an ID.
- The user is always taken from the verified token, never from the URL or body. This is
  the main protection against IDOR: there is no way to even ask for another user's data.
- Dates (`dueDate`, check-in date, journal date) are plain dates like `2026-11-15`, in the
  user's time zone. Timestamps are UTC, like `2026-11-15T08:30:00Z`.

## 3. API outline

The API is REST over HTTPS, with JSON. REST means each kind of thing has its own address
(a resource), and the HTTP method says what to do with it:

| Method | Meaning | Safe to repeat? |
|---|---|---|
| GET | Read | Yes |
| POST | Create a new item | No: repeating creates a second item |
| PUT | Create or fully replace the item at this address | Yes |
| PATCH | Change some fields | Yes, for our uses |
| DELETE | Remove | Yes |

"Safe to repeat" is called idempotent. It matters because networks fail and the app
retries. Retrying an idempotent request cannot cause damage.

All paths start with `/api/v1`. The `v1` lets a future version change the API without
breaking the old one.

### Endpoints

| Method and path | Story | What it does |
|---|---|---|
| GET `/health` | | Is the API up? The only endpoint without sign-in |
| GET `/me` | US-03 | My profile (time zone) |
| PATCH `/me` | | Change my time zone |
| DELETE `/me` | US-61 | Delete my account and all my data |
| GET `/todos?view=today\|upcoming\|all\|completed` | US-13 | List todos in a view |
| POST `/todos` | US-10 | Add a todo |
| PATCH `/todos/{todoId}` | US-11, US-12 | Edit, complete or uncomplete |
| DELETE `/todos/{todoId}` | US-12 | Delete |
| GET `/habits?archived=false` | US-22 | List habits with streaks and 30-day history |
| POST `/habits` | US-20 | Create a habit |
| PATCH `/habits/{habitId}` | US-20, US-23 | Edit, archive or unarchive |
| PUT `/habits/{habitId}/checkins/{date}` | US-21 | Check in (repeating does nothing extra) |
| DELETE `/habits/{habitId}/checkins/{date}` | US-21 | Undo a check-in |
| GET `/journal?from=&to=` | US-31 | List entries in a date range (dates and moods only) |
| GET `/journal/{date}` | US-31 | Read one entry |
| PUT `/journal/{date}` | US-30, US-32 | Write or update the entry for that date |
| DELETE `/journal/{date}` | US-32 | Delete |
| GET `/pages` | US-40 | List pages (titles only), last edited first |
| POST `/pages` | US-40 | Create an "Untitled" page |
| GET `/pages/{pageId}` | US-41 | Read a page with its content |
| PATCH `/pages/{pageId}` | US-40, US-41 | Rename or save content |
| DELETE `/pages/{pageId}` | US-40 | Delete |
| GET `/dashboard` | US-50 | Everything for the dashboard, in one response |
| GET `/export` | US-60 | Download all my data as a zip |

24 endpoints. No endpoint creates users; the admin does that through Cognito (US-01).

### Conventions

**Sign-in token.** Every request except `/health` carries the user's token. Which header it
travels in is decided in ADR-0003 (OAC replaces the normal `Authorization` header).

**Status codes.**

| Code | When |
|---|---|
| 200 / 201 / 204 | OK / created / done, nothing to return |
| 400 | Invalid input (too long, wrong format) |
| 401 | Not signed in, or token invalid or expired |
| 404 | Not found, including items that belong to someone else |
| 409 | Conflict: the page was saved elsewhere since you loaded it |
| 413 | Too large (page over its size limit) |
| 429 | Too many requests |
| 500 | Server error. The response never contains internal details |

**Error format.** Always the same shape, so the frontend handles errors in one place:

```json
{ "error": { "code": "validation_error", "message": "Title must be 1 to 200 characters." } }
```

**Pagination.** Lists return at most 50 items plus a `nextCursor`. To get more, send the
cursor back: `GET /todos?view=all&cursor=...`. A cursor is an opaque marker of where the
last page ended. Without pagination, one request could try to return everything.

**Auto-save and conflicts (pages and journal).** The editor saves a few seconds after you
stop typing. A page save sends the `version` it started from. If the stored version is
newer (for example, the page is open in two tabs), the server answers 409 instead of
silently overwriting. This is called optimistic concurrency.

**Request size.** The server rejects any request body over a fixed limit before reading
it.

## 4. Known risks to carry forward

| Risk | Where it is handled |
|---|---|
| Lambda responses have a maximum size (a few MB). A large export zip could exceed it | B9: if needed, build the zip in S3 and return a short-lived download link |
| Page content can grow past the database item size limit | I-08 table design and the B8 size limit |
| "Today" depends on the user's time zone, which affects views, streaks and the dashboard | Time zone is stored on the user; tests cover a time zone far from UTC |
