# The front door (B3-04 to B3-07, ADR-0007). An API Gateway HTTP API that receives every
# request on HTTPS, pages and API calls alike, and hands it to the Lambda function. FastAPI
# answers /api/* and serves the React app for everything else.
#
# ADR-0007 replaced the CloudFront design (ADR-0002), which needs the Paid plan for this
# account. The CloudFront code is in Git history (pull requests #12 and #13).

locals {
  # B3 decision 11: a page load is about 3 requests, so this is plenty for a few users,
  # and a flood is refused with 429 before it reaches Lambda (T-021).
  throttle_rate_per_second = 10
  throttle_burst           = 20
}

resource "aws_apigatewayv2_api" "app" {
  name          = "${var.project}-api"
  description   = "Front door for the app (ADR-0007)"
  protocol_type = "HTTP"

  # Answers on IPv4 and IPv6.
  ip_address_type = "dualstack"

  # The default https://<id>.execute-api... address. Needed while there is no custom
  # domain; switched off with the domain, so our name is then the only way in (T-038).
  disable_execute_api_endpoint = var.use_custom_domain
}

# Hands requests to Lambda. Payload format 2.0 is what the Web Adapter reads.
resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.app.id
  integration_type       = "AWS_PROXY"
  integration_uri        = module.backend.invoke_arn
  payload_format_version = "2.0"

  # A little above the Lambda timeout (10 s), so Lambda's own timeout answers first.
  timeout_milliseconds = 12000
}

# One catch-all route: every method and path goes to Lambda. FastAPI decides what each
# path means. Sign-in is checked by FastAPI from B4 on (ADR-0003).
resource "aws_apigatewayv2_route" "default" {
  #checkov:skip=CKV_AWS_309:Sign-in is checked in FastAPI (ADR-0003, B4); the catch-all route also serves the public React files and the health check. A JWT authorizer is reconsidered in B4.
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

# One line per request at the edge, like CloudFront logs would have been: when, from
# where, what, and the answer. Never bodies. 14 days (SR-43).
resource "aws_cloudwatch_log_group" "api_access" { # nosemgrep: terraform.aws.security.aws-cloudwatch-log-group-unencrypted.aws-cloudwatch-log-group-unencrypted
  #checkov:skip=CKV_AWS_158:AWS-managed encryption instead of a KMS key, project cost rule.
  #checkov:skip=CKV_AWS_338:14 days on purpose (SR-43): enough to investigate, short enough to keep cost and personal data low.
  name              = "/aws/apigateway/${var.project}-api"
  retention_in_days = 14
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.app.id
  name        = "$default" # addresses without a stage name in the path
  auto_deploy = true

  default_route_settings {
    throttling_rate_limit  = local.throttle_rate_per_second
    throttling_burst_limit = local.throttle_burst
  }

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_access.arn
    format = jsonencode({
      time           = "$context.requestTime"
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      method         = "$context.httpMethod"
      path           = "$context.path"
      status         = "$context.status"
      latencyMs      = "$context.responseLatency"
      integrationErr = "$context.integrationErrorMessage"
    })
  }
}

# Only this API may invoke the function, and only through its own stages and routes
# (SR-62). The function has no other public address.
resource "aws_lambda_permission" "api" {
  statement_id  = "AllowApiGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.backend.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.app.execution_arn}/*/*"
}
