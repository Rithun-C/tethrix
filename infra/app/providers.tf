# Credentials come from the environment (AWS_PROFILE=admin with `aws login`).
# They are never written in code.

provider "aws" {
  region = var.region

  # Every resource this provider creates gets these tags. Stack = app tells the session
  # sweep which stack a resource belongs to.
  default_tags {
    tags = {
      Project   = var.project
      ManagedBy = "terraform"
      Stack     = "app"
    }
  }
}
