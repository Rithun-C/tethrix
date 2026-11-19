# A module only says which versions it works with. The stack that calls it pins the
# exact provider version and configures region, tags and state.

terraform {
  required_version = ">= 1.15"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.71.0"
    }
  }
}
