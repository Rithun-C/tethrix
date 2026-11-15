# ADR-0001: Database choice

- Status: Accepted 2026-11-15
- Date: 2026-11-11, updated 2026-11-15 with access patterns

## Context

The app stores todos, habits, check-ins, journal entries and rich-text pages for each
user. The backend runs on Lambda outside a VPC. The account is on the AWS Free plan, so
the database must cost close to nothing when idle and must not need a NAT Gateway.

The access patterns are listed in `docs/inception/08-dynamodb-table-design.md` (14
patterns, AP1 to AP14).

## Options

### Option A: DynamoDB
- For: no idle cost; 25 read and 25 write units and 25 GB are always free in provisioned
  mode; reachable from Lambda without a VPC; access controlled by IAM; DynamoDB Local
  exists for development; teaches NoSQL data modelling.
- Against: the data model must be designed around access patterns up front; no ad-hoc
  queries or joins; full-text search is hard; items are limited to 400 KB.
- Cost: 0 USD with provisioned capacity inside the free tier.

### Option B: RDS PostgreSQL
- For: familiar relational model; flexible queries; easy full-text search.
- Against: billed by the hour whether used or not; Lambda must join a VPC to reach it,
  and without a NAT Gateway that Lambda then needs paid interface endpoints to reach
  other AWS services; must be destroyed after every session, which loses the data.
- Cost: too high to leave running for six months on credits.

### Option C: Aurora Serverless v2 or Aurora DSQL
- For: relational, and can scale down when idle.
- Against: still needs a VPC for the usual setup (Serverless v2), a minimum capacity
  charge, and newer services may not be available on the Free plan.
- Cost: not reliably zero.

## Decision

DynamoDB, as designed in I-08:

- One table, `productivity-app-data`, with one partition per user (`PK = USER#<userId>`).
- One sparse index, GSI1, for todos by status and due date and pages by last edit.
- Provisioned capacity inside the free tier: table 10/10, GSI1 5/5.
- All 14 access patterns are answered by GetItem or Query. No Scans.

RDS PostgreSQL is practised as a short lab in bolt B11 and destroyed the same day.

## Consequences

- Every query is scoped by the user ID from the verified token, which makes IDOR
  structurally hard.
- Search stays out of scope.
- Page content is limited to 100 KB; the fallback for larger pages is S3.
- Large saves may be throttled under provisioned capacity; the fallback is on-demand mode.
- A new feature that needs a new question must first add an access pattern and check the
  keys answer it.

## What I learned

To be filled in by the owner.
