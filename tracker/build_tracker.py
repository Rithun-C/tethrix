"""Builds tracker/project-tracker.xlsx.

Run once. It refuses to overwrite an existing workbook unless --force is given,
because overwriting would erase your statuses, cost log and learning log.

    python build_tracker.py [--force]

Needs: openpyxl
"""

import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

OUT = Path(__file__).parent / "project-tracker.xlsx"

FONT = Font(name="Arial", size=10)
BOLD = Font(name="Arial", size=10, bold=True)
TITLE = Font(name="Arial", size=12, bold=True)
HEADER_FILL = PatternFill("solid", start_color="E7E6E6")
INPUT_FILL = PatternFill("solid", start_color="FFF2CC")
GREEN = PatternFill("solid", start_color="E2EFDA", end_color="E2EFDA")
YELLOW = PatternFill("solid", start_color="FFF2CC", end_color="FFF2CC")
RED = PatternFill("solid", start_color="F8CBAD", end_color="F8CBAD")
GREY = PatternFill("solid", start_color="EDEDED", end_color="EDEDED")
WRAP = Alignment(wrap_text=True, vertical="top")

LAST = 500  # last row covered by formulas, dropdowns and colouring

D, S, C, O = "Dev", "Security", "Cloud", "Docs"
P, T = "Practical", "Theory"

