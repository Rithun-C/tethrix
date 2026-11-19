# productivity-app (working title)

A learning project. One real application built end to end to learn AWS, cloud security,
Terraform, AWS CLI, cloud development and containers.

The owner learns by doing. Always explain WHY, not just WHAT. If something cannot be
practised, document the theory instead.

Keep every doc and the tracker plain and simple. No decoration, no badges, no emojis.
The goal is learning, not presentation.

## The application

A personal Notion-style productivity app: todos, habit tracker, journal, rich-text pages
and a dashboard.

- Frontend: React (Vite + TypeScript)
- Backend: FastAPI (Python), packages managed with uv
- MVP order: Todos -> Habits -> Journal -> Pages -> Dashboard + data export
- In scope if time allows: attachments, reminders
- Out of scope: search, sharing

## Hard constraints (never break these)

1. AWS Free plan only. The account was created on 2026-11-09 and closes on 2027-05-11,
   or earlier if credits run out. Protect credits.
2. Never exceed the credit budget. Never use a service that is not available on the Free
   plan. If a service is unavailable or too costly, document the theory instead.
3. No AWS console work. Everything goes through AWS CLI and Terraform. Console is allowed
   only for one-time bootstrap (root MFA, first IAM admin), the Week 0 credit activities,
   and read-only billing checks.
4. All infrastructure in Terraform. No click-ops, no untracked CLI-created resources.
5. Never use AWS Organizations or Control Tower. Joining either upgrades the account to
   the Paid plan permanently.
6. Every step is documented.

## Cost rules

- No NAT Gateway, ever. Every public IPv4 address and Elastic IP costs money.
- Hourly services (ALB, EKS, RDS, ECS Fargate, WAF, GuardDuty, Inspector, Security Hub,
  Config, interface VPC endpoints) are short time-boxed labs only, destroyed the same day.
- Every lab needs, before it starts: a check that the service is available on the Free
  plan, a cost estimate, and the owner's approval. Labs live in `infra/labs/` with their
  own state so destroying a lab cannot touch the app.
- Stop all labs when remaining credits fall below the reserve set in the cost model
  (50 USD, set in I-11).
- Prefer SSE-S3 over KMS keys, and Parameter Store SecureString over Secrets Manager.
- Never script Cost Explorer API calls.
- Every CloudWatch log group gets a retention period.
- Cognito: no Plus tier, no SMS MFA (use TOTP). CloudTrail: management events only.
- `default_tags` on the provider. One region: us-east-1.
- Destroy costly resources at the end of every session and record it in the Cost Log.

## Architecture (proposed, confirmed through ADRs)

- Frontend: React build on S3 + CloudFront at `tethrix.satrix.in` (ADR-0006)
- Backend: FastAPI in a container on Lambda, using AWS Lambda Web Adapter
- API: CloudFront `/api/*` -> Lambda Function URL locked with Origin Access Control (OAC)
  - OAC replaces the `Authorization` header, so the JWT travels in a custom header.
  - POST/PUT need the body SHA-256 in `x-amz-content-sha256`.
- Auth: Cognito user pool. FastAPI verifies JWTs.
- Database: DynamoDB proposed (ADR-0001). RDS PostgreSQL only as a short lab.
- Files: S3 presigned URLs. Reminders: EventBridge Scheduler + SNS.
- Local dev: Docker Compose with React, FastAPI and DynamoDB Local.
- CI/CD: GitHub Actions with OIDC, no long-lived AWS keys. Public repo.
- Observability: CloudTrail, CloudWatch, X-Ray.

Theory only: Organizations, SCPs, Control Tower, EKS (Kubernetes practised locally with
kind), NAT Gateway, Transit Gateway, Network Firewall, Shield Advanced, multi-region DR.

## How we work

Three phases: Inception -> Construction -> Operations. Construction is done in short
"bolts".

- Claude drafts, the owner approves at every gate. Never move to the next phase or bolt
  without explicit approval.
- Each bolt: Claude proposes a design -> owner approves -> Claude writes code, tests and
  Terraform -> scanners run -> owner reviews -> owner deploys -> owner destroys costly
  resources -> docs updated.

The owner is new to these terms. When a new term comes up, explain it in plain language
and add it to `docs/glossary.md`.

Explain new or unfamiliar concepts visually as well: a Mermaid diagram (flowchart or
sequence). Durable diagrams live in the repo docs as Mermaid; bigger ones can also be
published as a private artifact page. Keep visuals plain.

The full plan and schedule are in `docs/project-plan.md`. Tasks are tracked in
`tracker/project-tracker.xlsx`.

