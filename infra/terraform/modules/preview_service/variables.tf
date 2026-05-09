variable "project_id" {
  description = "The Google Cloud project ID where the preview service will be created."
  type        = string
}

variable "region" {
  description = "The Google Cloud region where the preview service will be created."
  type        = string
}

variable "environment" {
  description = "The shared environment label, such as dev or staging."
  type        = string
}

variable "app_name" {
  description = "The application name used in preview resource naming."
  type        = string
}

variable "preview_id" {
  description = "A short preview identifier such as pr-123 or feature-login. Use lowercase letters, numbers, and dashes only."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.preview_id)) && length(var.preview_id) <= 20
    error_message = "preview_id must be 20 characters or fewer and contain only lowercase letters, numbers, and dashes."
  }
}

variable "container_image" {
  description = "Container image to deploy for this preview service."
  type        = string
}

variable "service_account_email" {
  description = "Shared service account email that the preview Cloud Run service should use."
  type        = string
}

variable "artifact_bucket_name" {
  description = "Shared artifact bucket name created by the base TerraPreview foundation."
  type        = string
}

variable "git_branch" {
  description = "Optional Git branch name associated with this preview deployment."
  type        = string
  default     = ""
}

variable "git_sha" {
  description = "Optional Git commit SHA associated with this preview deployment."
  type        = string
  default     = ""
}

variable "pr_number" {
  description = "Optional pull request number associated with this preview deployment."
  type        = string
  default     = ""
}
