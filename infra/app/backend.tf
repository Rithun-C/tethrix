# Where this stack keeps its state: the S3 bucket created by infra/bootstrap.
#
# The block is empty on purpose. The bucket name contains the account ID, so it is
# passed in at init time from backend.hcl, which git ignores:
#   terraform init -backend-config=backend.hcl
#
# The app has its own state file (key app/terraform.tfstate), separate from bootstrap
# and from every lab. A mistake in one stack cannot damage another.

terraform {
  backend "s3" {}
}
