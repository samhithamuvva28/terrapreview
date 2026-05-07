# TerraPreview

TerraPreview is a personal SWE/infra project for learning how to build ephemeral preview environments on Google Cloud. The long-term goal is to create isolated environments for GitHub pull requests and automatically clean them up after merge or close.

Phase 1 focuses only on the Terraform foundation. It gives you a simple, deployable GCP baseline that you can safely create, update, and destroy with Terraform.

## What Phase 1 Creates

- A Google Cloud Storage bucket for environment artifacts
- A service account for the preview application
- Basic IAM roles for that service account
- An Artifact Registry Docker repository
- A Cloud Run service placeholder
- Terraform outputs for the main resource values you will need later

## Project Structure

```text
terrapreview/
├── infra/
│   └── terraform/
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

## Cost Warning

Cloud Run, Artifact Registry, and Cloud Storage can incur charges if left running. Use `terraform destroy` when you are done testing Phase 1.

## What Each File Does

- `app/main.py` contains the simple FastAPI service with `/` and `/health`
- `app/requirements.txt` lists the Python dependencies for the app
- `app/Dockerfile` builds the app into a container image
- `infra/terraform/versions.tf` pins Terraform and provider versions
- `infra/terraform/variables.tf` defines the input variables
- `infra/terraform/main.tf` creates the GCP infrastructure
- `infra/terraform/outputs.tf` prints useful values after apply
- `infra/terraform/terraform.tfvars.example` shows the variables you should fill in locally
- `infra/terraform/README.md` explains the Terraform module in more detail
- `.gitignore` keeps local Terraform state, variable files, and Python cache files out of Git

## First Command To Run

Start here:

```bash
cd /Users/samhitha/Documents/ReferU.AI/LRA/LegalResarchAgent/terrapreview/infra/terraform
cp terraform.tfvars.example terraform.tfvars
terraform init
```
