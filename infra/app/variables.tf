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
