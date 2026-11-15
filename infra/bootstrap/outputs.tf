output "state_bucket_name" {
  description = "Copy this into backend.hcl after the first apply."
  value       = aws_s3_bucket.state.bucket
}
