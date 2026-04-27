# Code Review Agent — Implementation Roadmap

> Each item = one small, independently committable unit.
> Commit prefix key: `feat` `fix` `test` `chore` `infra` `docs`
> Mark done with `[x]` as you go. Update `progress.md` when a phase ships; append `lessons.md` after any user correction.
> **Architecture** lives under `architecture/` (diagram + README). If a task changes system boundaries, update that folder in the same change series.
> Agents: read `lessons.md` at session start; keep this file and `progress.md` the source of truth for status — not chat alone.

---

## Phase 0 — Project Scaffold ✅

- [x] `chore: init monorepo dirs` — create `backend/`, `frontend/`, `infra/`, `.github/workflows/` skeletons + root `README.md`
- [x] `chore: uv + pyproject.toml` — FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, httpx, PyGithub, markdown-it-py, structlog; dev: ruff, mypy, pytest, pytest-asyncio — lives in `backend/`
- [x] `chore: ruff + mypy config` — `backend/pyproject.toml` sections; line-length 100, strict mypy
- [x] `chore: Dockerfile` — `backend/Dockerfile` multi-stage: builder (uv install) → runtime (slim Python 3.12)
- [x] `chore: docker-compose.yml` — root-level; `api` service pointing at `backend/` + env file passthrough for local dev
- [x] `chore: .env.example` — `backend/.env.example` with all required secrets (OpenRouter, GitHub App, Supabase, Webhook secret)
- [x] `chore: src/main.py` — minimal FastAPI app with `/health` endpoint + `Mangum` Lambda handler; verified app imports + route registration
- [x] `chore: src/config.py` — `pydantic-settings` `Settings` class loading all env vars with safe defaults

---

## Phase 1 — Domain Models ✅

- [x] `feat: domain models` — `backend/src/domain/models.py`
  - `Repo`, `AuditRun`, `Finding` Pydantic v2 models
  - `FindingType` enum: `doc_drift | style_violation | convention`
  - `Severity` enum: `high | medium | low`
  - `AuditStatus` enum: `pending | running | completed | failed`
- [x] `feat: domain exceptions` — `backend/src/domain/exceptions.py`
  - `WebhookVerificationError`, `GitHubAPIError`, `AuditRunError`, `LLMJudgmentError`
- [x] `feat: domain interfaces` — `backend/src/domain/ports.py`
  - `IGitHubAdapter`, `ILLMAdapter`, `IRunRepository`, `IFindingRepository` abstract base classes

---

## Phase 2 — Database ✅

- [x] `feat: SQLAlchemy setup` — `backend/src/db/engine.py` — async engine + `AsyncSession` factory from `DATABASE_URL`
- [x] `feat: ORM models` — `backend/src/db/orm.py` — `RepoORM`, `AuditRunORM`, `FindingORM` table definitions
- [x] `feat: alembic init + initial migration` — `backend/alembic/` config + `001_initial_schema.py` creating `repos`, `audit_runs`, `findings` + indexes from product doc DDL
- [x] `feat: repository layer` — `backend/src/repositories/`
  - `RunRepository` — `create()`, `update_status()`, `get_by_id()`, `list_by_repo()`
  - `FindingRepository` — `bulk_create()`, `get_by_run()`, `update_action()`
  - `RepoRepository` — `create()`, `get_by_user()`, `get_by_installation()`

---

## Phase 3 — GitHub App Integration ✅

- [x] `feat: github webhook endpoint` — `backend/src/api/routers/webhooks.py`
  - `POST /webhooks/github`
  - HMAC-SHA256 signature verification against `GITHUB_WEBHOOK_SECRET`
  - Returns `202 Accepted` **before** long audit work: on **Lambda**, use **`lambda:InvokeFunction` async** on a dedicated **audit function** or **SQS** queue (in-process `asyncio.create_task` alone is not enough, the invocation can end and freeze work). Optional JSON body `{ "status": "triggered", "run_id": "<uuid>" }` for tracing (align with `IMPLEMENTATION_GUIDE.md` API Contracts)
  - Handles `pull_request` events: `opened` + `synchronize`
