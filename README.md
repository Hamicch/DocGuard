# DocGuard

> AI-powered GitHub PR reviewer that detects documentation drift and style violations, posts structured findings directly on the PR, and stores run history in a dashboard.

---

## What it does

DocGuard installs as a GitHub App on your repository. Every time a pull request is opened or synchronized, it:

1. Fetches the changed `.py` and `.md` files at the PR's head commit
2. Indexes Python symbols (via AST) and Markdown documentation sections
3. Links code symbols to their documentation counterparts
4. Infers coding conventions from existing files using an LLM
5. Judges **documentation drift** — code that changed but its docs didn't
6. Judges **style violations** — new code that breaks established conventions
7. Drafts a proposed fix for each finding
8. Posts a grouped Markdown comment on the PR
9. Persists every run and finding to Supabase for review in the dashboard

---

## How to use

### 1. Install the GitHub App

Go to your DocGuard GitHub App settings page and click **Install**. Select the repository you want to monitor.

### 2. Connect your repository in the dashboard

Sign in to the DocGuard dashboard, navigate to **Settings**, and fill in:

- **Repository** — `owner/repo` (e.g. `acme/backend`)
- **GitHub Installation ID** — found in your GitHub App installation URL (`https://github.com/settings/installations/<id>`)

Click **Connect**.

### 3. Open a pull request

Push a branch and open a PR against your default branch. DocGuard will:

- Trigger within seconds of the webhook arriving
- Post a comment on the PR grouped by finding type and severity
- Record the run in the dashboard under **Audit Runs**

### 4. Review findings in the dashboard

Each run shows:
- PR number and title
- Status (`pending` → `running` → `completed` / `failed`)
- Finding counts by type (documentation drift, style violations, convention violations)
- Per-finding detail with file path, line number, description, and proposed fix

---

## Repo layout

```
nest/
├── backend/        # Python 3.12 FastAPI → AWS Lambda
│   ├── src/
│   │   ├── domain/       # Pydantic models and domain exceptions
│   │   ├── services/     # Orchestration, judges, indexers
│   │   ├── adapters/     # GitHub API, LLM client (OpenRouter/OpenAI)
│   │   ├── repositories/ # SQLAlchemy 2.0 async (Supabase/Postgres)
│   │   └── api/          # FastAPI routers and auth middleware
│   └── tests/
├── frontend/       # Next.js 15 dashboard → Vercel
├── infra/          # Terraform — Lambda, API Gateway, CloudWatch
├── architecture/   # System diagram and architecture notes
└── tasks/          # todo.md, progress.md, lessons.md
```

---

## Local development

### Prerequisites

- Python 3.12 + [uv](https://github.com/astral-sh/uv)
- Node.js 20+
- A Supabase project
- An OpenAI or OpenRouter API key
- A GitHub App (see [GitHub docs](https://docs.github.com/en/apps/creating-github-apps))

### Backend

```bash
cd backend
cp ../.env.example ../.env   # fill in secrets (see Environment variables below)
uv sync --extra dev
uv run uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`.

To expose it to GitHub webhooks during development, use a tunnel:

```bash
ngrok http 8000
# Set your GitHub App webhook URL to https://<ngrok-id>.ngrok.io/webhooks/github
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local   # set NEXT_PUBLIC_SUPABASE_URL, etc.
npm install
npm run dev
```

Dashboard available at `http://localhost:3000`.

### Run tests

```bash
cd backend
uv run pytest
uv run ruff check src
uv run mypy src
```

---

## Environment variables

### Backend (`.env`)

| Variable | Description |
|---|---|
| `DATABASE_URL` | Supabase Postgres connection string (`postgresql+asyncpg://...`) |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
| `SUPABASE_JWT_SECRET` | JWT secret for auth middleware |
| `GITHUB_APP_ID` | GitHub App ID |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App RSA private key (PEM, single line with `\n`) |
| `GITHUB_WEBHOOK_SECRET` | Webhook secret set in GitHub App settings |
| `LLM_API_KEY` | API key for your LLM provider |
| `LLM_BASE_URL` | Provider base URL (e.g. `https://api.openai.com/v1`) |
| `AUDIT_DISPATCH_MODE` | `background` (local) or `lambda_async` (production) |
| `AUDIT_WORKER_LAMBDA_NAME` | Lambda function name (required for `lambda_async` mode) |
| `LANGFUSE_PUBLIC_KEY` | _(optional)_ Langfuse public key for LLM tracing |
| `LANGFUSE_SECRET_KEY` | _(optional)_ Langfuse secret key |
| `LANGFUSE_HOST` | _(optional)_ Langfuse host (default: `https://cloud.langfuse.com`) |

---

## Infrastructure (AWS)

Terraform manages the Lambda function, API Gateway, and CloudWatch logs.

```bash
cd infra
cp terraform.tfvars.example terraform.tfvars
# Fill in values — at minimum: lambda_zip_path, supabase vars, github vars, llm vars
terraform init
terraform plan -var-file="terraform.tfvars"
terraform apply -var-file="terraform.tfvars"
```

To tear down:

```bash
cd infra
./scripts/terraform-destroy.sh
```

After any code change, repackage and redeploy:

```bash
cd backend
uv sync --no-dev
mkdir -p dist/lambda
rsync -a src/ dist/lambda/src/
rsync -a .venv/lib/python3.12/site-packages/ dist/lambda/
cd dist/lambda && zip -r ../docguard-lambda.zip . && cd ../..
# Then: terraform apply or aws lambda update-function-code
```

---

## LLM observability (Langfuse)

When `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, every audit run creates a trace in Langfuse with nested generations for each agent:

- `convention_extractor` — infers coding conventions from existing files
- `drift_judge` — checks doc-code pairs for documentation drift
- `style_judge` — checks new code against inferred conventions
- `fix_drafter` — proposes a fix for each finding

Traces are grouped by `run_id` and visible under **Traces** in the Langfuse dashboard.

---

## Documentation

- [Product spec](doc/PRODUCT_DOCUMENT.md)
- [Architecture diagram](architecture/README.md)
- [Infrastructure docs](infra/README.md)
- [Task board](tasks/todo.md)
