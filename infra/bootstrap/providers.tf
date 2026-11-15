# Credentials come from the environment (AWS_PROFILE=admin with `aws login`).
# They are never written in code.

provider "aws" {
  region = var.region

  # Every resource this provider creates gets these tags. Tags make it easy to find
  # everything belonging to the project, for example in the session-end sweep.
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Stack     = "bootstrap"
    }
  }
}
