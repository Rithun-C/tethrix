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

variable "domain_name" {
  description = "The app's address (ADR-0006). Only this subdomain is ever managed here, never the parent domain."
  type        = string
  default     = "tethrix.satrix.in"
}

variable "backend_image_tag" {
  description = "Git commit ID of the backend image in ECR. Null only for the first, targeted apply (runbook step 2)."
  type        = string
  default     = null

  validation {
    condition     = var.backend_image_tag == null || can(regex("^[0-9a-f]{40}$", var.backend_image_tag))
    error_message = "The image tag must be a full 40-character Git commit ID (ADR-0004)."
  }
}

variable "lambda_reserved_concurrency" {
  description = "Cap on Lambda copies running at once (SR-72). -1 = no reservation: the account limit (10 on 2026-11-20) is the cap, and AWS refuses any reservation while it is 10."
  type        = number
  default     = -1
}

variable "final_destroy" {
  description = "Set to true only for the final destroy (O-11): turns off deletion protection and lets ECR be deleted with images inside."
  type        = bool
  default     = false
}
