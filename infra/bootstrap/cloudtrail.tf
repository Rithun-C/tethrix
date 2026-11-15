# CloudTrail: a permanent, tamper-evident record of every management action in the
# account. Management events from the first trail are free. Only the S3 storage costs,
# and it is tiny.

locals {
  account_id            = data.aws_caller_identity.current.account_id
  trail_name            = "${var.project}-trail"
  cloudtrail_bucket     = "${var.project}-cloudtrail-${local.account_id}"
  trail_log_days        = 180
  trail_noncurrent_days = 30

  # Built by hand rather than read from the trail resource. The trail needs the bucket
  # policy to exist first, and the bucket policy needs the trail ARN, so reading it from
  # the trail would create a loop.
  trail_arn = "arn:aws:cloudtrail:${var.region}:${local.account_id}:trail/${local.trail_name}"
}

# ---------- Logs bucket ----------

resource "aws_s3_bucket" "cloudtrail" {
  #checkov:skip=CKV_AWS_18:Access logging for the log bucket would need a third bucket; CloudTrail itself records management access.
  #checkov:skip=CKV_AWS_144:Cross-region replication breaks the one-region rule and costs money.
  #checkov:skip=CKV_AWS_145:SSE-S3 is used instead of KMS to avoid the monthly key cost (project cost rule).
  #checkov:skip=CKV2_AWS_62:Event notifications are not needed for the log bucket.
  bucket = local.cloudtrail_bucket

  # force_destroy is left at its default (false). Terraform then refuses to delete the
  # bucket while it still holds logs, which protects the evidence. At the end of the
  # project (O-11) the bucket is emptied on purpose first.
}

resource "aws_s3_bucket_versioning" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Trivy asks for a KMS key here. SSE-S3 is used instead to avoid the monthly key cost
# (project cost rule). Same reason as the checkov skip CKV_AWS_145 above.
#trivy:ignore:AVD-AWS-0132
resource "aws_s3_bucket_server_side_encryption_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

data "aws_iam_policy_document" "cloudtrail_bucket" {
  # CloudTrail checks it is allowed to use the bucket before writing.
  statement {
    sid       = "AWSCloudTrailAclCheck"
    effect    = "Allow"
    actions   = ["s3:GetBucketAcl"]
    resources = [aws_s3_bucket.cloudtrail.arn]

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    # Only on behalf of our own trail. This blocks the "confused deputy" problem:
    # someone else's trail cannot be pointed at this bucket.
    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.trail_arn]
    }
  }

  # CloudTrail may write log files, only under this account's folder.
  statement {
    sid       = "AWSCloudTrailWrite"
    effect    = "Allow"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.cloudtrail.arn}/AWSLogs/${local.account_id}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudtrail.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "s3:x-amz-acl"
      values   = ["bucket-owner-full-control"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceArn"
      values   = [local.trail_arn]
    }
  }

  # Refuses any request that is not over HTTPS.
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.cloudtrail.arn,
      "${aws_s3_bucket.cloudtrail.arn}/*",
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

resource "aws_s3_bucket_policy" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id
  policy = data.aws_iam_policy_document.cloudtrail_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.cloudtrail]
}

# Logs are kept for 180 days, which covers the whole project including the incident
# drill. Old versions of overwritten or deleted files are kept 30 more days.
resource "aws_s3_bucket_lifecycle_configuration" "cloudtrail" {
  bucket = aws_s3_bucket.cloudtrail.id

  rule {
    id     = "expire-old-logs"
    status = "Enabled"

    filter {}

    expiration {
      days = local.trail_log_days
    }

    noncurrent_version_expiration {
      noncurrent_days = local.trail_noncurrent_days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  depends_on = [aws_s3_bucket_versioning.cloudtrail]
}

# ---------- Trail ----------

# Trivy and Semgrep ask for a KMS key on the trail. Not used: monthly key cost
# (project cost rule). Same reason as the checkov skip CKV_AWS_35 below.
#trivy:ignore:AVD-AWS-0015
resource "aws_cloudtrail" "this" { # nosemgrep: terraform.aws.security.aws-cloudtrail-encrypted-with-cmk.aws-cloudtrail-encrypted-with-cmk
  #checkov:skip=CKV_AWS_35:SSE-S3 on the bucket is used instead of a KMS key to avoid the monthly key cost.
  #checkov:skip=CKV_AWS_252:No SNS topic for log delivery notifications yet; not needed for a single-person account.
  #checkov:skip=CKV2_AWS_10:Sending to CloudWatch Logs costs per GB; planned for Operations (O-01).
  name           = local.trail_name
  s3_bucket_name = aws_s3_bucket.cloudtrail.id

  # One trail that records every region. Still free. Attackers with stolen keys often
  # use regions you never look at.
  is_multi_region_trail = true

  # IAM, STS and sign-in events are global, not tied to a region. Record them too.
  include_global_service_events = true

  # Writes a signed digest file every hour, so you can later prove no log file was
  # changed or deleted.
  enable_log_file_validation = true

  # Management events only (create, change, delete). Data events, such as every S3
  # object read, cost money per event and are left off.
  event_selector {
    read_write_type           = "All"
    include_management_events = true
  }

  # CloudTrail checks the bucket policy when the trail is created.
  depends_on = [aws_s3_bucket_policy.cloudtrail]
}
