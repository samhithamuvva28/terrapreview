locals {
  preview_name = "${var.app_name}-${var.environment}-${var.preview_id}"

  common_labels = {
    app         = var.app_name
    environment = var.environment
    managed_by  = "terraform"
    phase       = "phase2"
    preview_id  = var.preview_id
    project     = "terrapreview"
  }

  artifact_prefix = "previews/${var.preview_id}/"
}

resource "google_cloud_run_v2_service" "preview" {
  name     = local.preview_name
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_ALL"

  labels = local.common_labels

  template {
    service_account = var.service_account_email

    containers {
      image = var.container_image

      env {
        name  = "TERRAPREVIEW_ENVIRONMENT"
        value = var.environment
      }

      env {
        name  = "TERRAPREVIEW_PREVIEW_ID"
        value = var.preview_id
      }

      env {
        name  = "TERRAPREVIEW_ARTIFACT_BUCKET"
        value = var.artifact_bucket_name
      }

      env {
        name  = "TERRAPREVIEW_ARTIFACT_PREFIX"
        value = local.artifact_prefix
      }
    }

    labels = local.common_labels
  }
}

resource "google_cloud_run_v2_service_iam_member" "public_invoker" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.preview.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
