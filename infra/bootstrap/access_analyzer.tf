# IAM Access Analyzer (external access): keeps checking resource policies and raises a
# finding when something is shared outside this account or with the public.
# CloudTrail shows what happened; Access Analyzer shows what is possible.
#
# The external access analyzer is free. The "unused access" and "internal access"
# analyzers are paid per resource each month and are not used.
#
# It is regional: it checks resources in us-east-1, plus global ones such as IAM roles.

resource "aws_accessanalyzer_analyzer" "this" {
  analyzer_name = "${var.project}-external-access"

  # ACCOUNT: look for access from outside this single account.
  # (ORGANIZATION would need AWS Organizations, which we never use.)
  type = "ACCOUNT"
}
