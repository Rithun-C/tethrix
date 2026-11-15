# infra/app

The Terraform stack for the application itself. It has no resources yet; the first ones
(ECR, Lambda, CloudFront) arrive in bolt B3.

| File | What it holds |
|---|---|
| `versions.tf` | Terraform and provider versions |
| `backend.tf` | State location (the S3 bucket from `infra/bootstrap`) |
| `backend.hcl.example` | Template for `backend.hcl`, which holds the bucket name |
| `providers.tf` | Region and default tags |
| `variables.tf` | Inputs |

## First use (owner, in B3)

```sh
cp backend.hcl.example backend.hcl   # then replace ACCOUNT_ID
AWS_PROFILE=admin terraform init -backend-config=backend.hcl
AWS_PROFILE=admin terraform plan
```

Until then, `make validate` checks the code without touching AWS.
