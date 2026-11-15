# I-02: User stories and acceptance criteria

- Status: Approved 2026-11-15
- Date: 2026-11-15
- Based on: `01-vision-and-scope.md` (MVP features only)

## How to read this

Each story says who wants what, and why:

> As a user, I want [something] so that [reason].

The acceptance criteria are the checks that prove the story is done. Each one becomes at
least one automated test in the bolt that builds it.

"User" means a signed-in user. "Admin" means the owner, working through the CLI or
Terraform.

## Accounts and sign-in (bolt B4)

**US-01: Create an account (admin)**
As the admin, I want to create user accounts myself so that strangers cannot sign up.
- [ ] There is no sign-up page or sign-up API.
- [ ] The admin creates a user with one CLI command, documented in a runbook.
- [ ] The new user must set their own password at first sign-in.

**US-02: Sign in with MFA**
As a user, I want to sign in with my password and an authenticator app code so that a
stolen password alone is not enough.
- [ ] Sign-in asks for email, password and a 6-digit code.
- [ ] A user without MFA set up is made to set it up at first sign-in.
- [ ] Wrong password or code shows one generic message ("Sign-in failed"), never which
      part was wrong.

**US-03: Stay signed in, and sign out**
As a user, I want to stay signed in while I use the app, and to sign out when I am done.
- [ ] A session lasts until sign-out or 1 hour of inactivity.
- [ ] Sign-out clears the session on this device; the back button does not show my data.

**US-04: Only see my own data**
As a user, I want to be certain no other user can see or change my data.
- [ ] Every API request without a valid token gets 401.
- [ ] A request for another user's item gets 404 (not 403, so it does not reveal the item
      exists).
- [ ] An automated two-user test runs for every feature: user B tries to read, edit and
      delete each of user A's item types and fails every time.

## Todos (bolt B5)

**US-10: Add a todo**
As a user, I want to add a todo with a title so that I do not forget it.
- [ ] Title is required, 1 to 200 characters. Notes are optional, up to 2,000 characters.
- [ ] Due date and priority (low, medium, high) are optional.
- [ ] The new todo appears in the list without reloading the page.

**US-11: Complete a todo**
As a user, I want to tick a todo off, and untick it if I made a mistake.
- [ ] Ticking moves it to Completed and records when.
- [ ] Unticking moves it back.

**US-12: Edit and delete a todo**
- [ ] I can change any field.
- [ ] Delete asks for confirmation, then removes the todo for good.

**US-13: See todos by view**
As a user, I want Today, Upcoming, All and Completed views so that I see what matters now.
- [ ] Today: due today or overdue, not completed. Overdue ones are marked.
- [ ] Upcoming: due after today, sorted by due date.
- [ ] All: every open todo. Completed: done todos, newest first.
- [ ] "Today" uses my time zone, not the server's.

## Habits (bolt B7)

**US-20: Create a habit**
As a user, I want to create a habit with a schedule so that I know which days it is due.
- [ ] Name is required, 1 to 100 characters.
- [ ] Schedule: every day, or chosen weekdays (at least one).
- [ ] I can edit the name and schedule later.

**US-21: Check in**
As a user, I want to check in a habit for today, and undo it.
- [ ] Only today can be checked in (past days are Later).
- [ ] Checking in twice on the same day has no extra effect.

**US-22: See streaks and history**
As a user, I want to see my streaks and the last 30 days so that I stay motivated.
- [ ] Current streak: scheduled days in a row checked in, counting back from today
      (today not yet checked does not break it).
- [ ] Days the habit is not scheduled do not break a streak.
- [ ] Longest streak is shown next to the current one.
- [ ] A 30-day grid shows checked, missed and not-scheduled days differently.

**US-23: Archive a habit**
- [ ] Archived habits disappear from Today and the dashboard but keep their history.
- [ ] I can unarchive one.

## Journal (bolt B8)

**US-30: Write today's entry**
As a user, I want to write one entry per day, with an optional mood, so that I can
reflect.
- [ ] One entry per date. Opening today's entry again edits the same one.
- [ ] Text up to 20,000 characters. Mood 1 to 5, optional.
- [ ] Changes save automatically while typing.

**US-31: Read past entries**
- [ ] I can move between dates and open any past entry.
- [ ] Days without an entry show as empty.

**US-32: Edit and delete an entry**
- [ ] I can edit any past entry.
- [ ] Delete asks for confirmation.

**US-33: Journal privacy**
As a user, I want my journal to stay private even from logs and errors.
- [ ] Journal text never appears in application logs, error messages or traces. A test
      checks this.
- [ ] Journal text is encrypted at rest (the method is decided in an ADR in B8).

## Pages (bolt B8)

**US-40: Create and manage pages**
As a user, I want to create, rename and delete pages for longer notes.
- [ ] New pages start as "Untitled". Title up to 200 characters.
- [ ] Delete asks for confirmation.
- [ ] The page list is sorted by last edited.

**US-41: Write rich text**
As a user, I want headings, bold, italic, lists, checklists, links and code blocks.
- [ ] All the formats above work and look the same after reloading.
- [ ] Changes save automatically while typing, with a visible "Saved" status.
- [ ] A page has a size limit; going over it shows a clear message instead of failing.

**US-42: Pages are safe**
As a user, I want pages to be unable to run code, even if I paste something nasty.
- [ ] Pasted or saved `<script>`, `onerror=` and `javascript:` links never run. Tests use
      a list of known XSS payloads.
- [ ] The server rejects page content that does not match the editor's format.
- [ ] Links open in a new tab without giving that tab access to the app.

## Dashboard (bolt B9)

**US-50: See my day at a glance**
As a user, I want one screen with today's todos, today's habits, my journal status and
recent pages.
- [ ] Shows today's and overdue todos, with tick boxes.
- [ ] Shows habits due today, with check-in buttons and current streaks.
- [ ] Shows today's journal entry, or a "Write today's entry" button.
- [ ] Shows the 5 most recently edited pages.
- [ ] Loads with one request to the API, not one per section.

## Data (bolt B9)

**US-60: Export everything**
As a user, I want to download all my data so that I keep it after the AWS account closes.
- [ ] One button downloads a zip file.
- [ ] The zip has all data as JSON, plus each journal entry and page as a Markdown file.
- [ ] The export contains only my data (two-user test).

**US-61: Delete my account**
As a user, I want to delete my account and everything in it.
- [ ] Asks me to type a confirmation phrase.
- [ ] Removes all my items and my sign-in account.
- [ ] Afterwards, my old token no longer works.

## Not stories, but checked in every bolt

These come from the Definition of Done and the quality goals:

- Every list the API returns is paginated (no unlimited results).
- Every input has a maximum size, checked on the server.
- Errors never show stack traces or internal details to the user.
- The scanners pass, and the threat model is updated.

## Decisions

Approved by the owner on 2026-11-15 with the suggested values:

1. Session: signed out after 1 hour of inactivity.
2. Journal entry size: up to 20,000 characters.