## Security rules for Claude's work

- Claude has no AWS credentials. Claude runs `terraform fmt`, `terraform validate`, tflint
  and checkov. The owner runs `plan`, `apply` and `destroy`.
- Never put secrets, keys, tokens, the AWS account ID or the owner's email in code, docs,
  prompts or commits. The repo is public.
- Treat IAM policies Claude writes as untrusted: no `*` unless an ADR justifies it.
- Claude's code passes the same gates as the owner's: tflint, checkov, Semgrep, Trivy,
  gitleaks, pip-audit, npm audit.
- Verify every suggested dependency exists and is the real package. Pin versions.
- App-specific risks to check in every bolt:
  - IDOR: user A reading user B's data
  - Stored XSS through the rich-text editor
  - Journal entries are sensitive personal data
  - A local-dev auth bypass must never work in a deployed build

## Definition of Done (every bolt)

- [ ] Code, tests and Terraform written, and all scanners pass
- [ ] ADRs written or updated for decisions made
- [ ] Threat model updated
- [ ] Findings logged in `docs/security/findings-log.md`
- [ ] Runbooks updated
- [ ] Cost Log entry added, costly resources destroyed
- [ ] Journal entry written
- [ ] Tracker statuses updated
- [ ] "Decisions", "Open decisions" and "Current status" below updated

## Decisions

| Date | Decision |
|---|---|
| 2026-11-11 | Region is us-east-1 |
| 2026-11-11 | GitHub repo is public |
| 2026-11-11 | No custom domain; use the default CloudFront domain (replaced 2026-11-20) |
| 2026-11-11 | Claude gets no AWS credentials; static checks only |
| 2026-11-11 | At the end: export data, destroy everything, let the account close |
| 2026-11-11 | The AWS Labs aidlc-workflows tool is not used; the phase/bolt process above is |
| 2026-11-11 | Human admin is IAM user `admin` with MFA and `aws login`, no access keys (ADR-0005) |
| 2026-11-15 | No public sign-up: the admin creates user accounts (I-01) |
| 2026-11-15 | Journal: one entry per day (I-01) |
| 2026-11-15 | Database: DynamoDB single table, provisioned capacity in the free tier (ADR-0001) |
| 2026-11-15 | API edge: CloudFront to Lambda function URL with OAC; fallback HTTP API (ADR-0002) |
| 2026-11-15 | Auth: Cognito Lite, hosted sign-in with PKCE, token in `X-Auth-Token`, profile check per request (ADR-0003) |
| 2026-11-15 | Backend: container image in ECR with Lambda Web Adapter, arm64 (ADR-0004) |
| 2026-11-15 | Credit reserve 50 USD (labs stop below it), lab budget 40 USD in total (I-11) |
| 2026-11-15 | Scanners run as Docker images pinned by digest in `tools/versions.env`; CI runs the same `make` targets (B1) |
| 2026-11-15 | The app's Terraform stack is `infra/app/`. Licence: MIT (B1) |
| 2026-11-15 | Backend Python packages are managed with uv (`pyproject.toml` + `uv.lock`), not pip. pip-audit stays as the scanner |
| 2026-11-15 | Python 3.12 for the backend; Node 26 (latest LTS) for the frontend (B2) |
| 2026-11-15 | App tests and linters run inside the dev containers, on the laptop and in CI. FastAPI `/docs` is off everywhere. Logging uses Python's own `logging` (B2) |
| 2026-11-20 | B3 design approved with all recommendations: temporary `POST /api/v1/echo` until B5, CloudFront Function for React routes, CloudFront access logs off, DynamoDB PITR on, first apply with `-target`, ECR keeps 3 images, three pull requests |
| 2026-11-20 | The app's domain is `tethrix.satrix.in`, a subdomain of the owner's domain (ADR-0006). Only the subdomain is used by this project |

## Open decisions

| Topic | Where it gets decided |
|---|---|
| Editor library: TipTap vs BlockNote | ADR in bolt B8 |
| Journal encryption: SSE vs KMS key vs client-side | ADR in bolt B8 |
| App name | Any time |
| DNS for `tethrix.satrix.in`: Route 53 subdomain zone or records by hand | ADR-0006, before B3 pull request 2 |

## Current status

