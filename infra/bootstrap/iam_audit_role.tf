# Read-only role for security scanners such as Prowler (G-11, O-05).
#
# Why a role instead of using admin: a scanner is third-party code. It only needs to read
# settings, so it gets an identity that can do nothing else. The admin user "assumes"
# (temporarily switches to) this role for the scan, and the credentials expire after an hour.

# Reads the existing admin user (created in the console during G-04, see ADR-0005).
# Fails the plan if the user does not exist, which is a useful check in itself.
data "aws_iam_user" "admin" {
  user_name = "admin"
}

# Trust policy: who may assume the role. Only the admin user.
data "aws_iam_policy_document" "security_audit_trust" {
  statement {
    sid     = "AllowAdminToAssume"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = [data.aws_iam_user.admin.arn]
    }
  }
}

resource "aws_iam_role" "security_audit" {
  name                 = "security-audit"
  description          = "Read-only role for security scanners (Prowler). Assumed by the admin user."
  assume_role_policy   = data.aws_iam_policy_document.security_audit_trust.json
  max_session_duration = 3600
}

# AWS managed policies documented by Prowler as the minimum it needs.
# SecurityAudit: read security configuration. ViewOnlyAccess: list and describe resources.
# Neither can change anything or read data such as S3 object contents.
resource "aws_iam_role_policy_attachment" "security_audit" {
  role       = aws_iam_role.security_audit.name
  policy_arn = "arn:aws:iam::aws:policy/SecurityAudit"
}

resource "aws_iam_role_policy_attachment" "view_only" {
  role       = aws_iam_role.security_audit.name
  policy_arn = "arn:aws:iam::aws:policy/job-function/ViewOnlyAccess"
}

output "security_audit_role_arn" {
  description = "Used in the audit profile in ~/.aws/config."
  value       = aws_iam_role.security_audit.arn
}
