# The app's single table (B3-03, ADR-0001, I-08). Created now; the code starts using it
# in B5, which also gives the Lambda role its first database permissions.

module "table" {
  source = "../modules/dynamodb_table"

  name                = "${var.project}-data"
  deletion_protection = !var.final_destroy
}
