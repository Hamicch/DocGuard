# Code Review Agent — Implementation Guide

> **Complete technical specification for building the MVP. Hand this to any senior engineer or coding agent and they can build it from scratch.**

---

## Project Overview

**Name**: Code Review Agent (working name: `doc-drift`)  
**Goal**: AI-powered agent that watches GitHub PRs, detects documentation drift + code style violations, posts structured feedback  
**Timeline**: 8-hour MVP build  
**Deployment**: AWS Lambda + API Gateway + Supabase, provisioned via Terraform

---

## Complete Folder Structure

```
code-review-agent/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml              # Local development
├── Dockerfile.api                  # FastAPI service
├── pyproject.toml                  # Python dependencies (uv)
├── uv.lock
│
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app factory
│   ├── config.py                   # Pydantic Settings
│   │
│   ├── domain/                     # Pure business models
│   │   ├── __init__.py
│   │   ├── repo.py
│   │   ├── audit_run.py
│   │   ├── finding.py
│   │   └── pr_event.py
│   │
│   ├── services/                   # Use cases / orchestration
│   │   ├── __init__.py
│   │   ├── audit_service.py        # Main audit orchestrator
│   │   ├── indexer_service.py      # Code + doc indexing
│   │   ├── convention_service.py   # Extract conventions
│   │   ├── drift_service.py        # Drift detection
│   │   ├── style_service.py        # Style violation detection
│   │   └── github_service.py       # GitHub interactions
│   │
│   ├── adapters/                   # External integrations
│   │   ├── __init__.py
│   │   ├── parsers/
│   │   │   ├── __init__.py
│   │   │   ├── python_parser.py    # AST indexing
│   │   │   └── markdown_parser.py  # Markdown parsing
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # LLMProvider port
│   │   │   └── openrouter.py       # OpenRouter adapter
│   │   ├── github/
│   │   │   ├── __init__.py
│   │   │   ├── webhook.py          # Webhook verification
│   │   │   └── api_client.py       # GitHub REST API
│   │   └── auth/
│   │       ├── __init__.py
│   │       └── supabase_auth.py    # JWT verification
│   │
│   ├── repositories/               # Data access
│   │   ├── __init__.py
│   │   ├── base.py                 # Generic repo pattern
│   │   ├── repo_repository.py
│   │   ├── audit_run_repository.py
│   │   └── finding_repository.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py              # SQLAlchemy async session
│   │   ├── models.py               # ORM models
│   │   └── migrations/             # Alembic
│   │       ├── alembic.ini
│   │       ├── env.py
│   │       └── versions/
│   │           └── 001_initial.py
│   │
│   ├── api/                        # FastAPI routes
│   │   ├── __init__.py
│   │   ├── deps.py                 # Dependency injection
│   │   ├── webhooks/
│   │   │   ├── __init__.py
│   │   │   └── github.py           # POST /webhooks/github
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── runs.py             # GET /api/runs, /api/runs/{id}
│   │   │   ├── findings.py         # POST /api/findings/{id}/action
│   │   │   └── repos.py            # GET/POST /api/repos
│   │   └── schemas/                # Pydantic request/response models
│   │       ├── __init__.py
│   │       ├── run.py
│   │       ├── finding.py
│   │       └── repo.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging.py              # Structured JSON logging
│   │   └── cost_tracker.py         # LLM token/cost tracking
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py             # Shared fixtures
│       ├── unit/
│       │   ├── test_python_parser.py
│       │   ├── test_markdown_parser.py
│       │   ├── test_drift_service.py
│       │   └── test_style_service.py
│       ├── integration/
│       │   ├── test_api_runs.py
│       │   ├── test_audit_service.py
│       │   └── test_repositories.py
│       └── e2e/
│           └── test_full_webhook_flow.py
│
├── frontend/                       # Next.js dashboard
│   ├── package.json
│   ├── next.config.js
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── .env.local.example
│   │
│   ├── app/
│   │   ├── layout.tsx              # Root layout with providers
│   │   ├── page.tsx                # Redirect to /dashboard
│   │   ├── login/
│   │   │   └── page.tsx            # Supabase Auth UI
│   │   ├── dashboard/
│   │   │   ├── layout.tsx          # Protected layout
│   │   │   ├── page.tsx            # Runs list
│   │   │   └── runs/
│   │   │       └── [id]/
│   │   │           └── page.tsx    # Run detail + findings
│   │   └── api/                    # Next.js API routes (if needed)
│   │
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── table.tsx
│   │   │   └── badge.tsx
│   │   ├── auth-provider.tsx       # Supabase auth context
│   │   ├── run-card.tsx
│   │   ├── finding-card.tsx
│   │   └── code-diff.tsx
│   │
│   ├── lib/
│   │   ├── supabase.ts             # Supabase client
│   │   ├── api-client.ts           # Typed fetch to FastAPI
│   │   └── types.ts                # Shared types
│   │
│   └── public/
│       └── logo.svg
│
├── infra/                          # Terraform
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── terraform.tfvars.example
│   │
│   ├── modules/
│   │   ├── apigateway/
│   │   │   ├── main.tf             # HTTP API, routes, stage
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── lambda/
│   │   │   ├── main.tf             # Function, IAM, optional SQS event source
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   ├── ecr/                    # optional: container-image Lambda
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   └── outputs.tf
│   │   └── networking/             # optional: VPC for Lambda (often skipped with Supabase)
│   │       ├── main.tf
│   │       ├── variables.tf
│   │       └── outputs.tf
│   │
│   └── environments/
│       └── dev/
│           └── terraform.tfvars
│
├── scripts/
│   ├── setup-dev.sh                # Local dev setup
│   ├── build-and-push.sh           # Docker build + ECR push
│   ├── run-migrations.sh           # Alembic migrations
│   ├── seed-test-data.sh           # Insert test repos/runs
│   └── generate-github-app-jwt.py  # GitHub App JWT for testing
│
├── .github/
│   └── workflows/
│       ├── ci.yml                  # Lint, test, type-check
│       └── deploy.yml              # Build, push, terraform apply
│
└── docs/
    ├── SETUP.md                    # Local setup guide
    ├── DEPLOYMENT.md               # Production deployment
    ├── API.md                      # API documentation
    └── ARCHITECTURE.md             # Architecture decisions
```

