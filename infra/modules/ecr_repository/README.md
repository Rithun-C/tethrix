# Module: ecr_repository

A private ECR repository: immutable tags, scan on push, AES-256 encryption and a
lifecycle rule that keeps the newest few images. Used for the backend image (ADR-0004,
task B3-01).

| Input | Default | Meaning |
|---|---|---|
| `name` | | Repository name |
| `images_to_keep` | 3 | Images kept by the lifecycle rule |
| `force_delete` | false | Allow destroy with images inside; only for the final destroy |

Outputs: `repository_url`, `repository_arn`, `repository_name`.
