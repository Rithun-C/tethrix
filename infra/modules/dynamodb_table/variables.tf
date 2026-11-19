variable "name" {
  description = "Table name."
  type        = string
}

variable "table_capacity" {
  description = "Read and write capacity units of the table."
  type        = number
  default     = 10
}

variable "index_capacity" {
  description = "Read and write capacity units of the GSI1 index."
  type        = number
  default     = 5

  validation {
    # The always-free tier is 25 read and 25 write units for the whole account.
    condition     = var.index_capacity >= 1 && var.index_capacity <= 10
    error_message = "Index capacity must be between 1 and 10 to stay inside the free tier."
  }
}

variable "deletion_protection" {
  description = "Refuse deletion. Set to false only for the final destroy."
  type        = bool
  default     = true
}