# (bolt, phase, [(id, task, category, type), ...])
PLAN = [
    ("Scaffold", "Setup", [
        ("S-01", "Build repo scaffold and docs templates", O, P),
        ("S-02", "Build project tracker workbook", O, P),
    ]),
    ("Guardrails", "Week 0", [
        ("G-01", "Root account: MFA, no root keys, alternate contacts", S, P),
        ("G-02", "Record plan type, credit balance and expiry date in Cost Log", C, P),
        ("G-03", "Complete the credit activities (console exception), destroy each", C, P),
        ("G-04", "IAM admin with MFA and short-lived CLI credentials", S, P),
        ("G-05", "AWS CLI profile, region pin, identity check", C, P),
        ("G-06", "Terraform bootstrap: state bucket (versioned, SSE-S3, private, native locking)", C, P),
        ("G-07", "Budgets in Terraform with credit-aware alert thresholds", C, P),
        ("G-08", "Account defaults: S3 Block Public Access, EBS encryption, IMDSv2", S, P),
        ("G-09", "CloudTrail management-events trail with S3 lifecycle", S, P),
        ("G-10", "IAM Access Analyzer", S, P),
        ("G-11", "Prowler baseline scan, log findings", S, P),
        ("G-12", "Runbook: session start/end checklist and 'what is running' sweep", O, P),
        ("G-13", "Runbook: emergency cost stop", O, P),
        ("G-14", "Theory: Free plan mechanics, shared responsibility, IAM fundamentals", O, T),
    ]),
    ("Inception", "Inception", [
        ("I-01", "Vision, scope and cut line", O, P),
        ("I-02", "User stories and acceptance criteria for MVP", O, P),
        ("I-03", "Domain model and API contract outline", D, P),
        ("I-04", "ADR-0001 database choice, with access patterns", C, P),
        ("I-05", "ADR-0002 API edge: Function URL + OAC vs HTTP API", C, P),
        ("I-06", "ADR-0003 auth flow, token header, local dev auth", S, P),
        ("I-07", "ADR-0004 compute packaging: container + Web Adapter vs zip", C, P),
        ("I-08", "DynamoDB single-table design for all four features", D, P),
        ("I-09", "STRIDE threat model v1", S, P),
        ("I-10", "Architecture and data-flow diagrams", O, P),
        ("I-11", "Cost model, lab budget and credit reserve", C, P),
        ("I-12", "Security requirements baseline (OWASP ASVS subset)", S, P),
        ("I-13", "Bolt plan refined, tracker updated", O, P),
        ("I-14", "Theory: Well-Architected pillars; Lambda vs ECS vs EKS", O, T),
    ]),
    ("B1 Foundation", "Construction", [
        ("B1-01", "Git init, GitHub repo, branch protection", D, P),
        ("B1-02", "Install and pin tflint, checkov, Semgrep, Trivy, gitleaks, pip-audit", S, P),
        ("B1-03", "Pre-commit hooks", S, P),
        ("B1-04", "Terraform skeleton: pinned providers, default_tags, backend, module conventions", C, P),
        ("B1-05", "CI workflow with static checks only (no AWS access)", D, P),
        ("B1-06", "Dependency pinning and update policy", S, P),
        ("B1-07", "Makefile task runner", D, P),
        ("B1-08", "Theory: Terraform state, locking, drift, modules", O, T),
        ("B1-09", "Theory: supply-chain security", O, T),
    ]),
    ("B2 Local dev", "Construction", [
        ("B2-01", "FastAPI skeleton: health, settings, structured logs, pytest", D, P),
        ("B2-02", "React + Vite + TS skeleton: routing, API client, tests, lint", D, P),
        ("B2-03", "Dockerfiles: multi-stage, non-root, pinned digests", D, P),
        ("B2-04", "Docker Compose with frontend, backend, DynamoDB Local", D, P),
        ("B2-05", "Local table creation and seed script", D, P),
        ("B2-06", "Image scanning (Trivy) and Dockerfile lint", S, P),
        ("B2-07", "Local Kubernetes lab with kind", C, P),
        ("B2-08", "Theory: container internals, image hardening, EKS", O, T),
    ]),
    ("B3 Walking skeleton", "Construction", [
        ("B3-01", "ECR module: scan on push, lifecycle, immutable tags", C, P),
        ("B3-02", "Lambda module: container + Web Adapter, least-privilege role, log retention", C, P),
        ("B3-03", "DynamoDB table module", C, P),
        ("B3-04", "S3 frontend bucket + CloudFront + OAC", C, P),
        ("B3-05", "CloudFront /api/* to Function URL with OAC, body-hash handling", C, P),
        ("B3-06", "Security headers policy (CSP, HSTS)", S, P),
        ("B3-07", "Negative test: direct Function URL access is denied", S, P),
        ("B3-08", "Manual deploy runbook and smoke test", O, P),
        ("B3-09", "Theory: CloudFront, OAC vs OAI, SigV4", O, T),
        ("B3-10", "Theory: VPC basics, NAT Gateway, why this Lambda is outside a VPC", O, T),
    ]),
    ("B4 Auth", "Construction", [
        ("B4-01", "Cognito user pool and client in Terraform (PKCE, TOTP MFA)", C, P),
        ("B4-02", "FastAPI JWT verification (JWKS cache, issuer, audience, expiry)", S, P),
        ("B4-03", "Frontend sign-up, sign-in, sign-out, token storage decision", D, P),
        ("B4-04", "Authorization layer scoped by user ID, two-user IDOR test harness", S, P),
        ("B4-05", "Local dev auth, with guard against bypass in deployed builds", S, P),
        ("B4-06", "Threat model update: auth", S, P),
        ("B4-07", "Theory: OAuth2/OIDC, JWT pitfalls, user pools vs identity pools", O, T),
    ]),
    ("B5 Todos", "Construction", [
        ("B5-01", "Todos API: CRUD, validation, pagination", D, P),
        ("B5-02", "Todos repository on DynamoDB with tests", D, P),
        ("B5-03", "Todos UI", D, P),
        ("B5-04", "IDOR and input-validation tests", S, P),
        ("B5-05", "Deploy, smoke test, cost log", C, P),
        ("B5-06", "Theory: DynamoDB keys, GSIs, capacity modes", O, T),
    ]),
    ("B6 CI/CD", "Construction", [
        ("B6-01", "GitHub OIDC provider and roles, subject pinned to repo and environment", S, P),
        ("B6-02", "Separate read-only plan role and apply role", S, P),
        ("B6-03", "Workflow: build, scan, push image, plan on pull request", D, P),
        ("B6-04", "Gated apply, frontend sync, CloudFront invalidation", D, P),
        ("B6-05", "All scanner gates enforced in CI", S, P),
        ("B6-06", "Actions pinned by commit SHA, minimal token permissions", S, P),
        ("B6-07", "Rollback runbook", O, P),
        ("B6-08", "Theory: OIDC federation, deployment strategies, AWS Code* services", O, T),
    ]),
    ("B7 Habits", "Construction", [
        ("B7-01", "Habits API: habits, check-ins, streaks, timezones", D, P),
        ("B7-02", "Habits UI", D, P),
        ("B7-03", "Tests including IDOR", S, P),
        ("B7-04", "Deploy and docs", C, P),
    ]),
    ("B8 Journal + Pages", "Construction", [
        ("B8-01", "Journal API and UI", D, P),
        ("B8-02", "Journal data controls: log redaction, encryption ADR", S, P),
        ("B8-03", "KMS lab: one key, key policy, rotation (time-boxed)", C, P),
        ("B8-04", "ADR: TipTap vs BlockNote, packages verified and pinned", D, P),
        ("B8-05", "Pages API: JSON document storage, 400 KB limit strategy", D, P),
        ("B8-06", "Pages UI with editor", D, P),
        ("B8-07", "Stored-XSS defences: schema validation, no raw HTML, CSP, payload tests", S, P),
        ("B8-08", "Deploy and threat model update", S, P),
        ("B8-09", "Theory: KMS envelope encryption, Parameter Store vs Secrets Manager", O, T),
    ]),
    ("B9 Dashboard + export", "Construction", [
        ("B9-01", "Dashboard aggregate API", D, P),
        ("B9-02", "Dashboard UI", D, P),
        ("B9-03", "Full data export", D, P),
        ("B9-04", "Account and data deletion", S, P),
        ("B9-05", "Deploy and docs", C, P),
    ]),
    ("B10 Attachments + reminders", "Construction", [
        ("B10-01", "Attachments bucket: private, SSE-S3, lifecycle, CORS", C, P),
        ("B10-02", "Presigned upload/download API with size, type and per-user key limits", S, P),
        ("B10-03", "Attachment UI", D, P),
        ("B10-04", "Reminders with EventBridge Scheduler and SNS", C, P),
        ("B10-05", "Scheduler role least privilege, dead-letter queue", S, P),
        ("B10-06", "Tests and threat model update", S, P),
        ("B10-07", "Theory: S3 security deep dive, event-driven patterns", O, T),
    ]),
    ("B11 Hardening labs", "Construction", [
        ("B11-01", "WAF lab on CloudFront", S, P),
        ("B11-02", "GuardDuty, Security Hub, Inspector, Config lab", S, P),
        ("B11-03", "VPC lab: subnets, security groups, short-lived EC2 via SSM, gateway endpoint", C, P),
        ("B11-04", "Interface VPC endpoint lab", C, P),
        ("B11-05", "RDS PostgreSQL lab", C, P),
        ("B11-06", "ECS Fargate + ALB lab running the same container", C, P),
        ("B11-07", "IAM tightening: permission boundaries, Access Analyzer policy validation", S, P),
        ("B11-08", "Lambda limits: concurrency cap, timeouts, throttling", C, P),
        ("B11-09", "Theory: Organizations, SCPs, Control Tower", O, T),
        ("B11-10", "Theory: Transit Gateway, Network Firewall, Shield Advanced, multi-region DR", O, T),
    ]),
    ("Operations", "Operations", [
        ("O-01", "CloudWatch dashboard and alarms to SNS", C, P),
        ("O-02", "Logs Insights queries and metric filters", C, P),
        ("O-03", "X-Ray tracing", C, P),
        ("O-04", "CloudTrail investigation practice via CLI", S, P),
        ("O-05", "Prowler rerun, compare to baseline, fix or accept", S, P),
        ("O-06", "OWASP ZAP baseline and authenticated scan of own app", S, P),
        ("O-07", "Incident drill: leaked deny-all access key, postmortem", S, P),
        ("O-08", "Backup and restore drill", C, P),
        ("O-09", "Runbooks finalised", O, P),
        ("O-10", "Final cost review", C, P),
        ("O-11", "Export data, destroy everything, verify zero resources (by 2027-04-30)", C, P),
        ("O-12", "Retrospective", O, P),
        ("O-13", "Theory: incident response lifecycle, RPO/RTO strategies", O, T),
    ]),
]

