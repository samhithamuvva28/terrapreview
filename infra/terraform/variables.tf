variable "project_id" {
  description = "The Google Cloud project ID where TerraPreview resources will be created."
  type        = string
}

variable "region" {
  description = "The Google Cloud region for regional resources such as Artifact Registry and Cloud Run."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "A short environment name such as dev, staging, or preview."
  type        = string
  default     = "dev"
}

variable "app_name" {
  description = "The application name used in resource naming."
  type        = string
  default     = "terrapreview"
}

variable "container_image" {
  description = "The container image to deploy to Cloud Run. You can keep the default sample image or replace it with your own Artifact Registry image later."
  type        = string
  default     = "us-docker.pkg.dev/cloudrun/container/hello"
}

variable "firestore_collection_name" {
  description = "Firestore collection name used by the TerraPreview control plane metadata API."
  type        = string
  default     = "preview_records"
}

variable "existing_artifact_bucket_name" {
  description = "Optional existing Cloud Storage bucket name to keep using for TerraPreview artifacts. Set this when importing an existing shared foundation."
  type        = string
  default     = ""
}