---

## Tech Stack Versions

```toml
[project]
name = "code-review-agent"
version = "0.1.0"
requires-python = ">=3.12"

dependencies = [
    "fastapi==0.115.0",
    "uvicorn[standard]==0.32.0",
    "pydantic==2.9.2",
    "pydantic-settings==2.6.1",
    "sqlalchemy[asyncio]==2.0.36",
    "alembic==1.14.0",
    "asyncpg==0.30.0",               # Postgres async driver
    "httpx==0.27.2",
    "openai==1.54.4",                # OpenAI SDK (points to OpenRouter)
    "PyGithub==2.4.0",
    "python-jose[cryptography]==3.3.0",  # JWT verification
    "markdown-it-py==3.0.0",
    "python-multipart==0.0.12",
    "structlog==24.4.0",             # Structured logging
]

[project.optional-dependencies]
dev = [
    "ruff==0.7.4",
    "mypy==1.13.0",
    "pytest==8.3.3",
    "pytest-asyncio==0.24.0",
    "pytest-cov==6.0.0",
    "respx==0.21.1",                 # Mock HTTP
    "faker==33.1.0",
]
```

Frontend (package.json):
```json
{
  "name": "code-review-agent-frontend",
  "version": "0.1.0",
  "dependencies": {
    "next": "15.0.3",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@supabase/supabase-js": "^2.45.4",
    "@supabase/auth-ui-react": "^0.4.7",
    "@supabase/auth-ui-shared": "^0.1.8",
    "tailwindcss": "^3.4.14",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "lucide-react": "^0.454.0"
  },
  "devDependencies": {
    "typescript": "^5.6.3",
    "@types/node": "^22.8.6",
    "@types/react": "^18.3.11",
    "eslint": "^9.13.0",
    "eslint-config-next": "15.0.3"
  }
}
```

---

## Environment Variables

### Backend (.env)

```bash
# App
ENVIRONMENT=development
LOG_LEVEL=INFO

# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbG...
SUPABASE_SERVICE_ROLE_KEY=eyJhbG...
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-settings

# Database (Supabase Postgres connection string)
DATABASE_URL=postgresql+asyncpg://postgres:password@db.xxxxx.supabase.co:5432/postgres

# GitHub
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# OpenRouter
OPENROUTER_API_KEY=sk-or-v1-xxxxx
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# AWS (for deployed environment)
AWS_REGION=us-east-1

# Note: In production, pass sensitive values as **Lambda environment variables** set by Terraform / CI (no AWS Secrets Manager for MVP).
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbG...
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000  # or deployed API Gateway invoke URL
```

