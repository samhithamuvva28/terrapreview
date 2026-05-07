# Preview Environment Terraform

This directory contains the Phase 2 Terraform configuration for a single manual preview environment.

It does not recreate the shared foundation from Phase 1. Instead, it reuses:

- the shared TerraPreview service account
- the shared artifacts bucket
- the shared Artifact Registry repository

Each preview deployment creates a separate Cloud Run service, such as `terrapreview-dev-pr-123`.

## Typical Usage

You can either use the helper scripts from the repository root, or run Terraform here directly.

### Recommended: helper scripts

From the repository root:

```bash
./scripts/preview-up.sh pr-123 us-central1-docker.pkg.dev/my-project/terrapreview-dev-repo/terrapreview-app:phase2
./scripts/preview-down.sh pr-123
```

The helper scripts create one Terraform workspace per preview ID so multiple previews can coexist without overwriting each other.

### Direct Terraform usage

If you want to run Terraform manually in this directory, create a local `terraform.tfvars` based on the example file and fill in the shared values from Phase 1.

Then run:

```bash
terraform init
terraform plan
terraform apply
terraform destroy
```

## Outputs

After apply, Terraform prints:

- preview ID
- preview service name
- preview service URL
- preview container image
- preview artifact prefix
