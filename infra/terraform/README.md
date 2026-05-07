# Shared Terraform Foundation

This directory contains the shared Terraform foundation for TerraPreview on Google Cloud Platform.

Phase 1 creates the reusable base resources.
Phase 2 preview environments build on top of this foundation instead of recreating it.

## Resources Created

- Google provider configuration
- Cloud Storage bucket for artifacts
- Service account for the preview app
- Basic IAM roles for storage access and logging
- Artifact Registry Docker repository
- Shared Cloud Run service
- Outputs for the main resource values

## Files

- `versions.tf` defines the Terraform and provider versions
- `variables.tf` defines the input variables
- `main.tf` creates the GCP resources
- `outputs.tf` prints helpful values after deployment
- `terraform.tfvars.example` shows sample variable values you can copy into a real local `terraform.tfvars`

## Phase 2 Preview Layer

Manual preview environments live under:

```text
environments/preview/
```

That directory reuses the shared outputs from this foundation, especially:

- `project_id`
- `region`
- `environment`
- `app_name`
- `service_account_email`
- `bucket_name`

## Usage

1. Copy the example variable file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

2. Edit `terraform.tfvars` with your GCP project values.

3. Run Terraform:

```bash
terraform init
terraform validate
terraform plan
terraform apply
```

4. Destroy the resources when you no longer need them:

```bash
terraform destroy
```

## Notes

- Bucket names must be globally unique, so this module adds a small random suffix to the bucket name.
- The default Cloud Run image is a public sample container so you can test infrastructure before building your own app image.
- When you are ready to use your own container, update `container_image` and run `terraform apply` again.
- The helper scripts in `scripts/preview-up.sh` and `scripts/preview-down.sh` use the outputs from this directory to create and destroy preview-specific services in Phase 2.