---

## Database Schema (Alembic Migration)

File: `backend/db/migrations/versions/001_initial.py`

```python
"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2026-04-26
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # repos table
    op.create_table(
        'repos',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('full_name', sa.Text, nullable=False),
        sa.Column('github_installation_id', sa.BigInteger),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_unique_constraint('uq_repos_user_full_name', 'repos', ['user_id', 'full_name'])
    op.create_index('idx_repos_user', 'repos', ['user_id'])

    # audit_runs table
    op.create_table(
        'audit_runs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('repo_id', UUID(as_uuid=True), sa.ForeignKey('repos.id')),
        sa.Column('pr_number', sa.Integer, nullable=False),
        sa.Column('pr_title', sa.Text),
        sa.Column('pr_author', sa.Text),
        sa.Column('pr_url', sa.Text),
        sa.Column('head_sha', sa.Text),
        sa.Column('status', sa.Text, nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('finished_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('duration_ms', sa.Integer),
        sa.Column('error_message', sa.Text),
        sa.Column('total_findings', sa.Integer, server_default='0'),
        sa.Column('doc_drift_count', sa.Integer, server_default='0'),
        sa.Column('style_violation_count', sa.Integer, server_default='0'),
        sa.Column('convention_violation_count', sa.Integer, server_default='0'),
        sa.Column('llm_tokens_used', sa.Integer, server_default='0'),
        sa.Column('cost_estimate_usd', sa.Numeric(10, 4), server_default='0'),
        sa.Column('pr_comment_id', sa.BigInteger),
        sa.Column('pr_comment_url', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_runs_user_created', 'audit_runs', ['user_id', 'created_at'])
    op.create_index('idx_runs_repo_pr', 'audit_runs', ['repo_id', 'pr_number'])

    # findings table
    op.create_table(
        'findings',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', UUID(as_uuid=True), sa.ForeignKey('audit_runs.id', ondelete='CASCADE')),
        sa.Column('finding_type', sa.Text, nullable=False),
        sa.Column('severity', sa.Text, nullable=False),
        sa.Column('file_path', sa.Text, nullable=False),
        sa.Column('line_number', sa.Integer),
        sa.Column('title', sa.Text, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('current_code', sa.Text),
        sa.Column('current_doc', sa.Text),
        sa.Column('proposed_fix', sa.Text),
        sa.Column('reasoning', sa.Text),
        sa.Column('confidence', sa.Numeric(3, 2)),
        sa.Column('user_action', sa.Text),
        sa.Column('user_action_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('user_custom_fix', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_findings_run', 'findings', ['run_id'])
    op.create_index('idx_findings_type_severity', 'findings', ['finding_type', 'severity'])

def downgrade() -> None:
    op.drop_table('findings')
    op.drop_table('audit_runs')
    op.drop_table('repos')
```

---

## API Contracts

### POST /webhooks/github

**Request**: GitHub webhook payload (JSON)
**Headers**: 
- `X-Hub-Signature-256`: HMAC signature
- `X-GitHub-Event`: `pull_request`

**Response**: `202 Accepted` after the audit is **enqueued** (e.g. background task). Body optional for GitHub; include JSON for operators and tests:

```json
{
  "status": "triggered",
  "run_id": "uuid"
}
```

### GET /api/runs

**Auth**: Bearer JWT (Supabase)
**Query params**: 
- `limit` (optional, default 20)
- `offset` (optional, default 0)

**Response**:
```json
{
  "runs": [
    {
      "id": "uuid",
      "repo_name": "owner/repo",
      "pr_number": 42,
      "pr_title": "Add feature X",
      "status": "completed",
      "started_at": "2026-04-26T10:30:00Z",
      "total_findings": 3,
      "doc_drift_count": 1,
      "style_violation_count": 2
    }
  ],
  "total": 10
}
```

### GET /api/runs/{id}

