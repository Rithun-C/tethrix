# Runbooks

A runbook is a step-by-step procedure that can be followed without thinking, including
at the end of a long session.

Each runbook has: purpose, when to use it, prerequisites, numbered steps with the exact
commands, how to verify it worked, and how to undo it.

## Written

| Runbook | Task |
|---|---|
| [Terraform bootstrap (state bucket)](terraform-bootstrap.md) | G-06 |
| [Budgets (import and apply)](budgets.md) | G-07 |
| [Account defaults](account-defaults.md) | G-08 |
| [CloudTrail](cloudtrail.md) | G-09 |
| [IAM Access Analyzer](access-analyzer.md) | G-10 |
| [Prowler security scan](prowler.md) | G-11, O-05 |
| [Session start and end checklist](session-checklist.md), with `scripts/sweep.sh` | G-12 |
| [Emergency cost stop](emergency-cost-stop.md) | G-13 |
| [Git repo, GitHub settings and CI](repo-and-ci.md) | B1-01, B1-03, B1-05 |
| [Local development](local-dev.md) | B2 |
| Kubernetes lab with kind: `infra/labs/kind/README.md` (a lab, kept with its files) | B2-07 |
| [Manual deploy and smoke test](deploy-manual.md) | B3-08 |
| [User accounts](user-accounts.md) | B4-08 |

## Planned runbooks

| Runbook | Written in |
|---|---|
| Rollback | B6 |
| Backup and restore | Operations |
| Leaked access key response | Operations |
| Final export and destroy | Operations |
