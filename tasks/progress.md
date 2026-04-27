# Progress — Code Review Agent

> Append a summary note here each time a phase ships.

---

## Phase 0 — Project Scaffold
Monorepo structure, FastAPI app with `/health`, Mangum Lambda handler, Dockerfile, docker-compose, `.env.example`, pydantic-settings config.

## Phase 1 — Domain Models
`Repo`, `AuditRun`, `Finding` Pydantic v2 models; `FindingType`, `Severity`, `AuditStatus`, `UserAction` enums; typed exceptions; `IGitHubAdapter`, `ILLMAdapter`, `IRunRepository`, `IFindingRepository` port ABCs.

## Phase 2 — Database
Async SQLAlchemy engine + session factory; `RepoORM`, `AuditRunORM`, `FindingORM` ORM models; Alembic config + `001_initial_schema` migration; `RepoRepository`, `RunRepository`, `FindingRepository` concrete implementations.

## Phase 3 — GitHub App Integration
`POST /webhooks/github` with HMAC-SHA256 verification, 202 response, BackgroundTasks dispatch placeholder; `GitHubAdapter` with App JWT → installation token (cached 50 min), PR diff, files, post/update comment.

## Phase 4 — Agent Pipeline: Indexing
`ast_indexer` (stdlib ast → CodeSymbol list), `md_indexer` (markdown-it-py → DocSection list), `linker` (confidence-scored doc↔code pairs), `convention_extractor` (LLM call cached by head_sha), `diff_analyzer` (regex → DiffResult). 67 unit tests.

## Phase 5 — LLM Judgment Layer
`LLMClient` (OpenAI SDK → OpenRouter, provider-agnostic via env vars, emits LLMTrace via structlog); `DriftJudge` (Claude Haiku, structured DriftJudgment); `StyleJudge` (GPT-4o-mini, structured StyleJudgment); `FixDrafter` (enriches judgments without proposed_fix, immutable model_copy). 100 unit tests.

## Phase 6 — Audit Orchestrator
`AuditOrchestrator.run_audit` — full 14-step pipeline (fetch → index → link → conventions → diff → drift judge → style judge → fix drafter → persist → comment → finalize); `format_comment` grouped Markdown renderer; `RunRepository.finalize_run`. IGitHubAdapter port aligned with installation_id. 123 unit tests.

## Phase 7 — API Layer ✅ (shipped 2026-04-27)
Supabase JWT auth middleware (`python-jose` HS256, `sub` → `uuid.UUID`); `GET /api/runs` (paginated), `GET /api/runs/{id}`; `POST /api/findings/{id}/action` (accepted/ignored/custom); `GET /api/repos`, `POST /api/repos`; CORS + lifespan in `main.py`; `UserAction` extended with `ignored`/`custom`; `list_by_user` added to `RunRepository`. 123 unit tests, mypy clean.

## Phase 8 — Frontend Dashboard ✅ (shipped 2026-04-27)
Manual Next.js 15 scaffold (TypeScript + Tailwind + App Router + shadcn baseline), Supabase SSR/auth helpers (`lib/supabase/{client,server,middleware}.ts`, `middleware.ts`), and dashboard pages: `/login`, `/runs`, `/runs/[id]`, `/settings`. Added typed backend API client (`lib/api.ts`), finding action controls, repo connect form, and `frontend/.env.local.example`. Frontend lint and production build pass.

## Phase 9 — Infrastructure (started 2026-04-27)
Terraform baseline scaffolded for AWS deployment: provider/version pinning, Lambda function + IAM role + env variable wiring, HTTP API Gateway proxy integration, CloudWatch log group and alarms, and outputs (`api_gateway_url`, Lambda identifiers). Added `infra/terraform.tfvars.example`, `infra/README.md`, and a guarded destroy helper script at `infra/scripts/terraform-destroy.sh`.
