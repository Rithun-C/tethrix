# A Lambda function that runs our container image (with the Lambda Web Adapter inside),
# its own role and its own log group. It has no public address of its own: the caller
# decides who may invoke it with aws_lambda_permission (ADR-0004, ADR-0007, task B3-02).

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Scanner exceptions (checkov skips and nosemgrep) are the same decisions in two tools:
# AWS-managed encryption instead of KMS keys (cost rule, F-013) and X-Ray deferred to
# Operations. Each is logged in docs/security/findings-log.md (F-021).

# ---- Logs ----------------------------------------------------------------------------
# Created here, before the function, with a retention period (SR-43). If Lambda created
# it on first use, it would keep logs forever.
resource "aws_cloudwatch_log_group" "this" { # nosemgrep: terraform.aws.security.aws-cloudwatch-log-group-unencrypted.aws-cloudwatch-log-group-unencrypted
  #checkov:skip=CKV_AWS_158:AWS-managed encryption instead of a KMS key, project cost rule.
  #checkov:skip=CKV_AWS_338:14 days on purpose (SR-43): enough to debug, short enough to keep cost and personal data low.
  name              = "/aws/lambda/${var.name}"
  retention_in_days = var.log_retention_days
}

# ---- Role ----------------------------------------------------------------------------
# Who may use the role: only the Lambda service, and only for functions in this account
# (aws:SourceAccount stops another account's function from borrowing it).
data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "this" {
  name               = "${var.name}-role"
  description        = "Runs the ${var.name} Lambda function."
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

# What the function may do (SR-70): write to its own log group, plus the DynamoDB actions
# it is given, on the ARNs it is given. In B3 the code reads no data, so the DynamoDB
# list is empty and no database statement exists at all.
data "aws_iam_policy_document" "permissions" {
  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.this.arn}:*"]
  }

  dynamic "statement" {
    for_each = length(var.dynamodb_actions) > 0 ? [1] : []

    content {
      sid       = "UseAppTable"
      actions   = var.dynamodb_actions
      resources = var.dynamodb_resource_arns
    }
  }

  # Indexes get their own statement, so item actions never apply to an index ARN and
  # Query never applies to the table itself.
  dynamic "statement" {
    for_each = length(var.dynamodb_index_actions) > 0 ? [1] : []

    content {
      sid       = "QueryAppIndexes"
      actions   = var.dynamodb_index_actions
      resources = var.dynamodb_index_arns
    }
  }
}

resource "aws_iam_role_policy" "this" {
  name   = "${var.name}-permissions"
  role   = aws_iam_role.this.id
  policy = data.aws_iam_policy_document.permissions.json
}

# ---- Function ------------------------------------------------------------------------
resource "aws_lambda_function" "this" { # nosemgrep: terraform.aws.security.aws-lambda-x-ray-tracing-not-active.aws-lambda-x-ray-tracing-not-active
  #checkov:skip=CKV_AWS_117:No VPC on purpose: the function only calls AWS APIs over HTTPS; a VPC would need a NAT Gateway or paid endpoints (B3-10).
  #checkov:skip=CKV_AWS_116:Only called synchronously through the function URL; a dead-letter queue applies to asynchronous calls.
  #checkov:skip=CKV_AWS_173:The environment holds no secrets (table name, log level); AWS-managed encryption is enough.
  #checkov:skip=CKV_AWS_272:Lambda code signing does not apply to container images; images are pinned by immutable tag and scanned instead.
  #checkov:skip=CKV_AWS_50:X-Ray tracing is part of the Operations observability work, not B3.
  #checkov:skip=CKV_AWS_115:The account limit of 10 concurrent runs is the cap (SR-72); AWS refuses a reservation while the limit is 10.
  function_name = var.name
  description   = var.description
  role          = aws_iam_role.this.arn

  package_type  = "Image"
  image_uri     = var.image_uri
  architectures = ["arm64"]

  memory_size = var.memory_mb
  timeout     = var.timeout_seconds

  # -1 means "no reservation": the function shares the account limit.
  reserved_concurrent_executions = var.reserved_concurrency

  environment { # nosemgrep: terraform.aws.security.aws-lambda-environment-unencrypted.aws-lambda-environment-unencrypted
    variables = var.environment
  }

  logging_config {
    log_format = "Text" # our app already writes one JSON object per line
    log_group  = aws_cloudwatch_log_group.this.name
  }

  lifecycle {
    precondition {
      condition     = var.image_uri != null
      error_message = "No image yet. Push one with `make push-backend`, then apply with -var backend_image_tag=<commit ID> (docs/runbooks/deploy-manual.md)."
    }
  }

  # The log group and the permission to write to it must exist before the first run.
  depends_on = [aws_iam_role_policy.this]
}