PHASES = ["Setup", "Week 0", "Inception", "Construction", "Operations"]
STATUSES = ["Not started", "In progress", "Blocked", "Done"]


def header(ws, row, titles, widths):
    for i, (title, width) in enumerate(zip(titles, widths), start=1):
        cell = ws.cell(row=row, column=i, value=title)
        cell.font = BOLD
        cell.fill = HEADER_FILL
        ws.column_dimensions[cell.column_letter].width = width


def dropdown(ws, options, cell_range):
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(cell_range)


def highlight(ws, cell_range, value, fill):
    ws.conditional_formatting.add(
        cell_range, CellIsRule(operator="equal", formula=[f'"{value}"'], fill=fill)
    )


def set_font(ws):
    for row in ws.iter_rows():
        for cell in row:
            if cell.font is None or cell.font.name != "Arial":
                cell.font = FONT


def build_readme(ws):
    lines = [
        ("How to use this workbook", TITLE),
        ("", FONT),
        ("Sheets", BOLD),
        ("Dashboard: read only. Every number is a formula. Do not type here.", FONT),
        ("Tasks: one row per task. Change Status, and fill Start Date, Done Date, Doc Link and Notes.", FONT),
        ("Cost Log: one row for every AWS session. Fill the yellow cells at the top once.", FONT),
        ("Learning Log: one row per study or build session, with hours.", FONT),
        ("", FONT),
        ("Routine", BOLD),
        ("Starting a task: set Status to 'In progress' and enter the Start Date.", FONT),
        ("Finishing a task: set Status to 'Done', enter the Done Date and the path of the doc you wrote.", FONT),
        ("Before an AWS session: note the credit balance from the billing page (Balance before).", FONT),
        ("After an AWS session: destroy costly resources, note the balance (Balance after), answer Yes or No.", FONT),
        ("A red 'No' in the Cost Log means something is still running. Fix it before you stop for the day.", FONT),
        ("The credit balance on the billing page can lag by several hours. Update the row the next day if it changed.", FONT),
        ("", FONT),
        ("Rules", BOLD),
        ("Enter dates as YYYY-MM-DD.", FONT),
        ("Add new tasks at the bottom of the Tasks sheet. Formulas cover rows up to 500.", FONT),
        ("Use the exact Phase and Bolt names already in the sheet, or the Dashboard will not count the task.", FONT),
        ("Do not rename sheets or move columns. The Dashboard formulas depend on them.", FONT),
        ("Close the workbook before committing. Excel lock files (~$...) are ignored by git.", FONT),
        ("Do not re-run build_tracker.py. It rebuilds an empty workbook and would erase your entries.", FONT),
    ]
    for i, (text, font) in enumerate(lines, start=1):
        ws.cell(row=i, column=1, value=text).font = font
    ws.column_dimensions["A"].width = 110


