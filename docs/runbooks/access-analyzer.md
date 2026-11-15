# Runbook: IAM Access Analyzer

Task: G-10. Stack: `infra/bootstrap/`. Code: `access_analyzer.tf`.

## Purpose

Create a free external access analyzer that flags anything shared outside the account.

## Prerequisites

- G-09 done
- Signed in: `aws login --profile admin`

## Steps

```
cd infra/bootstrap
export AWS_PROFILE=admin
terraform plan -out=tfplan
```

Check the plan:

- Summary line: `Plan: 1 to add, 0 to change, 0 to destroy.`
- The one resource is `aws_accessanalyzer_analyzer.this` with `type = "ACCOUNT"`.

If the plan looks right:

```
terraform apply tfplan
rm tfplan
```

## Verify

```
terraform plan                       # "No changes."

ANALYZER=$(aws accessanalyzer list-analyzers --type ACCOUNT --query 'analyzers[0].arn' --output text)
echo "${ANALYZER}"

aws accessanalyzer get-analyzer --analyzer-name productivity-app-external-access \
  --query 'analyzer.status'          # "ACTIVE"
```

The first scan takes a few minutes. Then list active findings:

```
aws accessanalyzer list-findings-v2 --analyzer-arn "${ANALYZER}" \
  --filter '{"status": {"eq": ["ACTIVE"]}}' \
  --query 'findings[].{resource:resource,type:resourceType,status:status}' --output table
```

Expected: no findings. Both buckets are private, and the CloudTrail bucket only trusts
the CloudTrail service for our own trail, which does not count as external.

If any finding appears, log it in `docs/security/findings-log.md` and tell Claude.

## Practice: check a deliberately bad policy

`validate-policy` checks a policy before you use it. It is free and needs no analyzer.

1. Create a test policy with two mistakes (outside the repo):

   ```
   cat > /tmp/bad-policy.json <<'EOF'
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "s3:GetObjects",
         "Resource": "*"
       },
       {
         "Effect": "Allow",
         "Action": "iam:PassRole",
         "Resource": "*"
       }
     ]
   }
   EOF
   ```

2. Check it:

   ```
   aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY \
     --policy-document file:///tmp/bad-policy.json \
     --query 'findings[].{type:findingType,issue:issueCode,detail:findingDetails}' --output table
   ```

3. What to look for:

   - An ERROR for `s3:GetObjects`: that action does not exist (the real one is
     `s3:GetObject`). A typo like this silently grants nothing.
   - A SECURITY_WARNING for `iam:PassRole` on `*`: this lets the holder hand any role,
     including admin roles, to a service. It is a classic privilege escalation path.

4. Delete the test file: `rm /tmp/bad-policy.json`

Every IAM policy Claude writes later is checked the same way.

## How to undo

Remove the resource and apply. Not planned before the end of the project.

## Cost

The external access analyzer is free.
