output "bucket_name" {
  description = "Name of the Cloud Storage bucket used for environment artifacts."
  value       = google_storage_bucket.artifacts.name
}

output "project_id" {
  description = "Google Cloud project ID used by the shared TerraPreview foundation."
  value       = var.project_id
}

output "region" {
  description = "Default region used by the shared TerraPreview foundation."
  value       = var.region
}

output "environment" {
  description = "Environment name used by the shared TerraPreview foundation."
  value       = var.environment
}

output "app_name" {
  description = "Application name used by the shared TerraPreview foundation."
  value       = var.app_name
}

output "service_account_email" {
  description = "Email address of the TerraPreview service account."
  value       = google_service_account.preview_app.email
}

output "artifact_registry_repository" {
  description = "Artifact Registry repository name for Docker images."
  value       = google_artifact_registry_repository.app_images.repository_id
}

output "cloud_run_service_url" {
  description = "Public URL of the Cloud Run service."
  value       = google_cloud_run_v2_service.preview_app.uri
}

output "firestore_collection_name" {
  description = "Firestore collection used by the TerraPreview control plane metadata API."
  value       = var.firestore_collection_name
}
