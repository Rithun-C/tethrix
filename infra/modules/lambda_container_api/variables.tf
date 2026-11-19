variable "name" {
  description = "Function name; also used for the role and the log group."
  type        = string
}

variable "description" {
  description = "Function description."
  type        = string
  default     = ""
}

variable "image_uri" {
  description = "Image to run, as repository_url:tag. Null until the first image is pushed."
  type        = string
  default     = null
}

variable "memory_mb" {
  description = "Memory in MB. CPU grows with memory."
  type        = number
  default     = 512

  validation {
    condition     = var.memory_mb >= 128 && var.memory_mb <= 1024
    error_message = "Memory must be between 128 and 1024 MB (more costs more per second)."
  }
}

variable "timeout_seconds" {
  description = "Longest a request may run."
  type        = number
  default     = 10

  validation {
    condition     = var.timeout_seconds >= 1 && var.timeout_seconds <= 30
    error_message = "Timeout must be between 1 and 30 seconds (T-022)."
  }
}

variable "reserved_concurrency" {
  description = "Cap on copies running at once; -1 for no reservation (SR-72)."
  type        = number
  default     = -1

  validation {
    condition     = var.reserved_concurrency == -1 || (var.reserved_concurrency >= 1 && var.reserved_concurrency <= 10)
    error_message = "Use -1 (no reservation) or a cap between 1 and 10."
  }
}

variable "environment" {
  description = "Environment variables. Never secrets: they are visible to anyone who can read the function."
  type        = map(string)
  default     = {}
}

variable "log_retention_days" {
  description = "How long logs are kept (SR-43)."
  type        = number
  default     = 14
}

variable "dynamodb_actions" {
  description = "DynamoDB actions the code uses, for example dynamodb:GetItem. Never dynamodb:* (SR-70)."
  type        = list(string)
  default     = []

  validation {
    condition     = alltrue([for a in var.dynamodb_actions : can(regex("^dynamodb:[A-Za-z]+$", a))])
    error_message = "List exact DynamoDB actions, such as dynamodb:Query. Wildcards are not allowed (SR-70)."
  }
}

variable "dynamodb_resource_arns" {
  description = "Table and index ARNs the actions apply to."
  type        = list(string)
  default     = []
}
