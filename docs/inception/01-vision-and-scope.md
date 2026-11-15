# I-01: Vision, scope and cut line

- Status: Approved 2026-11-15
- Date: 2026-11-15

## Vision

One private place for my day: what I have to do, the habits I am building, what I am
thinking, and longer notes. Simple enough to use every day, built well enough to learn
real AWS, security and Terraform from it.

## Who uses it

- Me, as the main user.
- A second test account, used to prove one user can never see another user's data (IDOR
  tests).
- No public sign-up. New accounts are created by the admin only. This keeps strangers,
  spam accounts and their cost out.

## Features

MVP = built in the bolts. Later = only if time allows. Out = not in this project.

### Todos (bolt B5)

| Feature | Scope |
|---|---|
| Create, edit, delete a todo (title, optional notes) | MVP |
| Mark done / not done | MVP |
| Optional due date and priority (low, medium, high) | MVP |
| Views: Today, Upcoming, All, Completed | MVP |
| Lists or tags to group todos | Later |
| Recurring todos | Later (needs reminders) |

### Habits (bolt B7)

| Feature | Scope |
|---|---|
| Create, edit, archive a habit (name, schedule: every day or chosen weekdays) | MVP |
| Check in for today, undo a check-in | MVP |
| Current streak and longest streak | MVP |
| Last 30 days shown as a simple grid | MVP |
| Check in for a past day | Later |

### Journal (bolt B8)

| Feature | Scope |
|---|---|
| One entry per day: text and an optional mood (1 to 5) | MVP |
| Browse entries by date | MVP |
| Edit and delete an entry | MVP |
| Rich text in journal entries | Later (reuse the Pages editor) |

### Pages (bolt B8)

| Feature | Scope |
|---|---|
| Create, rename, delete a page | MVP |
| Rich text: headings, bold, italic, lists, checklists, links, code blocks | MVP |
| Auto-save while typing | MVP |
| Pages inside pages (nesting) | Later |
| Images inside pages | Later (needs attachments) |

### Dashboard (bolt B9)

| Feature | Scope |
|---|---|
| Today's and overdue todos | MVP |
| Today's habits with check-in buttons and streaks | MVP |
| Latest journal entry, or a "write today's entry" prompt | MVP |
| Recently edited pages | MVP |

### Account and data (bolts B4, B9)

| Feature | Scope |
|---|---|
| Sign in and sign out, with MFA (authenticator app) | MVP |
| Export all my data (JSON, plus pages and journal as Markdown) | MVP |
| Delete my account and all its data | MVP |

### Later bolts (B10, first to cut)

| Feature | Scope |
|---|---|
| Attach files to pages and todos | Later |
| Reminders by email for todos with a due time | Later |

### Out of scope

Search, sharing and collaboration, mobile apps, offline mode, AI features, a custom
domain, multiple languages.

## Quality goals

| Goal | Target | Why |
|---|---|---|
| Cost | Under 2 USD a month when no lab is running | Credits must last to 2027-04-30 |
| Privacy | No user can read another user's data; journal text never appears in logs | Journal is sensitive personal data |
| Security | Every bolt passes the scanners and the Definition of Done | Learning goal |
| Speed | Pages load in under 2 seconds normally; the first request after idle may take up to 3 seconds | Lambda "cold starts" are an accepted trade-off for near-zero cost |
| Availability | Best effort. No uptime target | Personal learning project |
| Devices | Works in a desktop and a phone browser | No separate mobile app |

## Cut line

If the schedule slips, cut in this order:

1. B10 Attachments and reminders
2. The RDS and ECS labs in B11 (become theory notes)
3. Habit history grid and dashboard extras (keep only today's items)

Never cut: authentication, IDOR protection, XSS defences, data export (needed before the
account closes), the Definition of Done.

## How we know it worked

- I use the app daily for at least the last month of the project.
- Every MVP feature above is deployed and passes its tests.
- The O-05 Prowler rerun has no new unexplained failures compared to the baseline.
- The incident drill (O-07) is done and written up.
- Total credit use stays within the cost model (I-11).
- Everything is exported and destroyed by 2027-04-30.

## Decisions

Approved by the owner on 2026-11-15 with the recommended options:

1. Sign-up: admin creates accounts only. No public sign-up.
2. Journal: one entry per day.
3. Nothing added to the MVP.
