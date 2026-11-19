# The front door (B3-04 to B3-06, ADR-0002, ADR-0006). One distribution at
# https://tethrix.satrix.in with two behaviours:
#   /api/*      -> Lambda function URL, signed with OAC, never cached
#   everything  -> S3 bucket with the React build, signed with OAC, cached

# AWS-managed policies, looked up by name instead of copying their IDs.
data "aws_cloudfront_cache_policy" "caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "caching_disabled" {
  name = "Managed-CachingDisabled"
}

# Passes the browser's headers, cookies and query strings on to Lambda, except Host:
# the function URL only answers to its own host name (ADR-0002).
data "aws_cloudfront_origin_request_policy" "all_viewer_except_host" {
  name = "Managed-AllViewerExceptHostHeader"
}

# ---- Origin Access Control -------------------------------------------------------------
# CloudFront signs every request to the origin with SigV4. The bucket policy and the
# Lambda permissions accept only requests signed this way by our distribution.
resource "aws_cloudfront_origin_access_control" "s3" {
  name                              = "${var.project}-frontend-s3"
  description                       = "CloudFront to the frontend bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_origin_access_control" "lambda" {
  name                              = "${var.project}-api-lambda"
  description                       = "CloudFront to the API function URL"
  origin_access_control_origin_type = "lambda"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

# ---- React routing ---------------------------------------------------------------------
resource "aws_cloudfront_function" "spa_router" {
  name    = "${var.project}-spa-router"
  comment = "Sends React routes such as /todos to /index.html (B3 decision 2)"
  runtime = "cloudfront-js-2.0"
  code    = file("${path.module}/functions/spa_router.js")
  publish = true
}

# ---- Security headers (SR-60, SR-61) ---------------------------------------------------
# Added to every response, on both behaviours. override = true: our values win over
# anything the origin sends.
resource "aws_cloudfront_response_headers_policy" "security" {
  #checkov:skip=CKV_AWS_259:Fails only on preload. The HSTS preload list accepts whole registrable domains (satrix.in), which is not this project's to decide.
  name    = "${var.project}-security-headers"
  comment = "CSP, HSTS and friends (SR-60, SR-61)"

  security_headers_config {
    # Scripts, styles and API calls only from our own address. No inline scripts, no
    # eval, no framing. Cognito is added to connect-src in B4.
    content_security_policy {
      content_security_policy = join("; ", [
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self'",
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src 'self'",
        "manifest-src 'self'",
        "base-uri 'none'",
        "form-action 'self'",
        "frame-ancestors 'none'",
      ])
      override = true
    }

    # Browsers remember for a year to use HTTPS only for this name and any name under it
    # (includeSubDomains covers *.tethrix.satrix.in, never the parent satrix.in).
    # No preload: the preload list takes whole registrable domains, and satrix.in is
    # not this project's to decide for.
    strict_transport_security {
      access_control_max_age_sec = 31536000
      include_subdomains         = true
      preload                    = false
      override                   = true
    }

    content_type_options {
      override = true
    }

    frame_options {
      frame_option = "DENY"
      override     = true
    }

    referrer_policy {
      referrer_policy = "strict-origin-when-cross-origin"
      override        = true
    }
  }
}

# ---- The distribution --------------------------------------------------------------------
locals {
  frontend_origin_id = "frontend-s3"
  api_origin_id      = "api-lambda"

  # The function URL looks like https://abc123.lambda-url.us-east-1.on.aws/ ; CloudFront
  # wants only the host name.
  api_origin_domain = replace(trimsuffix(module.backend.function_url, "/"), "https://", "")
}

# Trivy asks for WAF (AWS-0011): same reason as checkov CKV_AWS_68 below.
#trivy:ignore:AVD-AWS-0011
resource "aws_cloudfront_distribution" "app" {
  #checkov:skip=CKV_AWS_68:WAF is billed monthly per web ACL and rule; practised in the B11-01 lab only.
  #checkov:skip=CKV2_AWS_47:Same as CKV_AWS_68 (WAF rule for Log4j); no Java in this app.
  #checkov:skip=CKV_AWS_86:Access logs off (B3 decision 3): S3 logs need ACLs, which our bucket defaults forbid; Lambda logs every API call.
  #checkov:skip=CKV_AWS_310:Origin failover needs a second origin in another place; one region by design.
  #checkov:skip=CKV_AWS_374:No geo restriction: the owner may use the app while travelling.
  comment             = "${var.project} (ADR-0002)"
  enabled             = true
  is_ipv6_enabled     = true
  http_version        = "http2and3"
  default_root_object = "index.html"
  aliases             = [var.domain_name]

  # Edge locations in North America and Europe only: the cheapest price class.
  price_class = "PriceClass_100"

  origin {
    origin_id                = local.frontend_origin_id
    domain_name              = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.s3.id
  }

  origin {
    origin_id                = local.api_origin_id
    domain_name              = local.api_origin_domain
    origin_access_control_id = aws_cloudfront_origin_access_control.lambda.id

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  # Everything that is not the API: the React files.
  default_cache_behavior {
    target_origin_id           = local.frontend_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_optimized.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa_router.arn
    }
  }

  # The API: every method, never cached (answers are per user from B4 on).
  ordered_cache_behavior {
    path_pattern               = "/api/*"
    target_origin_id           = local.api_origin_id
    viewer_protocol_policy     = "redirect-to-https"
    allowed_methods            = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods             = ["GET", "HEAD"]
    compress                   = true
    cache_policy_id            = data.aws_cloudfront_cache_policy.caching_disabled.id
    origin_request_policy_id   = data.aws_cloudfront_origin_request_policy.all_viewer_except_host.id
    response_headers_policy_id = aws_cloudfront_response_headers_policy.security.id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # Our own certificate, so TLS 1.2 can be the minimum (SR-50, ADR-0006). SNI: the
  # certificate is chosen by name; a dedicated IP would cost 600 USD a month.
  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.app.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

# ---- Who may call the function URL -------------------------------------------------------
# Only CloudFront, and only for our distribution (SR-62, ADR-0002). AWS needs both
# permissions for a function URL behind OAC.
resource "aws_lambda_permission" "cloudfront_invoke_url" {
  statement_id           = "AllowCloudFrontInvokeFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = module.backend.function_name
  principal              = "cloudfront.amazonaws.com"
  source_arn             = aws_cloudfront_distribution.app.arn
  function_url_auth_type = "AWS_IAM"
}

resource "aws_lambda_permission" "cloudfront_invoke" {
  statement_id             = "AllowCloudFrontInvokeFunction"
  action                   = "lambda:InvokeFunction"
  function_name            = module.backend.function_name
  principal                = "cloudfront.amazonaws.com"
  source_arn               = aws_cloudfront_distribution.app.arn
  invoked_via_function_url = true
}
