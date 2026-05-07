output "preview_id" {
  description = "Preview identifier used for this deployment."
  value       = var.preview_id
}

output "service_name" {
  description = "Cloud Run service name for this preview environment."
  value       = google_cloud_run_v2_service.preview.name
}

output "service_url" {
  description = "Public Cloud Run URL for this preview environment."
  value       = google_cloud_run_v2_service.preview.uri
}

output "container_image" {
  description = "Container image deployed to this preview environment."
  value       = var.container_image
}

output "artifact_prefix" {
  description = "Artifact bucket prefix reserved for this preview environment."
  value       = local.artifact_prefix
}
