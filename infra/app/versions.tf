# Pins the Terraform and provider versions so every run behaves the same.
# Kept equal to infra/bootstrap/versions.tf.

terraform {
  required_version = "~> 1.15"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.71.0"
    }
  }
}
