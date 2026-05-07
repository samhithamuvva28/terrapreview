output "preview_id" {
  description = "Preview identifier used for this deployment."
  value       = module.preview_service.preview_id
}

output "preview_service_name" {
  description = "Cloud Run service name for this preview environment."
  value       = module.preview_service.service_name
}

output "preview_service_url" {
  description = "Public Cloud Run URL for this preview environment."
  value       = module.preview_service.service_url
}

output "preview_container_image" {
  description = "Container image deployed to this preview environment."
  value       = module.preview_service.container_image
}

output "preview_artifact_prefix" {
  description = "Artifact bucket prefix reserved for this preview environment."
  value       = module.preview_service.artifact_prefix
}
