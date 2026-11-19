# Module: lambda_container_api

A Lambda function that runs a container image with the Lambda Web Adapter, plus:

- its own IAM role: write to its own log group, and only the DynamoDB actions and ARNs
  passed in (none in B3)
- its own log group with a retention period (SR-43)
- a function URL with auth type `AWS_IAM`, so only signed requests get in (ADR-0002)

Who may call the function URL (CloudFront) is decided by the caller with
`aws_lambda_permission`, because it needs the distribution's ARN.

| Input | Default | Meaning |
|---|---|---|
| `name` | | Function, role and log group name |
| `image_uri` | null | `repository_url:tag`; apply fails with a clear message while null |
| `memory_mb`, `timeout_seconds` | 512, 10 | ADR-0004 |
| `reserved_concurrency` | -1 | -1 = no reservation (SR-72) |
| `environment` | {} | Never secrets |
| `log_retention_days` | 14 | SR-43 |
| `dynamodb_actions`, `dynamodb_resource_arns` | [] | Exact actions only, no wildcards (SR-70) |

Outputs: `function_name`, `function_arn`, `function_url`, `role_name`, `log_group_name`.
