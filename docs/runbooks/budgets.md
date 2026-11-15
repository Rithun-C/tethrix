# Runbook: Budgets (import and apply)

Task: G-07. Stack: `infra/bootstrap/`. Code: `budgets.tf`, `imports.tf`.

## Purpose

Bring the console-made `monthly-cost` budget under Terraform, set both budgets to
exclude credits, and add a `daily-cost` budget.

## Prerequisites

- G-06 done (state is in S3)
- Signed in: `aws login --profile admin`

## Steps

1. Create the variables file (git ignores it, because it holds your email):

   ```
   cd infra/bootstrap
   cp terraform.tfvars.example terraform.tfvars
   ```

   Edit `terraform.tfvars` and put your real email in `alert_email`.

2. Plan:

   ```
   export AWS_PROFILE=admin
   terraform plan -out=tfplan
   ```

3. Check the plan before applying:

   - Summary line: `Plan: 1 to import, 1 to add, 1 to change, 0 to destroy.`
     The change count can be 0 if the console budget already matches the code.
   - `aws_budgets_budget.monthly` says "will be imported", followed by the differences
     between the console budget and the code. Expected: tags added, the console's 85%
     alert removed, and the 50% and 80% alerts added. `filter_expression`, `metrics` and
     `billing_view_arn` must NOT change; if they do, stop and ask.
   - `aws_budgets_budget.daily` says "will be created".
   - Nothing in the S3 bucket resources changes.
   - The email shows as `(sensitive value)`. That is expected.

4. Apply:

   ```
   terraform apply tfplan
   rm tfplan
   ```

## Verify

```
terraform plan                       # must say "No changes."
aws budgets describe-budgets --account-id "$(aws sts get-caller-identity --query Account --output text)" \
  --query 'Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,unit:TimeUnit}' \
  --output table
```

The table must show two budgets: `monthly-cost` (MONTHLY) and `daily-cost` (DAILY).

## Lesson from the first plan (2026-11-12)

The first version of the code used the old `cost_types` block. The plan showed it
would remove the console's `filter_expression`, `metrics` and `billing_view_arn`, and
switch to the old format. Nothing was applied. The code was rewritten in the new format
so that it matches what AWS stores. Reading the plan before applying caught this.

## Troubleshooting

- "Cannot import non-existent remote object": the console budget is not named exactly
  `monthly-cost`. Check the name with the `describe-budgets` command above and tell Claude.
- The plan wants to destroy and recreate `monthly`: stop and ask. Some budget settings
  cannot be changed in place.

## How to undo

Budgets cost nothing, so there is no reason to remove them before the end of the project.
To remove one, delete its block from `budgets.tf`, then plan and apply.

## Cost

Budgets without actions are free.
