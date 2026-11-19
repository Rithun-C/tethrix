# The bucket that holds the React build (B3-04). Private: only CloudFront can read it,
# through OAC. The files are uploaded by `make publish-frontend`, not by Terraform:
# a build is data, like the users in B4-08.

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "frontend" {
  #checkov:skip=CKV_AWS_18:Access logging needs a second bucket; the files are public through CloudFront anyway and CloudTrail records management access.
  #checkov:skip=CKV_AWS_144:Cross-region replication breaks the one-region rule and costs money.
  #checkov:skip=CKV_AWS_145:SSE-S3 instead of KMS, project cost rule (F-013). The files are the public website.
  #checkov:skip=CKV2_AWS_62:Event notifications are not needed for website files.
  #checkov:skip=CKV_AWS_21:No versioning: every build can be rebuilt from its Git commit, and old versions would only add storage cost.
  # Bucket names are global; the account ID keeps ours unique without writing it here.
  bucket = "${var.project}-frontend-${data.aws_caller_identity.current.account_id}"

  # Lets destroy remove the bucket with the build inside. Safe: everything in it is
  # rebuilt from Git by `make publish-frontend`.
  force_destroy = true
}

# Encrypts objects at rest with S3-managed keys. Trivy asks for KMS; same cost reason.
#trivy:ignore:AVD-AWS-0132
resource "aws_s3_bucket_server_side_encryption_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# The bucket itself is never public. Visitors only reach the files through CloudFront.
resource "aws_s3_bucket_public_access_block" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

# Cleans up uploads that never finished, so they do not cost storage.
resource "aws_s3_bucket_lifecycle_configuration" "frontend" {
  bucket = aws_s3_bucket.frontend.id

  rule {
    id     = "abort-incomplete-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 1
    }
  }
}

data "aws_iam_policy_document" "frontend" {
  # CloudFront may read files, but only when the request comes from our distribution
  # (aws:SourceArn). Another distribution, even one in this account, gets nothing.
  statement {
    sid       = "AllowOurCloudFrontToRead"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.frontend.arn}/*"]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.app.arn]
    }
  }

  # Refuses anything not over HTTPS (SR-50).
  statement {
    sid     = "DenyInsecureTransport"
    effect  = "Deny"
    actions = ["s3:*"]
    resources = [
      aws_s3_bucket.frontend.arn,
      "${aws_s3_bucket.frontend.arn}/*",
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

resource "aws_s3_bucket_policy" "frontend" {
  bucket = aws_s3_bucket.frontend.id
  policy = data.aws_iam_policy_document.frontend.json

  depends_on = [aws_s3_bucket_public_access_block.frontend]
}