**Auth**: Bearer JWT
**Response**:
```json
{
  "run": {
    "id": "uuid",
    "repo_name": "owner/repo",
    "pr_number": 42,
    "pr_url": "https://github.com/...",
    "status": "completed",
    "started_at": "...",
    "finished_at": "...",
    "duration_ms": 35000,
    "findings": [
      {
        "id": "uuid",
        "finding_type": "doc_drift",
        "severity": "high",
        "file_path": "src/auth.py",
        "line_number": 45,
        "title": "Function renamed but docs not updated",
        "current_code": "def find_user(id: str):",
        "current_doc": "Call `get_user(id)` to retrieve...",
        "proposed_fix": "Call `find_user(id)` to retrieve...",
        "reasoning": "Function was renamed from get_user to find_user..."
      }
    ]
  }
}
```

### POST /api/findings/{id}/action

**Auth**: Bearer JWT
**Body**:
```json
{
  "action": "accepted" | "ignored" | "custom",
  "custom_fix": "optional custom fix text"
}
```

**Response**: `204 No Content`

---

## Core Service Logic (canonical pipeline)

This matches `PRODUCT_DOCUMENT.md` (PR diff and files via **GitHub REST API**, no full repo clone on disk) and `tasks/todo.md` Phase 6. Names like `AuditService` vs `audit_orchestrator` are interchangeable; the **order of steps** is what implementations must follow.

### Ordered steps (one PR audit)

1. **Persist run start** — Insert `audit_runs` row (`status=running`, `started_at`, PR metadata from webhook or API).
2. **Fetch PR metadata** — Title, author, URL, `head_sha`, changed file list (GitHub API).
3. **Fetch content for indexing** — For each relevant `.py` / `.md` path at `head_sha`, `get_file_contents` (or batch APIs). Keep blobs in memory. No git clone in MVP.
4. **Build indexes** — AST symbols from Python text; doc sections from Markdown text (same parsers as a clone-based design, different input source).
5. **Link docs to code** — Produce `(doc_section, code_symbol)` pairs for drift judging.
6. **Extract conventions** — LLM over a small sample of existing file texts; cache key includes `head_sha` (or base ref) so unchanged trees do not re-pay the call.
7. **Fetch unified diff** — Raw diff text for the PR for change detection and style scope.
8. **Analyze diff** — Map hunks to symbols and new code regions.
9. **Judge drift** — LLM structured output per linked pair where code changed.
10. **Judge style** — LLM structured output for new/changed regions vs `ConventionSet`.
11. **Draft fixes** — Optional pass to enrich `proposed_fix` where judges left gaps.
12. **Persist findings** — Bulk insert rows; update run counters, token/cost totals.
13. **Format PR comment** — Single Markdown comment grouped by finding type and severity.
14. **Post or update comment** — Create comment or update existing `pr_comment_id` on re-run.
15. **Finalize run** — `status=completed`, `finished_at`, `duration_ms`, store `pr_comment_id` / URL. On any failure after step 1, set `status=failed`, `error_message`, `finished_at`, then re-raise or log.

Webhook handler returns **202** quickly after enqueueing this pipeline. On **Lambda**, use **async `lambda:InvokeFunction`** on an **audit** function or **SQS** (not only `asyncio.create_task`, or the platform may cut off work when the handler returns). Response body may include `run_id` for tracing.

### audit_service.py (pseudocode, API-backed)

```python
from datetime import UTC, datetime

class AuditService:
    async def run_pr_audit(
        self,
        repo: Repo,
        pr_number: int,
        head_sha: str,
    ) -> AuditRun:
        run = await self.run_repo.create(
            AuditRun(
                user_id=repo.user_id,
                repo_id=repo.id,
                pr_number=pr_number,
                head_sha=head_sha,
                status="running",
                started_at=datetime.now(UTC),
            )
        )

        try:
            pr_data = await self.github.get_pr(repo.full_name, pr_number)

            file_blobs = await self.github.fetch_pr_files_text(
                repo.full_name, pr_number, head_sha
            )
            code_index = await self.indexer.index_python_files(file_blobs)
            doc_index = await self.indexer.index_markdown_files(file_blobs)

            linked = await self.linker.link(doc_index, code_index)

            conventions = await self.convention_service.extract(
                code_index, cache_key=head_sha
            )

            diff_text = await self.github.get_pr_diff(repo.full_name, pr_number)
            diff_view = await self.diff_analyzer.analyze(diff_text, code_index)

            drift_raw = await self.drift_service.judge(linked, diff_view, pr_data)
            style_raw = await self.style_service.judge(diff_view, conventions)

            findings = await self.fix_drafter.enrich(drift_raw + style_raw)

            await self.finding_repo.bulk_create(run.id, findings)

            body = self.comment_formatter.render(findings)
            comment_id = await self.github.upsert_pr_comment(
                repo.full_name, pr_number, body, existing_id=run.pr_comment_id
            )

            run.status = "completed"
            run.finished_at = datetime.now(UTC)
            run.total_findings = len(findings)
            run.pr_comment_id = comment_id
            await self.run_repo.update(run)
            return run

        except Exception as e:
            run.status = "failed"
            run.error_message = str(e)
            run.finished_at = datetime.now(UTC)
            await self.run_repo.update(run)
            raise
```