- [x] `feat: github API adapter` — `backend/src/adapters/github.py`
  - `get_pr_diff(repo, pr_number)` — raw unified diff text
  - `get_pr_files(repo, pr_number)` — list of changed file paths + contents
  - `get_file_contents(repo, path, ref)` — fetch any file at a given commit
  - `post_pr_comment(repo, pr_number, body)` → comment ID
  - `update_pr_comment(repo, comment_id, body)`
  - Auth: GitHub App JWT → installation token (cached 50 min)

---

## Phase 4 — Agent Pipeline: Indexing

- [x] `feat: python AST indexer` — `backend/src/services/indexing/ast_indexer.py`
  - Input: file path + source text
  - Output: list of `CodeSymbol(name, type, signature, docstring, line_number)`
  - Extracts: functions, classes, public methods — using `ast` stdlib only
- [x] `feat: markdown indexer` — `backend/src/services/indexing/md_indexer.py`
  - Input: file path + markdown text
  - Output: list of `DocSection(heading, body, code_blocks[], inline_refs[])`
  - Uses `markdown-it-py`; extracts inline `` `code` `` references
- [x] `feat: doc-code linker` — `backend/src/services/indexing/linker.py`
  - Input: list of `DocSection[]` + `CodeSymbol[]`
  - Output: list of `LinkedPair(doc_section, code_symbol, confidence)`
  - Strategy: exact name match first; substring match fallback
- [x] `feat: convention extractor` — `backend/src/services/indexing/convention_extractor.py`
  - Input: list of representative Python file contents (5–10 files)
  - Output: `ConventionSet(naming, control_flow, error_handling, imports, comments)` — Pydantic model
  - Single LLM call; result cached by `head_sha` to avoid re-running on same commit
- [x] `feat: PR diff analyzer` — `backend/src/services/indexing/diff_analyzer.py`
  - Input: raw unified diff text
  - Output: `DiffResult(changed_symbols[], new_code_blocks[], deleted_symbols[])`
  - Identifies Python symbol names from diff hunks via regex + AST

---

## Phase 5 — LLM Judgment Layer

- [x] `feat: LLM client` — `backend/src/adapters/llm_client.py`
  - Provider-agnostic: uses the **OpenAI Python SDK** pointed at `https://openrouter.ai/api/v1`
    (OpenRouter exposes an OpenAI-compatible API so any provider is a config change, not a code change)
  - Swapping to a different base URL / API key is the only change needed to target OpenAI, Anthropic, etc. directly
  - `chat_completion(messages, model, response_format)` → parsed Pydantic model
  - Model constants are just strings — easily overridden by env var or caller:
    `HAIKU = "anthropic/claude-haiku-4-5"`, `GPT4O_MINI = "openai/gpt-4o-mini"`, `GEMINI_FLASH = "google/gemini-flash-1.5"`
  - **OpenAI SDK tracing**: attach an `AsyncOpenAI` client with tracing enabled; each call emits an
    `LLMTrace` structured log event (and optionally persists to DB) containing:
    `trace_id`, `model`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `latency_ms`, `run_id`
  - `LLMTrace` Pydantic model added to `domain/models.py`; surfaced in the dashboard (Phase 8)
  - Trace data flows: `llm_client` → structlog JSON → CloudWatch → (future) dashboard query
- [x] `feat: drift judge` — `backend/src/services/judgment/drift_judge.py`
  - Input: `LinkedPair` + changed code context
  - Output: `DriftJudgment(drifted: bool, severity, description, proposed_fix, reasoning, confidence)` — Pydantic
  - Model: Claude Haiku (via `llm_client`); structured output via `response_format={"type": "json_schema"}`
- [x] `feat: style judge` — `backend/src/services/judgment/style_judge.py`
  - Input: `new_code_block` + `ConventionSet`
  - Output: `StyleJudgment(violation: bool, severity, description, proposed_fix, reasoning, confidence)` — Pydantic
  - Model: GPT-4o-mini (via `llm_client`)
- [x] `feat: fix drafter` — `backend/src/services/judgment/fix_drafter.py`
  - Input: list of raw judgments with `violation=True`
  - Enriches each with a concrete `proposed_fix` string if not already provided
  - Model: whichever model produced the judgment (reuse for context)

---

## Phase 6 — Audit Orchestrator

