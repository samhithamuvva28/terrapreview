variable "project_id" {
  description = "The Google Cloud project ID where preview services will be created."
  type        = string
}

variable "region" {
  description = "The Google Cloud region where preview services will be created."
  type        = string
}

variable "environment" {
  description = "The shared environment label, such as dev."
  type        = string
}

variable "app_name" {
  description = "The application name used in preview resource naming."
  type        = string
}

variable "preview_id" {
  description = "A short preview identifier such as pr-123 or feature-login."
  type        = string
}

variable "container_image" {
  description = "Container image to deploy for the preview service."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "service_account_email" {
  description = "Shared service account email created by the base TerraPreview foundation."
  type        = string
}

variable "artifact_bucket_name" {
  description = "Shared artifact bucket created by the base TerraPreview foundation."
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
