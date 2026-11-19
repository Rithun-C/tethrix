variable "name" {
  description = "Repository name."
  type        = string
}

variable "images_to_keep" {
  description = "How many images the lifecycle rule keeps. Older ones are deleted."
  type        = number
  default     = 3

  validation {
    condition     = var.images_to_keep >= 2 && var.images_to_keep <= 10
    error_message = "Keep between 2 (current + one to roll back to) and 10 images."
  }
}

variable "force_delete" {
  description = "Allow destroy while the repository still holds images. Only for the final destroy."
  type        = bool
  default     = false
}
