# Infrastructure (Terraform)

This directory contains Terraform for deploying the backend API to AWS Lambda + API Gateway.

## Files

- `versions.tf` — Terraform and provider versions.
- `variables.tf` — all configurable inputs (including app env vars).
- `lambda.tf` — Lambda function, IAM role, log group.
- `apigateway.tf` — HTTP API + Lambda integration.
- `observability.tf` — CloudWatch alarms.
- `outputs.tf` — exported deployment values.
- `terraform.tfvars.example` — template input values.
- `scripts/terraform-destroy.sh` — guarded destroy helper.

## Deploy (phase 9 baseline)

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# fill terraform.tfvars values

terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

## Destroy safely

```bash
cd infra
./scripts/terraform-destroy.sh
```

The script requires typing `destroy` and uses `terraform.tfvars`.

## Notes

- Secrets are injected via Lambda environment variables for MVP (no Secrets Manager yet).
- `lambda_zip_path` expects a built deployment artifact (e.g. `../backend/dist/lambda.zip`).
- Langfuse tracing is optional. Set `langfuse_public_key`, `langfuse_secret_key`, and optionally
  `langfuse_host` in `terraform.tfvars` to enable tracing in the deployed Lambda; leave them empty
  to keep tracing disabled.
- Full CI/CD packaging and deploy automation is covered in Phase 10.
