# TerraPreview

TerraPreview is a personal SWE/infra project for learning how to build ephemeral preview environments on Google Cloud. The long-term goal is to create isolated environments for GitHub pull requests and automatically clean them up after merge or close.

Phase 1 focuses on the Terraform foundation. It gives you a simple, deployable GCP baseline that you can safely create, update, and destroy with Terraform.

Phase 2 adds a manual preview environment workflow on top of that foundation. It lets you create one isolated Cloud Run preview service per `preview_id` before adding full GitHub pull request automation later.

## What Phase 1 Creates

- A Google Cloud Storage bucket for environment artifacts
- A service account for the preview application
- Basic IAM roles for that service account
- An Artifact Registry Docker repository
- A Cloud Run service placeholder
- Terraform outputs for the main resource values you will need later

## What Phase 2 Adds

- A reusable Terraform module for per-preview Cloud Run services
- A dedicated preview Terraform environment at `infra/terraform/environments/preview`
- A manual `preview-up` workflow for creating a named preview service
- A manual `preview-down` workflow for destroying a named preview service
- Preview-specific outputs such as the preview URL, preview service name, and artifact prefix

## Project Structure

```text
terrapreview/
├── scripts/
│   ├── preview-up.sh
│   └── preview-down.sh
├── infra/
│   └── terraform/
│       ├── environments/
│       │   └── preview/
│       ├── modules/
│       │   └── preview_service/
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       ├── versions.tf
│       ├── terraform.tfvars.example
│       └── README.md
├── app/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── .gitignore
├── .dockerignore
└── README.md
```

## Prerequisites

- A Google Cloud project
- [Terraform](https://developer.hashicorp.com/terraform/downloads)
- [gcloud CLI](https://cloud.google.com/sdk/docs/install)
- [Docker](https://docs.docker.com/get-docker/)

## Authenticate with Google Cloud

Run these commands before using Terraform:

```bash
gcloud auth login
gcloud auth application-default login
gcloud config set project <PROJECT_ID>
```

## Terraform Workflow

Move into the Terraform directory first:

```bash
cd infra/terraform
```

Create your own `terraform.tfvars` from the example file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Then run the standard workflow:

```bash
terraform init
terraform validate
terraform plan
terraform apply
terraform destroy
```

What each command does:

- `terraform init` downloads the providers and prepares the working directory
- `terraform validate` checks that the Terraform configuration is valid
- `terraform plan` shows what Terraform will create or change
- `terraform apply` creates or updates the infrastructure
- `terraform destroy` deletes the temporary resources when you are done

## Build and Push the App Image

After Terraform creates Artifact Registry, use the output values and push your container image.

Set a few helpful shell variables:

```bash
export PROJECT_ID="<PROJECT_ID>"
export REGION="<REGION>"
export REPOSITORY="<ARTIFACT_REGISTRY_REPOSITORY_NAME>"
export IMAGE_NAME="terrapreview-app"
export IMAGE_TAG="phase1"
```

Build the Docker image from the `app/` directory:

```bash
cd ../../app
docker build -t ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG} .
```

Configure Docker to authenticate with Artifact Registry:

```bash
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

Push the image:

```bash
docker push ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:${IMAGE_TAG}
```

## Update the Cloud Run Image

The Terraform configuration uses a configurable `container_image` variable. After pushing your own image, update `terraform.tfvars`:

```hcl
container_image = "us-central1-docker.pkg.dev/my-project/terrapreview-dev-repo/terrapreview-app:phase1"
```

Then re-run:

```bash
cd ../infra/terraform
terraform apply
```

## Phase 2 Manual Preview Workflow

Phase 2 keeps the shared Phase 1 resources in place and adds separate preview services on demand.

Create a preview environment:

```bash
./scripts/preview-up.sh pr-123 us-central1-docker.pkg.dev/my-project/terrapreview-dev-repo/terrapreview-app:phase2
```

That command:

- reads the shared Phase 1 Terraform outputs
- creates a dedicated Cloud Run service for `pr-123`
- stores the preview in its own Terraform workspace named `pr-123`
- prints the preview service URL

Destroy a preview environment:

```bash
./scripts/preview-down.sh pr-123
```

Recommended naming examples for `preview_id`:

- `pr-123`
- `feature-login`
- `bugfix-auth`

Keep `preview_id` short and use only lowercase letters, numbers, and dashes.

## Cost Warning

Cloud Run, Artifact Registry, and Cloud Storage can incur charges if left running. Use `terraform destroy` when you are done testing Phase 1.

## What Each File Does

- `app/main.py` contains the simple FastAPI service with `/` and `/health`
- `app/requirements.txt` lists the Python dependencies for the app
- `app/Dockerfile` builds the app into a container image
- `infra/terraform/versions.tf` pins Terraform and provider versions
- `infra/terraform/modules/preview_service/` contains the reusable module for one preview Cloud Run service
- `infra/terraform/environments/preview/` contains the Terraform entrypoint for manual preview environments
- `infra/terraform/variables.tf` defines the input variables
- `infra/terraform/main.tf` creates the GCP infrastructure
- `infra/terraform/outputs.tf` prints useful values after apply
- `infra/terraform/terraform.tfvars.example` shows the variables you should fill in locally
- `infra/terraform/README.md` explains the Terraform module in more detail
- `scripts/preview-up.sh` creates or updates a named preview environment
- `scripts/preview-down.sh` destroys a named preview environment
- `.gitignore` keeps local Terraform state, variable files, and Python cache files out of Git
- `.dockerignore` keeps local cache files out of Docker build context

## First Command To Run

Start here:

```bash
cd /Users/samhitha/Documents/Projects/terrapreview/infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
```
