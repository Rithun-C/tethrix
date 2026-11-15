# I-08: DynamoDB table design

- Status: Approved 2026-11-15 (100 KB page limit, provisioned capacity)
- Date: 2026-11-15
- Based on: `03-domain-model-and-api.md`. Goes with ADR-0001.

## 1. DynamoDB in five ideas

1. A table holds items. An item is like a row, but items in one table can have different
   fields.
2. Every item has a primary key with two parts:
   - Partition key (PK): decides where the item is stored. All items with the same PK
     are kept together.
   - Sort key (SK): orders the items inside one partition.
3. Fast, cheap reads only work by key: "get this exact item" (GetItem), or "get items in
   this partition whose SK starts with / is between ..." (Query). Anything else means
   reading the whole table (Scan), which we never do.
4. So you design the keys from the questions the app asks (the access patterns), not
   from the data. This is the opposite of a relational database.
5. A global secondary index (GSI) is a second copy of selected items with different keys,
   kept up to date by DynamoDB, so you can query the same data another way.

## 2. Access patterns

Every API endpoint needs one of these. If a pattern is not listed here, the design
cannot answer it cheaply.

| # | Question the app asks | Endpoint |
|---|---|---|
| AP1 | Get my profile | GET /me |
| AP2 | Open todos due today or earlier | GET /todos?view=today, dashboard |
| AP3 | Open todos due after today, by due date | GET /todos?view=upcoming |
| AP4 | All open todos | GET /todos?view=all |
| AP5 | Completed todos, newest first | GET /todos?view=completed |
| AP6 | Get, change or delete one todo | PATCH, DELETE /todos/{id} |
| AP7 | All my habits | GET /habits, dashboard |
| AP8 | All check-ins for my habits (for streaks and the grid) | GET /habits, dashboard |
| AP9 | Add or remove one check-in | PUT, DELETE /habits/{id}/checkins/{date} |
| AP10 | Journal entries between two dates | GET /journal?from=&to= |
| AP11 | Get, write or delete the entry for a date | GET, PUT, DELETE /journal/{date} |
| AP12 | My pages, last edited first, titles only | GET /pages, dashboard |
| AP13 | Get, save or delete one page | GET, PATCH, DELETE /pages/{id} |
| AP14 | Everything I own (export, account deletion) | GET /export, DELETE /me |

## 3. The design: one table, one partition per user

Table name: `productivity-app-data`

Every item of a user has the same partition key: `USER#<userId>`. The sort key says what
the item is.

| Item | PK | SK | Other fields |
|---|---|---|---|
| Profile | `USER#<userId>` | `PROFILE` | timeZone, createdAt |
| Todo | `USER#<userId>` | `TODO#<todoId>` | title, notes, dueDate, priority, completed, completedAt, ... |
| Habit | `USER#<userId>` | `HABIT#<habitId>` | name, schedule, archived, ... |
| Check-in | `USER#<userId>` | `CHECKIN#<habitId>#<date>` | createdAt |
| Journal entry | `USER#<userId>` | `JOURNAL#<date>` | text, mood, ... |
| Page | `USER#<userId>` | `PAGE#<pageId>` | title, content, version, ... |

Example: a user's partition, sorted by SK:

```
PK=USER#u1   SK=CHECKIN#h1#2026-11-14
PK=USER#u1   SK=CHECKIN#h1#2026-11-15
PK=USER#u1   SK=HABIT#h1
PK=USER#u1   SK=JOURNAL#2026-11-15
PK=USER#u1   SK=PAGE#p1
PK=USER#u1   SK=PROFILE
PK=USER#u1   SK=TODO#t1
PK=USER#u1   SK=TODO#t2
```

### Why one partition per user

- IDOR protection is built into the shape of the data. The API takes the userId from the
  verified token and every query starts with `PK = USER#<that id>`. There is no query that
  can reach another partition.
- Export and account deletion (AP14) are one Query on the user's partition.
- One table means one set of Terraform, one IAM permission, one capacity setting.

### Index GSI1: todos by status and date, pages by last edit

Some questions need a different order than the SK gives (todos by due date, pages by
last edit). Only todos and pages get GSI1 fields. Other items leave them out, so they do
not appear in the index at all. This is called a sparse index.

| Item | GSI1PK | GSI1SK |
|---|---|---|
| Open todo with due date | `USER#<userId>#TODO#OPEN` | `DUE#<dueDate>#<todoId>` |
| Open todo, no due date | `USER#<userId>#TODO#OPEN` | `NODUE#<todoId>` |
| Completed todo | `USER#<userId>#TODO#DONE` | `DONE#<completedAt>#<todoId>` |
| Page | `USER#<userId>#PAGES` | `EDITED#<updatedAt>#<pageId>` |

