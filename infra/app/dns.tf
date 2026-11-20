# The app's domain (ADR-0006): a Route 53 zone for the subdomain only, the TLS
# certificate, the name on API Gateway, and the records that point the name there
# (ADR-0007).
#
# The parent domain hands this subdomain to Route 53 with four NS records, added by the
# owner once at the parent's DNS provider (docs/runbooks/deploy-manual.md, step 3).
# Nothing here touches the parent domain.
#
# Everything in this file exists only while var.use_custom_domain is true. With false,
# the app is served on API Gateway's own execute-api address.

resource "aws_route53_zone" "app" {
  count = var.use_custom_domain ? 1 : 0

  #checkov:skip=CKV2_AWS_38:DNSSEC needs an asymmetric KMS key (about 1 USD a month) and a DS record at the parent; not worth it for a learning app. Theory note in B3-09.
  #checkov:skip=CKV2_AWS_39:Query logging goes to CloudWatch Logs and is paid per GB; not needed here.
  name    = var.domain_name
  comment = "productivity-app (ADR-0006). Delegated from the parent domain."
}

# Only Amazon's certificate authority may issue certificates for this name. If anyone
# tricked another authority, it would refuse. Free, and one record.
resource "aws_route53_record" "caa" {
  count = var.use_custom_domain ? 1 : 0

  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "CAA"
  ttl     = 3600
  records = ["0 issue \"amazon.com\""]
}

# The TLS certificate. A regional API Gateway domain needs a certificate in the same
# region, us-east-1, our only region. Public certificates are free and renew themselves.
resource "aws_acm_certificate" "app" {
  count = var.use_custom_domain ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  # When the certificate has to be replaced, the new one is created before the old one
  # is removed, so CloudFront is never left without one.
  lifecycle {
    create_before_destroy = true
  }
}

# The record ACM looks for to prove we control the name. It stays, so renewals happen
# without anyone doing anything.
resource "aws_route53_record" "cert_validation" {
  for_each = {
    # [*] gives an empty list when the certificate does not exist, so this map is empty.
    for option in flatten(aws_acm_certificate.app[*].domain_validation_options) : option.domain_name => {
      name   = option.resource_record_name
      type   = option.resource_record_type
      record = option.resource_record_value
    }
  }

  zone_id         = aws_route53_zone.app[0].zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 300
  records         = [each.value.record]
  allow_overwrite = true
}

# Waits until ACM has seen the record and issued the certificate. This only works once
# the NS records exist at the parent; until then it waits (up to 75 minutes) and fails.
resource "aws_acm_certificate_validation" "app" {
  count = var.use_custom_domain ? 1 : 0

  certificate_arn         = aws_acm_certificate.app[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Our name on API Gateway, with our certificate. TLS_1_2: only TLS 1.2 and newer are
# accepted (SR-50). Regional: served from us-east-1 directly, no CDN.
resource "aws_apigatewayv2_domain_name" "app" {
  count = var.use_custom_domain ? 1 : 0

  domain_name = var.domain_name

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.app[0].certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
    ip_address_type = "dualstack"
  }
}

# Requests for our name go to the API's default stage.
resource "aws_apigatewayv2_api_mapping" "app" {
  count = var.use_custom_domain ? 1 : 0

  api_id      = aws_apigatewayv2_api.app.id
  domain_name = aws_apigatewayv2_domain_name.app[0].id
  stage       = aws_apigatewayv2_stage.default.id
}

# The app's name points at the API Gateway domain, for IPv4 (A) and IPv6 (AAAA). Alias
# records are answered by Route 53 itself.
resource "aws_route53_record" "app" {
  for_each = var.use_custom_domain ? toset(["A", "AAAA"]) : toset([])

  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = each.key

  alias {
    name                   = aws_apigatewayv2_domain_name.app[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.app[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
