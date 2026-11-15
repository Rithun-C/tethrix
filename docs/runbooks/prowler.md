# Runbook: Prowler security scan

Tasks: G-11 (baseline), O-05 (rerun). Stack: `infra/bootstrap/`. Code: `iam_audit_role.tf`.

## Purpose

Scan the account with Prowler using a read-only role, keep the report outside the repo,
and log the results in `docs/security/findings-log.md`.

## Prerequisites

- G-10 done
- Docker Desktop running
- Signed in: `aws login --profile admin`

## Part 1: create the read-only role (once)

```
cd infra/bootstrap
export AWS_PROFILE=admin
terraform plan -out=tfplan
```

Check the plan:

- Summary line: `Plan: 3 to add, 0 to change, 0 to destroy.`
- `aws_iam_role.security_audit`, plus two `aws_iam_role_policy_attachment` resources for
  `SecurityAudit` and `ViewOnlyAccess`.
- In the trust policy, the only principal is `...:user/admin`.

Apply and print the role ARN:

```
terraform apply tfplan
rm tfplan
terraform output -raw security_audit_role_arn
```

## Part 2: add the audit profile (once)

Open `~/.aws/config` in a text editor and add this at the end. Replace the role ARN with
the output from Part 1:

```
[profile audit]
role_arn = arn:aws:iam::ACCOUNT_ID:role/security-audit
source_profile = admin
region = us-east-1
duration_seconds = 3600
```

What this means: when you use `--profile audit`, the CLI takes your `admin` credentials,
calls `sts:AssumeRole` on `security-audit`, and uses the role's temporary credentials.

Check it:

```
aws sts get-caller-identity --profile audit
```

The `Arn` must contain `assumed-role/security-audit/`. If it shows an error instead, see
Troubleshooting.

Check the role's trust policy with Access Analyzer (our rule: every IAM policy is validated):

```
aws iam get-role --role-name security-audit --profile admin \
  --query 'Role.AssumeRolePolicyDocument' > /tmp/trust.json
aws accessanalyzer validate-policy --profile admin \
  --policy-type RESOURCE_POLICY \
  --validate-policy-resource-type AWS::IAM::AssumeRolePolicyDocument \
  --policy-document file:///tmp/trust.json --query 'findings' --output json
rm /tmp/trust.json
```

Expected: `[]` (no findings).

## Part 3: run the scan

```
mkdir -p ~/prowler-output

# Put the audit role's temporary credentials into this terminal only
eval "$(aws configure export-credentials --profile audit --format env)"

docker run --rm \
  -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_SESSION_TOKEN \
  -v "$HOME/prowler-output:/home/prowler/output" \
  prowlercloud/prowler:5.46.0@sha256:33b8bac58779a0ed292f6c1f40f685796e681a0a2dcc26984637f71f2b052e8e \
  aws --region us-east-1 \
  --output-directory /home/prowler/output \
  --output-filename baseline-2026-11-12

# Remove the credentials from this terminal
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN
```

What each part does:

- `eval "$(aws configure export-credentials ...)"` sets three environment variables
  holding the role's temporary credentials.
- `-e AWS_ACCESS_KEY_ID ...` passes those variables into the container. Nothing is
  written to disk.
- `-v` connects `~/prowler-output` on your Mac to the container's output folder, so the
  report survives after the container exits.
- The image is pinned by tag and digest, so the exact same Prowler runs every time.
- `--rm` deletes the container when it finishes.

The scan takes about 5 to 15 minutes. At the end Prowler prints a summary table.

## Part 4: results

The reports are in `~/prowler-output/`: an HTML file to open in a browser, plus CSV and
JSON. They contain your account ID. Never copy them into the repo.

Tell Claude the scan finished. Claude reads the CSV and drafts entries for
`docs/security/findings-log.md`, each with a decision: fix now, fix in a later bolt, or
accept with a reason.

## Troubleshooting

- `get-caller-identity --profile audit` fails with a credentials error: the CLI may not
  use `aws login` credentials as a `source_profile`. Tell Claude; the fallback is to call
  `aws sts assume-role` directly.
- "Cannot connect to the Docker daemon": start Docker Desktop.
- The scan stops with "ExpiredToken": it ran longer than an hour. Run the `eval` line
  again and restart the scan.
- Many "AccessDenied" lines for one service: that service may not be available on the
  Free plan. Note it; it is not a failure of your setup.

## Cost

Free. Prowler only reads settings. Prowler 5.46.0 has no Cost Explorer module.
