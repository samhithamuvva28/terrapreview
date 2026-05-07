#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: ./scripts/preview-up.sh <preview-id> <container-image>"
  exit 1
fi

PREVIEW_ID="$1"
CONTAINER_IMAGE="$2"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="${ROOT_DIR}/infra/terraform"
PREVIEW_DIR="${BASE_DIR}/environments/preview"
TFVARS_FILE="${BASE_DIR}/terraform.tfvars"

if [[ ! "${PREVIEW_ID}" =~ ^[a-z0-9-]+$ ]]; then
  echo "preview-id must contain only lowercase letters, numbers, and dashes."
  exit 1
fi

if [[ ! -f "${TFVARS_FILE}" ]]; then
  echo "Shared Terraform variables were not found at ${TFVARS_FILE}."
  echo "Create ${TFVARS_FILE} from terraform.tfvars.example first."
  exit 1
fi

PROJECT_ID="$(sed -n 's/^project_id[[:space:]]*=[[:space:]]*"\(.*\)"$/\1/p' "${TFVARS_FILE}" | head -n 1)"
REGION="$(sed -n 's/^region[[:space:]]*=[[:space:]]*"\(.*\)"$/\1/p' "${TFVARS_FILE}" | head -n 1)"
ENVIRONMENT="$(sed -n 's/^environment[[:space:]]*=[[:space:]]*"\(.*\)"$/\1/p' "${TFVARS_FILE}" | head -n 1)"
APP_NAME="$(sed -n 's/^app_name[[:space:]]*=[[:space:]]*"\(.*\)"$/\1/p' "${TFVARS_FILE}" | head -n 1)"

if [[ -f "${BASE_DIR}/terraform.tfstate" ]]; then
  SERVICE_ACCOUNT_EMAIL="$(terraform -chdir="${BASE_DIR}" output -raw service_account_email)"
  ARTIFACT_BUCKET_NAME="$(terraform -chdir="${BASE_DIR}" output -raw bucket_name)"
else
  if ! command -v gcloud >/dev/null 2>&1; then
    echo "gcloud is required when ${BASE_DIR}/terraform.tfstate is not present."
    exit 1
  fi

  SERVICE_ACCOUNT_EMAIL="$(gcloud iam service-accounts list \
    --project="${PROJECT_ID}" \
    --filter="email~^${APP_NAME}${ENVIRONMENT}@${PROJECT_ID}\\.iam\\.gserviceaccount\\.com$" \
    --format="value(email)" | head -n 1)"

  ARTIFACT_BUCKET_NAME="$(gcloud storage buckets list \
    --project="${PROJECT_ID}" \
    --filter="name~^${APP_NAME}-${ENVIRONMENT}-${PROJECT_ID}-artifacts-" \
    --format="value(name)" | head -n 1)"
fi

if [[ -z "${PROJECT_ID}" || -z "${REGION}" || -z "${ENVIRONMENT}" || -z "${APP_NAME}" ]]; then
  echo "Could not read shared values from ${TFVARS_FILE}."
  exit 1
fi

if [[ -z "${SERVICE_ACCOUNT_EMAIL}" || -z "${ARTIFACT_BUCKET_NAME}" ]]; then
  echo "Could not discover the shared Phase 1 service account or bucket."
  echo "Make sure the shared foundation exists in project ${PROJECT_ID}."
  exit 1
fi

terraform -chdir="${PREVIEW_DIR}" init

if terraform -chdir="${PREVIEW_DIR}" workspace list | tr -d '* ' | grep -Fxq "${PREVIEW_ID}"; then
  terraform -chdir="${PREVIEW_DIR}" workspace select "${PREVIEW_ID}"
else
  terraform -chdir="${PREVIEW_DIR}" workspace new "${PREVIEW_ID}"
fi

terraform -chdir="${PREVIEW_DIR}" apply \
  -auto-approve \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="environment=${ENVIRONMENT}" \
  -var="app_name=${APP_NAME}" \
  -var="preview_id=${PREVIEW_ID}" \
  -var="container_image=${CONTAINER_IMAGE}" \
  -var="service_account_email=${SERVICE_ACCOUNT_EMAIL}" \
  -var="artifact_bucket_name=${ARTIFACT_BUCKET_NAME}"

echo
echo "Preview environment is ready."
echo "Preview URL: $(terraform -chdir="${PREVIEW_DIR}" output -raw preview_service_url)"
