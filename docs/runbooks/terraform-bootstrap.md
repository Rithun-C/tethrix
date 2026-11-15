# Runbook: Terraform bootstrap (state bucket)

Task: G-06. Stack: `infra/bootstrap/`.

## Purpose

Create the S3 bucket that holds Terraform state for every stack, then move this stack's
own state into it.

## Why two phases

The bucket that will hold the state has to be created by Terraform too. So:

1. Phase 1 creates the bucket using local state (a file on your laptop, ignored by git).
2. Phase 2 moves that state into the new bucket.

## Prerequisites

- AWS CLI 2.32.0 or later (for `aws login`)
- Terraform 1.15 or later. The S3 backend can use `aws login` credentials only from 1.15,
  and the AWS provider from 6.23.0. We pin 1.15 and 6.71.0.
- You are signed in: `aws login --profile admin`

## Phase 1: create the bucket

```
cd infra/bootstrap
export AWS_PROFILE=admin
aws sts get-caller-identity          # must show user/admin
terraform init
terraform plan -out=tfplan
```

Check the plan before applying:

- It must say `Plan: 7 to add, 0 to change, 0 to destroy.`
- The 7 resources: the bucket, versioning, encryption, public access block, ownership
  controls, bucket policy, lifecycle rule.
- Nothing outside `aws_s3_bucket*` should appear.

If the plan looks right:

```
terraform apply tfplan
terraform output -raw state_bucket_name
```

## Phase 2: move the state into the bucket

1. Create the backend settings file (git ignores it because it contains the account ID):

   ```
   cp backend.hcl.example backend.hcl
   ```

   Edit `backend.hcl` and replace the bucket value with the output from Phase 1.

2. Create `infra/bootstrap/backend.tf` with exactly this content:

   ```
   terraform {
     backend "s3" {}
   }
   ```

   The empty block says "use S3"; the details come from `backend.hcl`. This is called
   partial configuration.

3. Migrate:

   ```
   terraform init -backend-config=backend.hcl -migrate-state
   ```

   Answer `yes` when asked to copy the existing state.

## Verify

```
terraform plan                                   # must say "No changes."
aws s3 ls s3://<bucket-name>/bootstrap/          # must list terraform.tfstate
```

Then delete the local copies. They are no longer used, and they hold state on your laptop:

```
rm terraform.tfstate terraform.tfstate.backup tfplan
```

## Troubleshooting

- "No valid credential sources found": your `aws login` session expired. Run
  `aws login --profile admin` again and check `AWS_PROFILE=admin` is set.
- "BucketAlreadyExists": someone else owns that name. Should not happen, because the
  name contains your account ID.
- Plan wants to destroy the bucket: stop. `prevent_destroy` will block it anyway. Ask
  before doing anything.

## How to undo

The bucket has `prevent_destroy = true` on purpose. It is removed only at the very end of
the project (task O-11), after every other stack has been destroyed.

## Cost

The state file is a few kilobytes. Expected cost: 0.00 USD a month.
