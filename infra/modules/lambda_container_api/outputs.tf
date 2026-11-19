output "function_name" {
  description = "Function name."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "Function ARN."
  value       = aws_lambda_function.this.arn
}

output "function_url" {
  description = "The function URL. Not secret, but it only accepts requests signed by CloudFront."
  value       = aws_lambda_function_url.this.function_url
}

output "role_name" {
  description = "Name of the function's role, for policy checks."
  value       = aws_iam_role.this.name
}

output "log_group_name" {
  description = "CloudWatch log group of the function."
  value       = aws_cloudwatch_log_group.this.name
}
