# Runbook: Account defaults

Task: G-08. Stack: `infra/bootstrap/`. Code: `account_defaults.tf`.

## Purpose

Turn on account-wide safety settings that apply to everything created afterwards.

## Prerequisites

- G-07 done
- Signed in: `aws login --profile admin`

## Steps

```
cd infra/bootstrap
export AWS_PROFILE=admin
terraform plan -out=tfplan
```

Check the plan before applying:

- Summary line: `Plan: 6 to add, 0 to change, 0 to destroy.`
- The 6 resources:
  - `aws_s3_account_public_access_block.this`
  - `aws_ebs_encryption_by_default.this`
  - `aws_ec2_instance_metadata_defaults.this`
  - `aws_ebs_snapshot_block_public_access.this`
  - `aws_ec2_image_block_public_access.this`
  - `aws_iam_account_password_policy.this`
- No changes to the budgets. (`imports.tf` was deleted; the import was already done.)
- No changes to the S3 bucket resources.

If the plan looks right:

```
terraform apply tfplan
rm tfplan
```

## Verify

```
terraform plan                                              # must say "No changes."
aws s3control get-public-access-block --account-id "$(aws sts get-caller-identity --query Account --output text)"
aws ec2 get-ebs-encryption-by-default                       # EbsEncryptionByDefault: true
aws ec2 get-instance-metadata-defaults                      # HttpTokens: required
aws ec2 get-snapshot-block-public-access-state              # State: block-all-sharing
aws ec2 get-image-block-public-access-state                 # ImageBlockPublicAccessState: block-new-sharing
aws iam get-account-password-policy                         # MinimumPasswordLength: 14
```

## Notes

- The password policy applies the next time a password is set. Your current `admin`
  password keeps working. If it is shorter than 14 characters, change it to a stronger one.
- `aws_ec2_image_block_public_access` can take a few minutes to apply. That is normal.

## How to undo

Remove the resource block and apply. The setting goes back to the AWS default. There is
no reason to do this before the end of the project.

## Cost

All free.