- [ ] `feat: audit orchestrator` — `backend/src/services/audit_orchestrator.py`
  - `run_audit(repo_full_name, pr_number, head_sha, installation_id, run_id)`
  - **Canonical pipeline** (same order as `IMPLEMENTATION_GUIDE.md` § Core Service Logic; GitHub API only, no clone):
    1. Create DB run row (`running`, timestamps, PR metadata).
    2. Fetch PR metadata from GitHub API.
    3. Fetch changed `.py` / `.md` file contents at `head_sha` via API into memory.
    4. Index Python (AST) and Markdown from those blobs.
    5. Link doc sections to code symbols.
    6. Extract conventions (LLM), cache by commit/tree as designed.
    7. Fetch unified PR diff text.
    8. Analyze diff into changed symbols and new code regions.
    9. Drift judge (LLM) on linked pairs affected by changes.
    10. Style judge (LLM) on new/changed code vs conventions.
    11. Fix drafter pass if used.
    12. Bulk persist findings; update token/cost counters on run.
    13. Format Markdown PR comment; post or update GitHub comment.
    14. Finalize run (`completed`, counts, `pr_comment_id`, duration) or `failed` with `error_message`.
  - Catches + logs exceptions → sets status `failed`
  - **Local / Fargate-style**: can use in-process `asyncio.Task`. **Lambda**: implement as **SQS consumer** or **second Lambda** invoked asynchronously from the webhook handler (see Phase 3)
- [ ] `feat: PR comment formatter` — `backend/src/services/comment_formatter.py`
  - Renders findings as a single Markdown comment
  - Grouped: Documentation Drift / Style Violations / Convention Violations
  - Each finding: file path, line, description, proposed fix, severity badge
  - Includes summary header: `N findings (H high, M medium, L low)`
- [ ] `feat: run persistence` — integrate `RunRepository` + `FindingRepository` calls into orchestrator
  - `create_run()` before starting
  - `bulk_create_findings()` after judgment
  - `update_run(status, duration_ms, cost, counts, comment_id)` on completion

---

## Phase 7 — API Layer

- [ ] `feat: supabase JWT middleware` — `backend/src/api/middleware/auth.py`
  - Verifies Supabase-issued JWTs on all `/api/*` routes
  - Extracts `user_id` from `sub` claim; injects as request state
  - Returns `401` on missing/invalid token
- [ ] `feat: GET /api/runs` — paginated list of user's audit runs (20/page, newest first)
- [ ] `feat: GET /api/runs/{id}` — run detail + all findings for that run
- [ ] `feat: POST /api/findings/{id}/action` — accept / ignore / custom action on a finding
  - Body: `{ "action": "accepted" | "ignored" | "custom", "custom_fix": "..." }`
- [ ] `feat: GET /api/repos` — list user's connected repos
- [ ] `feat: POST /api/repos` — connect a new repo
  - Body: `{ "full_name": "owner/repo", "github_installation_id": 12345 }`
- [ ] `feat: FastAPI app wiring` — `backend/src/main.py` — register routers, CORS, lifespan (DB connect/disconnect); export **`handler`** for Lambda (e.g. **Mangum** wrapping the ASGI app, or AWS Lambda Web Adapter pattern)

---

## Phase 8 — Frontend Dashboard

- [ ] `feat: next.js init` — `npx create-next-app@latest frontend` with TypeScript, Tailwind, App Router; add shadcn/ui init
- [ ] `feat: supabase auth setup` — `@supabase/ssr` client helpers; `middleware.ts` session refresh; env vars `NEXT_PUBLIC_SUPABASE_URL` + `ANON_KEY`
- [ ] `feat: login page` — `/login` — email/password + GitHub OAuth via Supabase Auth UI; redirect to `/runs` on success
- [ ] `feat: runs list view` — `/runs`
  - Server Component; fetches `GET /api/runs` with Supabase JWT
  - Table: PR title, repo, status badge, finding counts, date, link to detail
  - Empty state for new users
- [ ] `feat: finding detail view` — `/runs/[id]`
  - Finding cards grouped by type
  - Each card: current code snippet, current doc snippet (drift only), proposed fix, reasoning, severity badge
  - Accept / Ignore / Custom action buttons → `POST /api/findings/{id}/action`
