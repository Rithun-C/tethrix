# Runbook: Session start and end checklist

Task: G-12. Script: `scripts/sweep.sh`.

## Purpose

Make every AWS session start safely and end with nothing costly left running. On the Free
plan, a forgotten resource does not create a bill; it burns credits, and running out of
credits closes the account.

## Start of session

1. Sign in and check who you are:

   ```
   aws login --profile admin
   export AWS_PROFILE=admin
   aws sts get-caller-identity --query Arn --output text     # must end in user/admin
   ```

2. Check your email for AWS Budgets alerts since the last session. An unexpected alert
   means: stop and follow `emergency-cost-stop.md`.

3. Note the credit balance from the Billing console (read-only). It goes in the Cost Log
   as "Balance before".

4. Run the sweep. It must match "Expected items" below, so you know you start clean:

   ```
   bash scripts/sweep.sh
   ```

5. If this session includes a lab with an hourly service, all three must be true before
   starting:
   - The service is available on the Free plan (checked, not assumed)
   - The cost estimate is written in the bolt design
   - The lab was approved

   Set a timer for the planned time box.

## End of session

1. Destroy every lab stack used today:

   ```
   cd infra/labs/<lab-name>
   terraform destroy
   ```

   Read the destroy plan before typing `yes`. It must list only the lab's resources.

2. Run the sweep, including all regions:

   ```
   bash scripts/sweep.sh --all
   ```

   Every line must be OK, or listed under "Expected items" below. Anything else: delete it
   now, or ask Claude if you are not sure what it is.

3. Fill in the tracker:
   - Cost Log: one row. Balance after (may lag a few hours; update it the next day if it
     changes). "All costly resources destroyed?" = Yes only if step 2 was clean.
   - Tasks: statuses and dates.
   - Learning Log: hours and the key learning.

4. Write the journal entry: copy `docs/journal/TEMPLATE.md` to `docs/journal/YYYY-MM-DD.md`.

5. Sign out:

   ```
   aws logout
   ```

## Expected items

These are permanent and show as CHECK in the sweep. That is fine.

| Sweep line | Expected value | Why it exists |
|---|---|---|
| S3 buckets | `productivity-app-tfstate-...`, `productivity-app-cloudtrail-...` | G-06, G-09 |
| IAM roles (not AWS service-linked) | `security-audit` | G-11 |
| IAM users | `admin` | G-04 |

Update this table whenever a bolt adds a permanent resource (for example the app's
Lambda function and DynamoDB table from B3).

Not shown by the sweep because they are free and permanent: budgets, the CloudTrail
trail, the Access Analyzer, account defaults.

## Troubleshooting

- "Credentials were refreshed, but the refreshed credentials are still expired" or
  "ExpiredToken": the `aws login` session ended (it lasts about 12 hours). Run:

  ```
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
  aws login --profile admin
  ```

  The `unset` matters: leftover `AWS_*` variables (for example from a Prowler run) take
  priority over the profile.
- Still failing: check the Mac clock is set automatically. AWS rejects requests from a
  clock that is off by more than a few minutes.

## Why each sweep section exists

- Hourly-billed: the resources that burn credits fastest. NAT gateways, load balancers,
  RDS, EKS and the detection services (GuardDuty, Security Hub, Config, Inspector) cost
  money every hour they exist, even with no traffic.
- Public IPv4: every public IPv4 address costs about 0.005 USD an hour.
- Storage: disks, snapshots and keys cost per month and survive after the server is gone.
- Side resources: console wizards create IAM roles, policies and log groups that are easy
  to miss. Finding F-001 was exactly this.
- Other regions (`--all`): you never use them, so anything there is either a mistake or
  a sign of compromise.

## Cost

The sweep is free. It only makes read-only calls and never calls Cost Explorer.
