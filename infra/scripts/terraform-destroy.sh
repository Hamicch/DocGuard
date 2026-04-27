#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f "terraform.tfvars" ]]; then
  echo "Missing infra/terraform.tfvars"
  echo "Copy infra/terraform.tfvars.example to infra/terraform.tfvars and fill values first."
  exit 1
fi

echo "About to destroy Terraform-managed infrastructure in: $ROOT_DIR"
read -r -p "Type 'destroy' to continue: " CONFIRM
if [[ "$CONFIRM" != "destroy" ]]; then
  echo "Aborted."
  exit 1
fi

terraform init
terraform destroy -var-file="terraform.tfvars" -auto-approve "$@"
