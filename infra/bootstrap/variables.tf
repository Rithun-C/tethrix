variable "project" {
  description = "Project name, used in resource names and tags."
  type        = string
  default     = "productivity-app"
}

variable "region" {
  description = "The only region this project uses."
  type        = string
  default     = "us-east-1"

  validation {
    condition     = var.region == "us-east-1"
    error_message = "This project uses one region only: us-east-1."
  }
}

variable "alert_email" {
  description = "Email address that receives budget alerts. Set it in terraform.tfvars, never in code."
  type        = string
  sensitive   = true

  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "alert_email must be a valid email address."
  }
}

variable "monthly_budget_usd" {
  description = "Monthly cost budget in USD, credits excluded."
  type        = number
  default     = 10
}

variable "daily_budget_usd" {
  description = "Daily cost budget in USD, credits excluded."
  type        = number
  default     = 1
}

variable "noncurrent_version_days" {
  description = "Days to keep old versions of the state file before they are deleted."
  type        = number
  default     = 90
}
