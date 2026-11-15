# productivity-app (working title)

A personal productivity app (todos, habits, journal, pages, dashboard) built to learn AWS,
cloud security, Terraform and containers. It runs entirely inside the AWS Free plan.

Nothing is deployed yet. The app runs locally with `make up` (http://localhost:5173):
see `docs/runbooks/local-dev.md`.

## Where things are

| Path | What it holds |
|---|---|
| `CLAUDE.md` | Project rules, decisions and current status |
| `docs/project-plan.md` | The full plan and schedule |
| `docs/glossary.md` | Plain-language meanings of the terms used here |
| `docs/adr/` | Architecture decision records |
| `docs/threat-model/` | STRIDE threat model |
| `docs/security/findings-log.md` | Security findings and what was done about them |
| `docs/bolts/` | One design doc per bolt |
| `docs/runbooks/` | Step-by-step operating procedures |
| `docs/theory/` | Notes on topics that cannot be practised on the Free plan |
| `docs/journal/` | One short learning entry per session |
| `app/frontend/` | React app (Vite + TypeScript, Node 26) |
| `app/backend/` | FastAPI app (Python 3.12, packages managed with uv) |
| `compose.yaml` | Runs the app on the laptop: `make up` |
| `infra/bootstrap/` | Terraform for state bucket, budgets and account guardrails |
| `infra/modules/` | Reusable Terraform modules |
| `infra/app/` | The app's Terraform stack |
| `infra/labs/` | One folder per time-boxed lab, each with its own state. `kind/` is the local Kubernetes lab |
| `Makefile` | Shortcuts for the checks: `make help` lists them |
| `tools/versions.env` | Every pinned scanner version |
| `.semgrep/` | Our own Semgrep rules and their tests |
| `docs/dependency-policy.md` | Rules for adding and updating dependencies |
| `scripts/sweep.sh` | Read-only "what is running?" check for the end of every session |
| `tracker/` | Task, cost and learning tracker (Excel) |

## Checks

Every change passes the same checks on the laptop and in CI: `make check`. Docker must be
running, because the scanners are pinned Docker images. Set-up steps are in
`docs/runbooks/repo-and-ci.md`.

## Rules in one paragraph

Free plan only. No console work beyond bootstrap and billing checks. All infrastructure in
Terraform. No NAT Gateway. Hourly services are same-day labs. No secrets in the repo.
The full rules are in `CLAUDE.md`.