- 2026-11-11: Scaffold and tracker built. Nothing deployed. No git repo yet (task B1-01).
- 2026-11-11: Week 0 started. G-01 (root account lockdown) done.
- 2026-11-11: G-02 done. Confirmed: Free plan, 100 USD credits, plan ends 2027-05-11.
- 2026-11-11: G-03 done. All five credit activities complete, credits now 200 USD.
  Budget `monthly-cost` kept, to be imported into Terraform in G-07. All other activity
  resources deleted. (Activation was briefly blocked by a name verification mismatch,
  now fixed.)
- 2026-11-11: G-04 and G-05 done. IAM user `admin` (MFA, no access keys, ADR-0005),
  CLI profile `admin` in us-east-1 using `aws login`. Session sweep for G-03 confirmed clean.
- 2026-11-12: G-06 code written in `infra/bootstrap/` (AWS provider 6.71.0). fmt, validate
  and checkov pass (26 passed, 4 skipped with reasons).
- 2026-11-12: G-06 done. State bucket applied, bootstrap state migrated to S3.
  The owner had never used Terraform; `docs/theory/terraform-basics.md` explains it.
- 2026-11-12: G-07 code written: `budgets.tf` (monthly-cost 10 USD imported, daily-cost
  1 USD new, both exclude credits), `imports.tf`. fmt, validate, checkov pass.
  First plan caught a format mismatch (old `cost_types` vs the console's
  `filter_expression`); code rewritten before apply.
- 2026-11-12: G-07 done. Both budgets applied and verified, plan shows no changes.
- 2026-11-12: G-08 code written in `account_defaults.tf` (S3 BPA, EBS encryption, IMDSv2,
  snapshot and AMI public sharing blocked, IAM password policy). `imports.tf` deleted.
  fmt, validate, checkov pass.
- 2026-11-12: G-08 done. Applied and verified.
- 2026-11-12: G-09 code written in `cloudtrail.tf` (logs bucket + multi-region trail,
  management events only, log file validation, 180-day retention). fmt, validate,
  checkov pass.
- 2026-11-12: G-09 done. Trail applied, log files confirmed in the bucket.
- 2026-11-12: G-09 log validation passed (1/1 digest, 7/7 logs valid).
- 2026-11-12: G-10 code written in `access_analyzer.tf` (external access analyzer, ACCOUNT
  scope).
- 2026-11-12: G-10 done. Analyzer ACTIVE, 0 findings. validate-policy practice done.
- 2026-11-12: G-11 code written: `iam_audit_role.tf` (role `security-audit`,
  SecurityAudit + ViewOnlyAccess, assumable only by `admin`). Prowler runs in Docker,
  image `prowlercloud/prowler:5.46.0` pinned by digest. Reports in `~/prowler-output/`,
  never in the repo.
- 2026-11-12: G-11 done. Baseline: 74 pass, 64 fail, 5 manual. Logged as F-001 to F-012
  in `docs/security/findings-log.md`. F-001 (G-03 leftovers) fixed and rechecked.
  Open: F-004 (confirm security contact), F-008 (alarms; owner chose to keep it as
  theory for now, revisit in O-01).
- 2026-11-12: G-12 (`session-checklist.md` + `scripts/sweep.sh`), G-13
  (`emergency-cost-stop.md`) and G-14 (`docs/theory/free-plan-shared-responsibility-iam.md`)
  written. First real sweep clean; two script bugs fixed (blank error text, us-east-1
  repeated in the all-regions loop).
- 2026-11-12: Week 0 complete (G-01 to G-14 done). Credits: 200 USD.
- To check before bolt B11-02: whether GuardDuty, Security Hub and Inspector are
  available on the Free plan (the first sweep returned errors for all three). If not,
  the lab becomes theory only.
- 2026-11-15: Inception started. Inception docs live in `docs/inception/`.
  I-01 approved (admin-only sign-up, one journal entry per day, nothing added to MVP).
  I-02 approved (25 stories; session 1 h idle; journal 20,000 chars).
  I-03 approved (24 endpoints).
  I-04 and I-08 approved: ADR-0001 Accepted (DynamoDB, single table, provisioned).
  I-05, I-06, I-07 drafted: ADR-0002 (function URL + OAC), ADR-0003 (Cognito hosted
  sign-in + PKCE, `X-Auth-Token`, local signed tokens), ADR-0004 (container + Web
  Adapter, arm64). All three Accepted.
- 2026-11-15: I-10 approved: `10-architecture-diagrams.md` (6 Mermaid diagrams), also
  viewable as a private artifact page: https://claude.ai/artifact/CBHZiLc5RJZ3XxEkahCAbP