def build_tasks(ws):
    header(
        ws, 1,
        ["ID", "Phase", "Bolt", "Task", "Category", "Type", "Status",
         "Start Date", "Done Date", "Doc Link", "Notes"],
        [8, 13, 26, 72, 10, 10, 13, 12, 12, 30, 40],
    )
    today = date.today()
    row = 2
    for bolt, phase, tasks in PLAN:
        for task_id, task, category, kind in tasks:
            done = phase == "Setup"
            ws.append([
                task_id, phase, bolt, task, category, kind,
                "Done" if done else "Not started",
                today if done else None,
                today if done else None,
            ])
            ws.cell(row=row, column=4).alignment = WRAP
            row += 1
    for r in range(2, LAST + 1):
        ws.cell(row=r, column=8).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=9).number_format = "yyyy-mm-dd"
    dropdown(ws, [D, S, C, O], f"E2:E{LAST}")
    dropdown(ws, [P, T], f"F2:F{LAST}")
    dropdown(ws, STATUSES, f"G2:G{LAST}")
    rng = f"G2:G{LAST}"
    highlight(ws, rng, "Not started", GREY)
    highlight(ws, rng, "In progress", YELLOW)
    highlight(ws, rng, "Blocked", RED)
    highlight(ws, rng, "Done", GREEN)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:K{row - 1}"


def build_cost_log(ws):
    ws["A1"], ws["B1"] = "Starting credits (USD)", 100
    ws["A2"], ws["B2"] = "Bonus credits earned (USD)", 0
    ws["A3"], ws["B3"] = "Account closes on", date(2027, 5, 11)
    ws["C3"] = "Confirm this date on the billing page (task G-02)."
    for r in (1, 2, 3):
        ws.cell(row=r, column=1).font = BOLD
        ws.cell(row=r, column=2).fill = INPUT_FILL
    ws["B1"].number_format = "0.00"
    ws["B2"].number_format = "0.00"
    ws["B3"].number_format = "yyyy-mm-dd"
    header(
        ws, 5,
        ["Date", "Bolt", "Services used", "Balance before", "Balance after",
         "Credits used", "All costly resources destroyed?", "Notes"],
        [26, 22, 40, 15, 15, 13, 30, 50],
    )
    for r in range(6, LAST + 1):
        ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=4).number_format = "0.00"
        ws.cell(row=r, column=5).number_format = "0.00"
        cell = ws.cell(row=r, column=6, value=f'=IF(AND(D{r}<>"",E{r}<>""),D{r}-E{r},"")')
        cell.number_format = "0.00"
    dropdown(ws, ["Yes", "No"], f"G6:G{LAST}")
    highlight(ws, f"G6:G{LAST}", "No", RED)
    ws.freeze_panes = "A6"


