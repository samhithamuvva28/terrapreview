provider "google" {
  project = var.project_id
  region  = var.region
}

module "preview_service" {
  source = "../../modules/preview_service"

  project_id            = var.project_id
  region                = var.region
  environment           = var.environment
  app_name              = var.app_name
  preview_id            = var.preview_id
  container_image       = var.container_image
  service_account_email = var.service_account_email
  artifact_bucket_name  = var.artifact_bucket_name
}