- 2026-11-15: I-09 drafted (`docs/threat-model/threat-model.md`, 27 threats: 11 High,
  4 done in Week 0, 2 accepted) and I-12 drafted (`docs/inception/12-security-requirements.md`,
  SR-01 to SR-83 from an OWASP ASVS 5.0 subset). Both approved the same day.
- 2026-11-15: I-11 drafted (`docs/inception/11-cost-model.md`): reserve 50 USD, lab
  budget 40 USD, app under 0.50 USD a month, labs estimated about 8 USD. Approved.
- 2026-11-15: I-13 drafted (`docs/inception/13-bolt-plan.md`: 3 new tasks, 5 reworded,
  start B1 early) and I-14 drafted (`docs/theory/well-architected-and-compute.md`).
  Both approved; tracker updated (B1-10, B1-11, B4-08 added).
- 2026-11-15: Inception closed (I-01 to I-14 done). Construction started: bolt B1
  Foundation.
- 2026-11-15: B1 design approved (Docker-pinned scanners, `infra/envs/lab/` renamed to
  `infra/app/`, MIT licence). All B1 files written; every check passes (`make gitleaks` needs the git repo, so the
  secret scan was run on staged files in a scratch copy; build notes in
  `docs/bolts/B1-foundation.md` section 8; accepted finding F-013).
- 2026-11-15: B1 done and approved. Public GitHub repo created and pushed, first CI run
  green, security features on, ruleset on `main` (pull request + `all-checks`), hooks
  installed, gates proven with a refused direct push and a blocked test pull request.
  From now on every change goes through a branch and a pull request.
- 2026-11-15: Bolt B2 (local dev) design approved (`docs/bolts/B2-local-dev.md`), with
  Python 3.12 and Node 26 instead of the recommended versions. Work is split into three
  pull requests: (1) backend, database, Compose; (2) frontend; (3) kind lab and theory.
- 2026-11-15: B2 pull request 1 written on branch `b2/backend`: FastAPI skeleton, backend
  Dockerfile, `compose.yaml`, local table and seed data, pip-audit, hadolint and image
  scan in CI. `make check` passes; `make up` answers on localhost:8080. Accepted finding
  F-015 (zlib in the base image, until 2026-12-15). Build notes in
  `docs/bolts/B2-local-dev.md` section 9. Merged.
- 2026-11-15: B2 pull request 2 written on branch `b2/frontend`: React skeleton (Vite,
  TypeScript 6.0.3 because the linter does not accept 7 yet, React Router), frontend
  Dockerfile (`dev`, `build`, `static`), `frontend` service in Compose, npm audit and
  frontend image scan in CI. `make check` passes; `make up` serves
  http://localhost:5173 with `/api` proxied to the backend. Accepted findings F-017
  (musl in the nginx base image, until 2026-12-15) and F-018 (minimatch in lint tools).
  Build notes in `docs/bolts/B2-local-dev.md` section 10. Merged.
- 2026-11-15: B2 pull request 3 written on branch `b2/kind-lab`: kind lab
  (`infra/labs/kind/`: cluster config, 6 manifests, README with 11 steps), theory note
  `docs/theory/containers-and-eks.md`, checkov now scans Kubernetes manifests. The lab
  passes the scanners but has NOT been run on a cluster (kind could not be installed in
  Claude's session); the owner's run is the first real test. Build notes in
  `docs/bolts/B2-local-dev.md` section 11. To close B2: owner merges, installs kind,
  does the lab, writes the journal entry, then approves. B3 does not start before that.
- 2026-11-16: Pull request 3 merged. The owner did the kind lab (kind v0.33.0): every
  step behaved as described, cluster deleted. B2-07 done. Still open before B2 closes:
  owner's review of the theory note (B2-08), journal entry, and the owner's approval.
- 2026-11-16: B2 done and approved by the owner. Carried over as owner tasks, to finish
  before B3 starts: read `docs/theory/containers-and-eks.md`, redo the lab answers
  (section 6 of `infra/labs/kind/README.md`), write the B1 and B2 journal entries.
  Next: bolt B3, starting with a design proposal. Not started.
- 2026-11-20: Owner allowed B3 to start while those B2 tasks are finished. B3 design
  (`docs/bolts/B3-walking-skeleton.md`) approved with all recommendations and the
  custom domain `tethrix.satrix.in` (ADR-0006, Proposed: DNS hosting to confirm).
  Pull request 1 (app changes, no AWS) started on branch `b3/app`.
- Local note: this laptop's network needs `BUILD_NETWORK := host` in `local.mk` (git
  ignored) for image builds; see `docs/runbooks/local-dev.md`, "Problems".
