# S3 bucket that holds Terraform state for every stack in this project.

# Reads the account ID at run time, so it never has to be written in this public repo.
data "aws_caller_identity" "current" {}

locals {
  # Bucket names are global across all AWS accounts, so the account ID makes it unique.
  state_bucket_name = "${var.project}-tfstate-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket" "state" {
  #checkov:skip=CKV_AWS_18:Access logging needs a second bucket; CloudTrail (G-09) records management access instead.
  #checkov:skip=CKV_AWS_144:Cross-region replication breaks the one-region rule and costs money.
  #checkov:skip=CKV_AWS_145:SSE-S3 is used instead of KMS to avoid the monthly key cost (project cost rule).
  #checkov:skip=CKV2_AWS_62:Event notifications are not needed for a state bucket.
  bucket = local.state_bucket_name

  # Stops `terraform destroy` from deleting the bucket by accident. Losing state means
  # Terraform forgets every resource it created. Removed on purpose only at the end (O-11).
  lifecycle {
    prevent_destroy = true
  }
}

# Keeps every previous version of the state file, so a bad write can be rolled back.
resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypts objects at rest with S3-managed keys (SSE-S3). Free, unlike a KMS key.
# Trivy asks for a KMS key here; skipped for the same cost reason as CKV_AWS_145 above.
#trivy:ignore:AVD-AWS-0132
resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Blocks every way of making the bucket or its objects public.
resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Turns off ACLs completely. Access is then controlled only by IAM and the bucket policy.
resource "aws_s3_bucket_ownership_controls" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Refuses any request that is not over HTTPS, so state never travels unencrypted.
data "aws_iam_policy_document" "state" {
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.state.arn,
      "${aws_s3_bucket.state.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "state" {
  bucket = aws_s3_bucket.state.id
  policy = data.aws_iam_policy_document.state.json

  # The public access block must exist first, or AWS may reject the policy.
  depends_on = [aws_s3_bucket_public_access_block.state]
}

# Deletes old state versions after a while and cleans up failed uploads, so storage
# stays close to zero.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-old-state-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = var.noncurrent_version_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  # Lifecycle rules on versioned buckets need versioning in place first.
  depends_on = [aws_s3_bucket_versioning.state]
}