The index only copies the fields lists need (title, dueDate, priority, completed). It
does not copy page content or notes. This is called the projection. It keeps the index
small, and keeps each page save cheap: the index copy of a page is a few bytes, not the
whole document.

### How each access pattern is answered

| # | How |
|---|---|
| AP1 | GetItem `PK=USER#u, SK=PROFILE` |
| AP2 | Query GSI1 `GSI1PK=USER#u#TODO#OPEN`, `GSI1SK <= DUE#<today>~` (sorted by due date; `NODUE#` sorts after `DUE#`, so undated todos are excluded) |
| AP3 | Query GSI1 `GSI1PK=USER#u#TODO#OPEN`, `GSI1SK BETWEEN DUE#<tomorrow> AND DUE#9999` |
| AP4 | Query GSI1 `GSI1PK=USER#u#TODO#OPEN` (all of it) |
| AP5 | Query GSI1 `GSI1PK=USER#u#TODO#DONE`, newest first |
| AP6 | GetItem / UpdateItem / DeleteItem `SK=TODO#<id>`. Completing a todo changes its GSI1 keys, which moves it from OPEN to DONE in the index automatically |
| AP7 | Query `PK=USER#u`, `SK begins_with HABIT#` |
| AP8 | Query `PK=USER#u`, `SK begins_with CHECKIN#` (sorted by habit, then date) |
| AP9 | PutItem / DeleteItem `SK=CHECKIN#<habitId>#<date>`. Putting the same key twice just overwrites it, so a check-in is naturally idempotent |
| AP10 | Query `PK=USER#u`, `SK BETWEEN JOURNAL#<from> AND JOURNAL#<to>`, returning only date and mood |
| AP11 | GetItem / PutItem / DeleteItem `SK=JOURNAL#<date>`. One key per date enforces one entry per day |
| AP12 | Query GSI1 `GSI1PK=USER#u#PAGES`, newest first, limit 50 |
| AP13 | GetItem / UpdateItem / DeleteItem `SK=PAGE#<id>`. Save uses a condition: only if `version` = the version the editor started from, otherwise 409 |
| AP14 | Query `PK=USER#u` (all items, paginated), then batch delete for account deletion |

The dashboard runs AP2, AP7, AP8, AP11 (today) and AP12 at the same time inside one API
request.

Every pattern is a GetItem or a Query. No Scans.

## 4. Size limits

A DynamoDB item can be at most 400 KB, including field names.

| Item | Limit we set | Why |
|---|---|---|
| Page content | 100 KB of editor JSON (roughly 10,000 words) | Well under 400 KB, and keeps each save affordable (see capacity) |
| Journal text | 20,000 characters (from I-02) | Up to about 80 KB in the worst case of non-English characters; usually about 20 KB |
| Todo notes | 2,000 characters | |

If 100 KB pages turn out too small in B8, the fallback is to store page content in S3
and keep only the metadata in DynamoDB.

## 5. Settings

| Setting | Value | Why |
|---|---|---|
| Capacity mode | Provisioned: table 10 read / 10 write units, GSI1 5 / 5 | See "Capacity" below |
| Encryption | Default (AWS owned key) | Free. Journal encryption gets its own ADR in B8 |
| Deletion protection | On | `terraform destroy` or a mistake cannot delete the table; turned off on purpose at the end |
| Point-in-time recovery (backups) | Decided in O-08 | Costs per GB-month; tiny, but not free |
| Local development | DynamoDB Local in Docker Compose (B2) | Same API, runs on the laptop, costs nothing |

### Capacity

DynamoDB has two ways to pay:

| | Provisioned | On-demand |
|---|---|---|
| You pay for | Reserved units per hour, used or not | Each request |
| Free tier | 25 read and 25 write units, always free | None for requests |
| Our cost | 0 USD (15 of the 25 units) | A few cents a month |
| If traffic is too high | Requests are slowed down (throttled) | Pays for every request |
| Runaway bug | Can never cost more | Costs grow with the bug until noticed |

Recommendation: provisioned. It is free, and it caps cost by design. A bug that loops
cannot spend credits; it gets throttled instead.

The trade-off to watch: a write uses 1 unit per 1 KB. Saving a 100 KB page uses 100 write
units, more than the 10 per second reserved. DynamoDB keeps up to 5 minutes of unused
capacity as burst, which covers occasional large saves, and the editor only saves a few
seconds after you stop typing. If throttling shows up in B8, switching to on-demand is a
one-line change.

## 6. What this design cannot do (on purpose)

- Search inside todos, journal or pages. Out of scope (I-01).
- Queries across users. The app never needs them, and not being able to is a security
  feature.
