# Credentials come from the environment (AWS_PROFILE=admin with `aws login`).
# They are never written in code.

provider "aws" {
  region = var.region

  # Replace NAME. The Stack tag lets the session sweep show which lab left something
  # running.
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Stack     = "lab-NAME"
    }
  }
}
