# The app's domain (ADR-0006): a Route 53 zone for the subdomain only, the TLS
# certificate, and the records that point the name at CloudFront.
#
# The parent domain hands this subdomain to Route 53 with four NS records, added by the
# owner once at the parent's DNS provider (docs/runbooks/deploy-manual.md, step 3).
# Nothing here touches the parent domain.

resource "aws_route53_zone" "app" {
  #checkov:skip=CKV2_AWS_38:DNSSEC needs an asymmetric KMS key (about 1 USD a month) and a DS record at the parent; not worth it for a learning app. Theory note in B3-09.
  #checkov:skip=CKV2_AWS_39:Query logging goes to CloudWatch Logs and is paid per GB; not needed here.
  name    = var.domain_name
  comment = "productivity-app (ADR-0006). Delegated from the parent domain."
}

# Only Amazon's certificate authority may issue certificates for this name. If anyone
# tricked another authority, it would refuse. Free, and one record.
resource "aws_route53_record" "caa" {
  zone_id = aws_route53_zone.app.zone_id
  name    = var.domain_name
  type    = "CAA"
  ttl     = 3600
  records = ["0 issue \"amazon.com\""]
}

# The TLS certificate. ACM certificates for CloudFront must be in us-east-1, which is
# already our only region. Public certificates are free and renew themselves.
resource "aws_acm_certificate" "app" {
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
    for option in aws_acm_certificate.app.domain_validation_options : option.domain_name => {
      name   = option.resource_record_name
      type   = option.resource_record_type
      record = option.resource_record_value
    }
  }

  zone_id         = aws_route53_zone.app.zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 300
  records         = [each.value.record]
  allow_overwrite = true
}

# Waits until ACM has seen the record and issued the certificate. This only works once
# the NS records exist at the parent; until then it waits (up to 75 minutes) and fails.
resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# The app's name points at CloudFront, for IPv4 (A) and IPv6 (AAAA). Alias records are
# answered by Route 53 itself, and queries for aliases to CloudFront are free.
resource "aws_route53_record" "app" {
  for_each = toset(["A", "AAAA"])

  zone_id = aws_route53_zone.app.zone_id
  name    = var.domain_name
  type    = each.key

  alias {
    name                   = aws_cloudfront_distribution.app.domain_name
    zone_id                = aws_cloudfront_distribution.app.hosted_zone_id
    evaluate_target_health = false
  }
}