---

## Dockerfile

File: `Dockerfile.api`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Run
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Docker Compose (Local Dev)

File: `docker-compose.yml`

```yaml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: code_review_agent
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@postgres:5432/code_review_agent
      SUPABASE_URL: ${SUPABASE_URL}
      SUPABASE_JWT_SECRET: ${SUPABASE_JWT_SECRET}
      GITHUB_APP_ID: ${GITHUB_APP_ID}
      GITHUB_APP_PRIVATE_KEY: ${GITHUB_APP_PRIVATE_KEY}
      GITHUB_WEBHOOK_SECRET: ${GITHUB_WEBHOOK_SECRET}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    ports:
      - "8000:8000"
    depends_on:
      - postgres
    volumes:
      - ./backend:/app/backend

volumes:
  postgres_data:
```

---

## Terraform Main

File: `infra/main.tf`

**Compute note**: The project targets **Lambda + API Gateway**. The HCL sketch below still shows **ECS-style modules** as a structural placeholder; replace with `aws_lambda_function`, `aws_apigatewayv2_api`, IAM roles, and optional `aws_sqs_queue` for an audit worker.

**Note on GitHub App Private Key**: The private key is a multiline PEM file. In Terraform, pass it as a single-line string with `\n` for newlines and map it into the Lambda **`environment`** block (sourced from a Terraform variable or CI secret at deploy time). **No Secrets Manager** for MVP.

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "your-terraform-state-bucket"
    key    = "code-review-agent/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region
}

module "networking" {
  source = "./modules/networking"
  
  project_name = var.project_name
  environment  = var.environment
}

module "ecr" {
  source = "./modules/ecr"
  
  repository_name = "${var.project_name}-api"
}

module "alb" {
  source = "./modules/alb"
  
  project_name   = var.project_name
  vpc_id         = module.networking.vpc_id
  public_subnets = module.networking.public_subnet_ids
}

module "ecs" {
  source = "./modules/ecs"
  
  project_name    = var.project_name
  environment     = var.environment
  vpc_id          = module.networking.vpc_id
  private_subnets = module.networking.private_subnet_ids
  alb_target_group_arn = module.alb.target_group_arn
  ecr_repository_url   = module.ecr.repository_url
  
  # Secrets
  supabase_url        = var.supabase_url
  supabase_jwt_secret = var.supabase_jwt_secret
  database_url        = var.database_url
  github_app_id       = var.github_app_id
  github_app_private_key = var.github_app_private_key
  github_webhook_secret = var.github_webhook_secret
  openrouter_api_key  = var.openrouter_api_key
}
```

---

## GitHub Actions CI/CD

File: `.github/workflows/deploy.yml`

```yaml
name: Deploy

on:
  push:
    branches: [main]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: code-review-agent-api

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Install dependencies
        run: uv sync
      
      - name: Lint
        run: uv run ruff check .
      
      - name: Type check
        run: uv run mypy backend/
      
      - name: Test
        run: uv run pytest -v --cov=backend

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Build and push Docker image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -f Dockerfile.api -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
      
      - name: Terraform Init
        working-directory: infra
        run: terraform init
      
      - name: Terraform Apply
        working-directory: infra
        env:
          TF_VAR_image_tag: ${{ github.sha }}
        run: terraform apply -auto-approve
```

---

## Build Order (8 Hours)

### Hour 0-1: Project Scaffold
1. Create folder structure
2. Initialize `pyproject.toml` with uv
3. Set up `docker-compose.yml` for local Postgres
4. Create Alembic migration for schema
5. Run migration locally
6. Set up `.env` with Supabase credentials
7. Create FastAPI `main.py` with health check endpoint
8. Test: `docker compose up`, hit `http://localhost:8000/health`

