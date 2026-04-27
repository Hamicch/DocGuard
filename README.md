# DocGuard

> AI-powered GitHub PR reviewer that detects documentation drift and style violations, posts structured findings on the PR, and stores run history in a dashboard.

## What it does

- Receives `pull_request` webhooks from GitHub
- Fetches changed `.py` and `.md` files at the PR's `head_sha` via the GitHub REST API
- Indexes Python symbols (AST) and Markdown doc sections, links them, and infers code conventions (LLM)
- Judges documentation drift and style violations with structured LLM output
- Posts a grouped Markdown comment on the PR
- Persists every run and finding to Supabase; surfaces them in a Next.js dashboard

## Repo layout

```
docguard/
├── backend/        # Python 3.12 FastAPI → AWS Lambda
├── frontend/       # Next.js 15 dashboard → Vercel
├── infra/          # Terraform (API Gateway, Lambda, CloudWatch)
├── architecture/   # System diagram + README
└── tasks/          # todo.md, progress.md, lessons.md (agent coordination)
```

## Quick start (local)

```bash
cp backend/.env.example backend/.env   # fill in secrets
docker compose up
```

## Infrastructure (Phase 9)

Terraform scaffolding for AWS Lambda + API Gateway now lives in `infra/`.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# fill values
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

Safe teardown helper:

```bash
cd infra
./scripts/terraform-destroy.sh
```

## Documentation

- [Product spec](doc/PRODUCT_DOCUMENT.md)
- [Implementation guide](doc/IMPLEMENTATION_GUIDE.md)
- [Architecture diagram](architecture/README.md)
- [Infrastructure docs](infra/README.md)
- [Task board](tasks/todo.md)
