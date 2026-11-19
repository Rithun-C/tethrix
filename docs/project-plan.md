# Project plan

Last updated: 2026-11-11

## Goal

Learn AWS, cloud security, Terraform, AWS CLI, cloud development and containers by
building one application end to end, inside the AWS Free plan.

## Fixed facts

- AWS account created 2026-11-09. It closes on 2027-05-11 (confirmed on the billing
  page in task G-02), or earlier if credits run out.
- Credits: 100 USD now, up to 100 USD more from the Week 0 activities.
- Time available: 20 to 25 hours a week.
- Region: us-east-1. Public GitHub repo. Domain `tethrix.satrix.in` (ADR-0006; until 2026-11-20 the plan was no custom domain).
- End of project: export data, destroy everything, let the account close.
- Hard deadline for the final destroy (task O-11): 2027-04-30.

## Architecture

```
Browser
  |
CloudFront (default domain)
  |-- /*      -> S3 bucket (React build), private, read through OAC
  |-- /api/*  -> Lambda Function URL (AWS_IAM auth), reached only through OAC
                   |
                 Lambda (container image: FastAPI + Lambda Web Adapter)
                   |-- DynamoDB (app data)
                   |-- S3 (attachments, presigned URLs)
                   |-- EventBridge Scheduler -> SNS (reminders)

Cognito user pool issues JWTs. FastAPI verifies them on every request.
```

Why this shape:

- Everything is pay-per-request, so the idle cost is close to zero.
- Lambda is not in a VPC, so there is no need for a NAT Gateway or paid VPC endpoints.
- The container image gives real Docker practice without paying for ECS or EKS.

Known quirks to design for:

- OAC signs requests and replaces the `Authorization` header. The JWT must travel in a
  custom header.
- POST and PUT through OAC need the SHA-256 of the body in `x-amz-content-sha256`.
- A DynamoDB item is limited to 400 KB. Long pages need chunking or S3 storage.
- Cognito has no official local emulator. Local dev auth needs a deliberate design.

## Cost approach

- The always-on stack should cost under 2 USD a month in credits.
- Most spending comes from hourly labs. Each lab needs an availability check, a cost
  estimate and approval before it starts, and is destroyed the same day.
- A lab budget and a credit reserve are set in Inception (task I-11).
- Budgets alerts lag by hours. They are a warning, not a safety switch. The session-end
  checklist is the real control.
- On the Free plan, running out of credits closes the account. It does not create a bill.

## Schedule

| Week | Dates | Phase / bolt | Outcome |
|---|---|---|---|
| 0 | 2026-11-11 to 11-17 | Guardrails | Account locked down, budgets, state bucket, CloudTrail |
| 1-2 | 11-15 (done early) | Inception | Scope, stories, ADRs, data model, threat model, cost model |
| 2-3 | 11-16 to 12-08 | B1 Foundation | Repo, scanners, pre-commit, Terraform skeleton, static CI |
| 4 | 12-09 to 12-15 | B2 Local dev | Both apps running in Docker Compose with DynamoDB Local |
| 5-6 | 12-16 to 12-29 | B3 Walking skeleton | "Hello world" deployed through CloudFront, OAC and Lambda |
| 7-8 | 12-30 to 2027-01-12 | B4 Auth | Cognito sign-in, JWT checks, per-user authorization |
| 9-10 | 01-13 to 01-26 | B5 Todos | First real feature deployed |
| 11 | 01-27 to 02-02 | B6 CI/CD | OIDC pipeline with gated apply |
| 12 | 02-03 to 02-09 | B7 Habits | Habit tracker deployed |
| 13-15 | 02-10 to 03-02 | B8 Journal + Pages | Journal and rich-text pages, XSS defences |
| 16 | 03-03 to 03-09 | B9 Dashboard + export | Dashboard, data export, data deletion |
| 17-18 | 03-10 to 03-23 | B10 Attachments + reminders | S3 uploads, scheduled reminders |
| 19 | 03-24 to 03-30 | B11 Hardening labs | WAF, detection services, VPC, RDS, ECS labs |
| 20-23 | 03-31 to 04-27 | Operations | Monitoring, Prowler, ZAP, incident drill, retrospective |
| - | 04-28 to 04-30 | Buffer | Final export and destroy |

Inception finished two weeks early (I-13). B1 starts at once; later end dates stay the
same, so the gained time is buffer.

If the schedule slips, cut in this order: B10, then the RDS and ECS labs in B11 (they
become theory notes).

## How each bolt runs

1. Claude proposes a design. The owner approves.
2. Claude writes code, tests and Terraform.
3. Scanners run: tflint, checkov, Semgrep, Trivy, gitleaks, pip-audit, npm audit.
4. The owner reviews, then runs `terraform plan` and `apply`.
5. The owner destroys costly resources at the end of the session.
6. Docs are updated against the Definition of Done in `CLAUDE.md`.

Nothing moves to the next bolt without the owner's explicit approval.

## Tasks

The task list lives in `tracker/project-tracker.xlsx`, sheet "Tasks". It is the single
source of truth for task status.

## Risks

| Risk | What we do about it |
|---|---|
| Credits run out and the account closes early | Same-day destroy rule, Cost Log every session, lab approval, credit reserve |
| A forgotten resource burns credits | Session-end sweep runbook (G-12), labs in separate Terraform state |
| The OAC + Function URL path proves awkward | Deployed early in B3 before any feature depends on it; ADR-0002 keeps HTTP API as a fallback |
| Schedule slips | Cut order above; hard destroy deadline of 2027-04-30 |
| A secret lands in the public repo | gitleaks in pre-commit and CI before the first push |
| A lab service is not available on the Free plan | Check first; write theory notes instead |
