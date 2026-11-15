# Pins the Terraform and provider versions so every run behaves the same.
# Terraform 1.10+ is needed for native S3 state locking (use_lockfile).

terraform {
  required_version = "~> 1.15"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.71.0"
    }
  }

  # No backend block yet. The first apply uses local state, because the bucket that will
  # hold the state does not exist until this stack creates it. After the first apply,
  # backend.tf is added and the state is migrated. See docs/runbooks/terraform-bootstrap.md.
}
