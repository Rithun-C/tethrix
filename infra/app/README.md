# infra/app

The Terraform stack for the application itself (bolt B3 onward). How to deploy it:
`docs/runbooks/deploy-manual.md`.

| File | What it holds |
|---|---|
| `versions.tf` | Terraform and provider versions |
| `backend.tf` | State location (the S3 bucket from `infra/bootstrap`) |
| `backend.hcl.example` | Template for `backend.hcl`, which holds the bucket name |
| `providers.tf` | Region and default tags |
| `variables.tf` | Inputs: domain, backend image tag, concurrency cap, final-destroy switch |
| `ecr.tf` | Repository for the backend image (module `ecr_repository`) |
| `dynamodb.tf` | The app's table (module `dynamodb_table`) |
| `lambda.tf` | The backend function (module `lambda_container_api`) |
| `auth.tf` | Cognito user pool (Lite, TOTP required), hosted sign-in domain, web app client (B4, ADR-0003) |
| `api.tf` | API Gateway HTTP API: catch-all route to Lambda, stage with throttling and access logs, Lambda permission (ADR-0007) |
| `dns.tf` | Route 53 zone for `tethrix.satrix.in`, CAA record, ACM certificate, API Gateway custom domain, alias records (ADR-0006) |
| `outputs.tf` | Values the `make` deploy targets read. Some contain the account ID: never paste them into docs |

`make validate`, `make lint`, `make checkov` check the code without touching AWS.