def build_learning_log(ws):
    header(
        ws, 1,
        ["Date", "Topic", "Category", "Hours", "Key learning", "Doc Link"],
        [12, 36, 10, 8, 70, 30],
    )
    for r in range(2, LAST + 1):
        ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
        ws.cell(row=r, column=4).number_format = "0.0"
    dropdown(ws, [D, S, C, O], f"C2:C{LAST}")
    ws.freeze_panes = "A2"


def build_dashboard(ws):
    status = f"Tasks!$G$2:$G${LAST}"
    ws["A1"] = "Dashboard"
    ws["A1"].font = TITLE
    ws["A2"] = "Every value on this sheet is a formula. Do not type here."

    rows = [
        ("Total tasks", f"=COUNTA(Tasks!$A$2:$A${LAST})", "0"),
        ("Done", f'=COUNTIF({status},"Done")', "0"),
        ("In progress", f'=COUNTIF({status},"In progress")', "0"),
        ("Blocked", f'=COUNTIF({status},"Blocked")', "0"),
        ("Overall % done", "=IF(B4=0,0,B5/B4)", "0%"),
        ("", None, None),
        ("Total credits (USD)", "='Cost Log'!B1+'Cost Log'!B2", "0.00"),
        ("Credits used (USD)", f"=SUM('Cost Log'!$F$6:$F${LAST})", "0.00"),
        ("Credits remaining (USD)", "=B10-B11", "0.00"),
        ("% of credits used", "=IF(B10=0,0,B11/B10)", "0%"),
        ("Days until account closes", "='Cost Log'!B3-TODAY()", "0"),
        ("Sessions with resources left running", f"=COUNTIF('Cost Log'!$G$6:$G${LAST},\"No\")", "0"),
        ("", None, None),
        ("Total hours learned", f"=SUM('Learning Log'!$D$2:$D${LAST})", "0.0"),
    ]
    for i, (label, formula, fmt) in enumerate(rows, start=4):
        ws.cell(row=i, column=1, value=label).font = BOLD
        if formula:
            ws.cell(row=i, column=2, value=formula).number_format = fmt

    def progress_table(start, title, names, column):
        key = f"Tasks!${column}$2:${column}${LAST}"
        for i, text in enumerate([title, "Tasks", "Done", "% done"], start=1):
            cell = ws.cell(row=start, column=i, value=text)
            cell.font = BOLD
            cell.fill = HEADER_FILL
        for r, name in enumerate(names, start=start + 1):
            ws.cell(row=r, column=1, value=name)
            ws.cell(row=r, column=2, value=f"=COUNTIF({key},A{r})")
            ws.cell(row=r, column=3, value=f'=COUNTIFS({key},A{r},{status},"Done")')
            ws.cell(row=r, column=4, value=f"=IF(B{r}=0,0,C{r}/B{r})").number_format = "0%"
        return start + len(names) + 2

    nxt = progress_table(20, "Phase", PHASES, "B")
    progress_table(nxt, "Bolt", [bolt for bolt, _, _ in PLAN], "C")

    ws.column_dimensions["A"].width = 36
    ws.column_dimensions["B"].width = 12
    ws.column_dimensions["C"].width = 10
    ws.column_dimensions["D"].width = 10


def main():
    if OUT.exists() and "--force" not in sys.argv:
        sys.exit(f"{OUT.name} already exists. Re-running would erase your entries. "
                 "Use --force only if you really want an empty workbook.")
    wb = Workbook()
    readme = wb.active
    readme.title = "Read Me"
    dashboard = wb.create_sheet("Dashboard")
    tasks = wb.create_sheet("Tasks")
    cost = wb.create_sheet("Cost Log")
    learning = wb.create_sheet("Learning Log")

    build_readme(readme)
    build_tasks(tasks)
    build_cost_log(cost)
    build_learning_log(learning)
    build_dashboard(dashboard)
    for ws in wb.worksheets:
        set_font(ws)
    wb.save(OUT)
    print(f"Wrote {OUT} with {sum(len(t) for _, _, t in PLAN)} tasks")


if __name__ == "__main__":
    main()
