# infra/modules

A module is a folder of Terraform files that can be used more than once, like a function
in code: inputs (variables) go in, resources are created, outputs come back.

| Module | What it makes | Bolt |
|---|---|---|
| [ecr_repository](ecr_repository/README.md) | Private ECR repository, immutable tags, scan on push, lifecycle rule | B3 |
| [dynamodb_table](dynamodb_table/README.md) | The app's single table from I-08 | B3 |
| [lambda_container_api](lambda_container_api/README.md) | Container Lambda with its role, log group and an `AWS_IAM` function URL | B3 |

## Rules for every module

1. One purpose per module (for example "a private S3 bucket", not "all storage").
2. Three files at least: `main.tf`, `variables.tf`, `outputs.tf`, plus a short `README.md`.
3. Every variable has a `type` and a `description`. Add a `validation` block where a
   wrong value could cost money or weaken security.
4. Every output has a `description`.
5. No `provider` block and no `backend` block inside a module. The stack that calls the
   module decides the region, the tags and the state. A module only declares which
   provider version it needs (`required_providers`).
6. Safe by default: encryption on, public access off, log retention set. The caller has
   to ask for anything less safe.
7. Names take a prefix from a variable. Nothing is hard-coded to one stack.
8. No `*` in IAM policies unless an ADR explains it.

## How a stack calls a module

```hcl
module "frontend_bucket" {
  source = "../modules/private-bucket"
  name   = "${var.project}-frontend"
}
```

Local modules are called by path, so they have no version number. They change together
with the stack, in the same commit.
