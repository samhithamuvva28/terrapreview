provider "google" {
  project = var.project_id
  region  = var.region
}

locals {
  name_prefix = "${var.app_name}-${var.environment}"

  common_labels = {
    app         = var.app_name
    environment = var.environment
    managed_by  = "terraform"
    project     = "terrapreview"
    phase       = "phase1"
  }
}

# This random suffix helps keep the bucket name globally unique.
resource "random_id" "bucket_suffix" {
  byte_length = 2
}

# Enable the APIs needed by the Phase 1 infrastructure.
resource "google_project_service" "required_apis" {
  for_each = toset([
    "artifactregistry.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "storage.googleapis.com",
  ])

  project            = var.project_id
  service            = each.value
  disable_on_destroy = false
}

resource "google_storage_bucket" "artifacts" {
  name                        = "${local.name_prefix}-${var.project_id}-artifacts-${random_id.bucket_suffix.hex}"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = true

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

resource "google_service_account" "preview_app" {
  account_id   = substr(replace(local.name_prefix, "-", ""), 0, 30)
  display_name = "${local.name_prefix} service account"
  description  = "Service account used by the TerraPreview Phase 1 Cloud Run service."
  project      = var.project_id

  depends_on = [google_project_service.required_apis]
}

resource "google_project_iam_member" "preview_app_storage_access" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.preview_app.email}"
}

resource "google_project_iam_member" "preview_app_log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.preview_app.email}"
}

resource "google_project_iam_member" "preview_app_artifact_registry_reader" {
  project = var.project_id
  role    = "roles/artifactregistry.reader"
  member  = "serviceAccount:${google_service_account.preview_app.email}"
}

resource "google_artifact_registry_repository" "app_images" {
  project       = var.project_id
  location      = var.region
  repository_id = "${local.name_prefix}-repo"
  description   = "Docker images for TerraPreview Phase 1."
  format        = "DOCKER"

  labels = local.common_labels

  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_v2_service" "preview_app" {
  name     = "${local.name_prefix}-service"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = local.common_labels

  template {
    service_account = google_service_account.preview_app.email

    containers {
      image = var.container_image
    }

    labels = local.common_labels
  }

  depends_on = [google_project_service.required_apis]
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.preview_app.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
