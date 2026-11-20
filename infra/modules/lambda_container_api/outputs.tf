output "function_name" {
  description = "Function name."
  value       = aws_lambda_function.this.function_name
}

output "function_arn" {
  description = "Function ARN."
  value       = aws_lambda_function.this.arn
}

output "invoke_arn" {
  description = "ARN that API Gateway uses to call the function."
  value       = aws_lambda_function.this.invoke_arn
}

output "role_name" {
  description = "Name of the function's role, for policy checks."
  value       = aws_iam_role.this.name
}

output "log_group_name" {
  description = "CloudWatch log group of the function."
  value       = aws_cloudwatch_log_group.this.name
}
