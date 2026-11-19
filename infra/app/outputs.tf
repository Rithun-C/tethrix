# Shown after apply on the owner's laptop. Some contain the account ID (the ECR address,
# the bucket name): never paste them into docs, issues or pull requests.

output "app_url" {
  description = "The app's address: the custom domain, or the *.cloudfront.net address while use_custom_domain is false."
  value       = var.use_custom_domain ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.app.domain_name}"
}

output "name_servers" {
  description = "Add these as NS records for the subdomain at the parent domain's DNS provider. Null while use_custom_domain is false."
  value       = one(aws_route53_zone.app[*].name_servers)
}

output "ecr_repository_url" {
  description = "Where make push-backend pushes. Contains the account ID."
  value       = module.ecr.repository_url
}

output "frontend_bucket" {
  description = "Where make publish-frontend uploads. Contains the account ID."
  value       = aws_s3_bucket.frontend.bucket
}

output "distribution_id" {
  description = "Used by make publish-frontend for the invalidation."
  value       = aws_cloudfront_distribution.app.id
}

output "cloudfront_domain" {
  description = "The distribution's own *.cloudfront.net name. Not written into the repo."
  value       = aws_cloudfront_distribution.app.domain_name
}

output "function_url" {
  description = "Direct function URL, for the negative test (must answer 403)."
  value       = module.backend.function_url
}

output "lambda_role_name" {
  description = "For the policy check with Access Analyzer (SR-70)."
  value       = module.backend.role_name
}

output "lambda_log_group" {
  description = "Where the API's logs are."
  value       = module.backend.log_group_name
}
