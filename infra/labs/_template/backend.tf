# Where this lab keeps its state: the S3 bucket created by infra/bootstrap.
#
# The block is empty on purpose. The bucket name contains the account ID, so it is
# passed in at init time from backend.hcl, which git ignores:
#   terraform init -backend-config=backend.hcl
#
# Each lab has its own state file (key labs/NAME/terraform.tfstate). Destroying a lab
# cannot touch the app or the bootstrap stack.

terraform {
  backend "s3" {}
}
