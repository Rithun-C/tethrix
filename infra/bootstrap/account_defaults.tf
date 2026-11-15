# Account defaults: settings made once that apply to everything created afterwards.
# They are a safety net for resources that forget a setting.
#
# All of these are free. If this stack were destroyed, each setting would go back to
# AWS's weaker default, which is one more reason bootstrap is destroyed last (task O-11).
#
# Scope: S3 Block Public Access and the password policy cover the whole account.
# The EC2 and EBS settings are per region; we only use us-east-1.

# No bucket in the account can be made public, whatever its own settings say.
resource "aws_s3_account_public_access_block" "this" {
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Every new EBS volume (EC2 disk) is encrypted. Uses the AWS-managed key aws/ebs,
# which is free. Only customer-managed KMS keys cost money.
resource "aws_ebs_encryption_by_default" "this" {
  enabled = true
}

# New EC2 instances must use IMDSv2. The instance metadata service hands out the
# instance's temporary AWS credentials. IMDSv1 answers any simple GET request, so a bug
# that makes the server fetch a URL for an attacker (SSRF) can leak those credentials.
# IMDSv2 requires a session token first, which blocks that attack.
resource "aws_ec2_instance_metadata_defaults" "this" {
  http_tokens = "required"

  # 2 hops lets containers running on an instance reach the metadata service.
  # With 1, only the instance itself can.
  http_put_response_hop_limit = 2
}

# EBS snapshots (disk backups) cannot be shared publicly.
resource "aws_ebs_snapshot_block_public_access" "this" {
  state = "block-all-sharing"
}

# AMIs (server images) cannot be shared publicly.
resource "aws_ec2_image_block_public_access" "this" {
  state = "block-new-sharing"
}

# Rules for IAM user passwords, such as the admin user's.
resource "aws_iam_account_password_policy" "this" {
  #checkov:skip=CKV_AWS_9:Forced password expiry is not used. Current NIST guidance (SP 800-63B) advises against it because it leads to weaker passwords. MFA protects the login instead.
  minimum_password_length        = 14
  require_lowercase_characters   = true
  require_uppercase_characters   = true
  require_numbers                = true
  require_symbols                = true
  password_reuse_prevention      = 24 # CIS benchmark value; the maximum AWS allows
  allow_users_to_change_password = true
}
