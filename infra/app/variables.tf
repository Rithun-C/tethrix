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

variable "use_custom_domain" {
  description = "Serve the app on domain_name (ADR-0006). false = API Gateway's own execute-api address, with no Route 53 zone or certificate."
  type        = bool
  # true since 2026-11-21: the registrar lifted the hold on the parent domain. Set to
  # false only to roll back to the execute-api address (docs/runbooks/deploy-manual.md).
  default = true
}

variable "disable_default_endpoint" {
  description = "With the custom domain on: switch off API Gateway's own execute-api address (T-038). false only during the first domain apply, until make smoke passes on the domain."
  type        = bool
  default     = true
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

variable "cognito_domain_prefix" {
  description = "Prefix of Cognito's hosted sign-in address, <prefix>.auth.us-east-1.amazoncognito.com. Must be unique in the region; change it if the first apply says it is taken."
  type        = string
  default     = "tethrix-app"

  validation {
    # Cognito's own rules: lower-case letters, digits and hyphens, and none of the
    # reserved words.
    condition     = can(regex("^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", var.cognito_domain_prefix)) && !can(regex("aws|amazon|cognito", var.cognito_domain_prefix))
    error_message = "Use lower-case letters, digits and hyphens, without the words aws, amazon or cognito."
  }
}