### Hour 1-2: Parsers & Indexing
1. Implement `python_parser.py` — AST extraction
2. Implement `markdown_parser.py` — doc parsing
3. Implement `indexer_service.py` — orchestrates both
4. Write unit tests for parsers
5. Test: index a real Python file + markdown doc

### Hour 2-3: LLM Integration & Drift Detection
1. Implement `openrouter.py` LLM adapter
2. Implement `drift_service.py` with Pydantic structured output
3. Implement `style_service.py` with convention checking
4. Implement `convention_service.py` to extract patterns
5. Write integration tests mocking OpenRouter
6. Test: send a code change + doc, get findings back

### Hour 3-4: GitHub Integration
1. Implement `github/webhook.py` — signature verification
2. Implement `github/api_client.py` — PR fetching, comment posting
3. Implement webhook route in FastAPI
4. Test locally with ngrok forwarding to localhost

### Hour 4-5: Persistence & Repositories
1. Implement ORM models in `db/models.py`
2. Implement repositories (repos, runs, findings)
3. Implement `audit_service.py` (or `audit_orchestrator.py`) — **full orchestration per "Core Service Logic"** (GitHub API file fetch + in-memory index, not clone)
4. Wire up FastAPI routes: `/api/runs`, `/api/runs/{id}`
5. Test end-to-end: webhook → audit → persist → query

### Hour 5-6: Frontend Dashboard
1. Create Next.js app with shadcn/ui
2. Implement Supabase Auth login page
3. Implement runs list page
4. Implement run detail page with findings
5. Connect to FastAPI via API client
6. Test: sign in, view runs, view findings

### Hour 6-7: Terraform & AWS Deployment
1. Write Terraform for **API Gateway HTTP API**, **Lambda** (zip or container image), **IAM**, **CloudWatch**, **Lambda env vars** (and **SQS** if you split webhook vs audit worker)
2. Build deployment artifact (`sam build`, zip layer, or `docker build` + ECR for container Lambda)
3. `terraform apply` to create infrastructure
4. Update frontend env to point to **API Gateway** base URL
5. Deploy frontend to Vercel
6. Test: hit production URL, verify webhook works

### Hour 7-8: End-to-End Testing & Polish
1. Set up GitHub App on test repo
2. Open real PR, verify agent comments
3. Check dashboard shows the run
4. Fix any bugs
5. Add structured logging
6. Write deployment docs
7. Record demo video

---

## Success Checklist

- [ ] Local dev environment works (`docker compose up`)
- [ ] Unit tests pass for parsers
- [ ] Integration tests pass for services
- [ ] Webhook signature verification works
- [ ] Agent can analyze a real PR and post findings
- [ ] Dashboard shows runs and findings correctly
- [ ] Supabase Auth protects all routes
- [ ] Terraform provisions all AWS resources
- [ ] CI/CD pipeline deploys on push to main
- [ ] Production webhook endpoint is live
- [ ] GitHub App is installed and triggering audits
- [ ] Demo recording is complete

---

## Handoff Notes

**For the coding agent**:
1. Start with Hour 0-1 (scaffold)
2. Run each hour's tests before moving to the next
3. Commit after each hour with message "Hour N: [summary]"
4. If blocked, document the blocker and move to next independent task
5. Prioritize working end-to-end over perfect code — this is MVP
6. Keep LLM prompts simple and focused — structured output via Pydantic
7. Use async/await everywhere — FastAPI + SQLAlchemy are async-first
8. Log every LLM call with token count for cost tracking

**Key technical decisions**:
- **AWS Lambda + API Gateway** for the API (scale to zero; split webhook ack and audit via **async invoke** or **SQS** so GitHub gets a fast **202**)
- Supabase for both Auth and Postgres (one vendor)
- OpenRouter for LLM flexibility
- JWT verification in FastAPI middleware
- All state in Postgres (no Redis/cache for MVP)
- Findings stored as rows, not JSONB blob
- Frontend on Vercel (not S3) for speed
- **PR audit uses GitHub REST API** (diff + file contents), not a git clone on the task instance, unless you explicitly expand scope
- **Secrets**: **Lambda environment variables** only for MVP (values injected by Terraform / CI); add Secrets Manager later if compliance requires it

**Demo script**:
Pre-open a PR 5 minutes before demo. Agent runs in background. During demo, show dashboard → run detail → findings → GitHub PR comment. Total demo time: 4 minutes.

---

This document is complete. Hand it to the coding agent and they can build the entire system from scratch.
