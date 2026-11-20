# Shown after apply on the owner's laptop. Some contain the account ID (the ECR address):
# never paste them into docs, issues or pull requests.

output "app_url" {
  description = "The app's address: the custom domain, or the execute-api address while use_custom_domain is false."
  value       = local.app_url
}

output "api_endpoint" {
  description = "API Gateway's own execute-api address. Switched off when the custom domain is on (T-038). Not written into the repo."
  value       = aws_apigatewayv2_api.app.api_endpoint
}

output "name_servers" {
  description = "Add these as NS records for the subdomain at the parent domain's DNS provider. Null while use_custom_domain is false."
  value       = one(aws_route53_zone.app[*].name_servers)
}

output "ecr_repository_url" {
  description = "Where make push-backend pushes. Contains the account ID."
  value       = module.ecr.repository_url
}

output "lambda_role_name" {
  description = "For the policy check with Access Analyzer (SR-70)."
  value       = module.backend.role_name
}

output "lambda_log_group" {
  description = "The app's own logs: one JSON line per request."
  value       = module.backend.log_group_name
}

output "api_access_log_group" {
  description = "API Gateway's access logs: one line per request at the edge."
  value       = aws_cloudwatch_log_group.api_access.name
}

output "cognito_user_pool_id" {
  description = "For make user-create, user-disable, user-delete."
  value       = aws_cognito_user_pool.app.id
}

output "cognito_domain_url" {
  description = "Cognito's hosted sign-in address."
  value       = local.cognito_domain_url
}

output "table_name" {
  description = "The app's DynamoDB table, for make user-create (profile items)."
  value       = module.table.name
}