- [ ] `feat: repo connect flow` — `/settings` — input for `owner/repo` + installation ID; calls `POST /api/repos`

---

## Phase 9 — Infrastructure (AWS Lambda)

- [ ] `infra: terraform API Gateway` — `infra/apigateway.tf` — HTTP API, routes to Lambda, `$default` stage, throttling as needed
- [ ] `infra: terraform Lambda` — `infra/lambda.tf` — function (zip or container image), IAM execution role, **function URL optional** (prefer API Gateway for GitHub webhook + JWT routes on same host)
  - Runtime Python 3.12; memory and timeout sized for PR audit (see product doc 60s target; add **SQS + worker** or **async Lambda invoke** if you approach **15 min** limit)
  - **Secrets: Lambda environment variables only** (MVP). Set values from Terraform `variables` / `.tfvars` supplied at apply time or from CI (e.g. GitHub Actions secrets → `terraform apply` `-var`). **Do not use AWS Secrets Manager** for this phase unless you explicitly add it later.
- [ ] `infra: terraform ECR` (optional) — `infra/ecr.tf` — only if Lambda uses a **container image**; lifecycle policy (keep last N)
- [ ] `infra: terraform CloudWatch` — `infra/observability.tf` — log group for Lambda, metric filters / alarms for errors + LLM cost signals
- [ ] `infra: terraform variables + outputs` — `infra/variables.tf` + `infra/outputs.tf` — API Gateway base URL, Lambda name/ARN, optional ECR URL

---

## Phase 10 — CI/CD

- [ ] `infra: GitHub Actions CI` — `.github/workflows/ci.yml`
  - Triggers: push to `main`, PRs targeting `main`
  - Jobs: `lint` (ruff), `typecheck` (mypy), `test` (pytest)
  - All jobs must pass before `build` job starts
- [ ] `infra: GitHub Actions build + package` — `build` job
  - Either **zip artifact** (`uv export` / `pip install -t` / `sam build`) or **`docker build` + push to ECR** when using container-based Lambda; tag with `$GITHUB_SHA`
  - Only runs on `main` branch
- [ ] `infra: GitHub Actions deploy` — `deploy` job (depends on `build`)
  - `terraform init` + `terraform apply -auto-approve` — updates **Lambda version** / alias and **API Gateway** deployment
  - Vercel deploy for frontend via `vercel --prod`

---

## Phase 11 — Tests

- [ ] `test: AST indexer unit tests` — `backend/tests/unit/test_ast_indexer.py`
  - Functions, classes, methods extracted correctly
  - Handles syntax errors gracefully
- [ ] `test: markdown indexer unit tests` — `backend/tests/unit/test_md_indexer.py`
  - Headings, code blocks, inline refs extracted
- [ ] `test: diff analyzer unit tests` — `backend/tests/unit/test_diff_analyzer.py`
  - Added/removed/changed symbols identified from diff hunks
- [ ] `test: drift judge unit tests` — `backend/tests/unit/test_drift_judge.py`
  - Mocked LLM responses; validates Pydantic output parsing
- [ ] `test: webhook integration test` — `backend/tests/integration/test_webhook.py`
  - `POST /webhooks/github` with valid + invalid HMAC signatures
  - Verify `202` vs `401` responses
- [ ] `test: API integration tests` — `backend/tests/integration/test_api.py`
  - Auth-required routes return `401` without token
  - `GET /api/runs` returns correct shape with mocked DB

---

## Phase 12 — Demo Prep & Verification

- [ ] `docs: end-to-end demo setup` — configure a test GitHub repo + install GitHub App + seed one AuditRun + findings in Supabase
- [ ] Verify all success criteria from `PRODUCT_DOCUMENT.md`:
  - [ ] User can sign up via Supabase Auth
  - [ ] User can connect a GitHub repo
  - [ ] Opening a PR triggers the agent within 60 seconds
  - [ ] Agent posts a structured PR comment with findings
  - [ ] Dashboard shows run history and finding details
  - [ ] Everything deployed to AWS via Terraform
  - [ ] CI/CD pipeline passes on push to main

---

## Currently In Progress

> Move items here when actively working on them (one at a time).

_None — ready to start Phase 0._

---

## Review Log

> Add a summary note here each time a phase ships.

_No phases shipped yet._
