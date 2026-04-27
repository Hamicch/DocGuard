# Handoff context — DocGuard / Code Review Agent

**Purpose:** Give another LLM (or human) enough context to continue implementation without re-reading the full chat history.

**Last updated:** 2026-04-27 (approximate session end)

---

## Product in one sentence

**DocGuard** is an AI-powered GitHub PR reviewer: webhooks on PR events → analyze Python + Markdown for doc drift and style issues → post a structured PR comment → persist runs/findings in Supabase for a Next.js dashboard.

**Canonical specs:** `doc/PRODUCT_DOCUMENT.md`, `doc/IMPLEMENTATION_GUIDE.md`, `architecture/architecture-final.mermaid`, `architecture/README.md`.

---

## Repo layout (high level)

| Path | Role |
|------|------|
| `backend/` | Python 3.12, FastAPI, SQLAlchemy async, Alembic, uv |
| `backend/src/domain/` | Pydantic models, exceptions, port interfaces (no I/O) |
| `backend/src/db/` | Async engine + ORM (`orm.py`) |
| `backend/src/repositories/` | Concrete repos implementing ports |
| `backend/src/adapters/` | GitHub (and later OpenRouter) |
| `backend/src/api/` | FastAPI routers |
| `backend/alembic/` | Migrations |
| `frontend/` | Next.js 15 (scaffold only, `.gitkeep`) |
| `infra/` | Terraform (skeleton) |
| `doc/` | Product doc, implementation guide, this file |
| `tasks/` | `todo.md` (roadmap), `progress.md`, `lessons.md`, `README.md` |
| `AGENTS.md`, `CLAUDE.md` | Agent instructions |
| `.cursor/rules/` | Workflow + Python conventions |

---

## Locked technical decisions (do not silently undo)

1. **Compute:** AWS Lambda + API Gateway (not Fargate).
2. **Secrets (MVP):** Environment variables on Lambda (not Secrets Manager).
3. **Indexing:** GitHub API fetch in memory (no full repo clone for MVP).
4. **Backend folder:** `backend/` with sources under `backend/src/`.
5. **Diagrams:** `architecture/` (not root `architecture-final.mermaid`).

---

## Phases completed (implementation status)

Phases **0–5** are implemented in code. **`tasks/todo.md`** marks them with checkboxes; treat that file as the live checklist.

### Phase 0 — Scaffold
- Monorepo dirs, `backend/pyproject.toml`, `uv.lock`, Ruff/Mypy/pytest config
- `backend/Dockerfile` (multi-stage): `COPY pyproject.toml uv.lock` + `uv sync --frozen --no-dev`
- Root `docker-compose.yml` → `api` service on port 8000
- `backend/.env.example` (secrets placeholders)
- `backend/src/main.py`: FastAPI + `GET /health` + **Mangum** `handler` for Lambda
- `backend/src/config.py`: `pydantic-settings` `Settings`

### Phase 1 — Domain
- `backend/src/domain/models.py` — `Repo`, `AuditRun`, `Finding`, enums, pipeline types (`CodeSymbol`, `DocSection`, `LinkedPair`, `LLMFinding`), `UserAction`
- `backend/src/domain/exceptions.py` — typed errors under `DocGuardError`
- `backend/src/domain/ports.py` — `IGitHubAdapter`, `ILLMAdapter`, `IRepoRepository`, `IRunRepository`, `IFindingRepository`

### Phase 2 — Database
- `backend/src/db/engine.py` — async engine; normalises `postgres://` → `postgresql+asyncpg://`; `AsyncSessionFactory`, `get_session()` dependency
- `backend/src/db/orm.py` — `RepoORM`, `AuditRunORM`, `FindingORM` aligned with `doc/PRODUCT_DOCUMENT.md` DDL
- `backend/alembic.ini` + `backend/alembic/env.py` — async migrations reading `DATABASE_URL` from settings
- `backend/alembic/versions/001_initial_schema.py` — initial tables + indexes
- Repositories: `repo_repository.py`, `run_repository.py`, `finding_repository.py`

### Phase 3 — GitHub
- `backend/src/api/routers/webhooks.py` — `POST /webhooks/github`
  - HMAC-SHA256 (`X-Hub-Signature-256`) vs `GITHUB_WEBHOOK_SECRET`
  - Handles `pull_request` with actions `opened`, `synchronize`, `reopened`
  - Returns **202** + `{"status":"triggered","run_id":"<uuid>"}`
  - Uses FastAPI `BackgroundTasks` to call `_trigger_audit` placeholder (logs only; **must** become SQS or async Lambda invoke before production — see `tasks/todo.md` Phase 3 note)
- `backend/src/adapters/github.py` — `GitHubAdapter`: App JWT → installation token (cached ~50 min), PR diff, files+contents, file at ref, post/update issue comment
- `backend/src/main.py` — includes webhook router; structlog configured at import

### Phase 4 — Agent Pipeline: Indexing
- `backend/src/domain/models.py` — added `ConventionSet`, `DiffResult` pipeline types
- `backend/src/domain/ports.py` — added `ILLMAdapter.extract_conventions()`
- `backend/src/services/indexing/ast_indexer.py` — `index_python(file_path, source) → list[CodeSymbol]`; stdlib `ast` only; graceful `SyntaxError` handling
- `backend/src/services/indexing/md_indexer.py` — `index_markdown(file_path, source) → list[DocSection]`; uses `markdown-it-py`; one section per heading; headingless content discarded
- `backend/src/services/indexing/linker.py` — `link(sections, symbols) → list[LinkedPair]`; confidence scoring: exact heading (1.0), inline ref (0.9), whole-word body (0.7), substring (0.5); pairs below 0.5 dropped
- `backend/src/services/indexing/convention_extractor.py` — `ConventionExtractor(llm).extract(head_sha, files)`; in-memory cache by commit SHA; truncates to 10 files
- `backend/src/services/indexing/diff_analyzer.py` — `analyze_diff(diff_text) → DiffResult`; regex-based symbol extraction from `+`/`-` lines; per-hunk `new_code_blocks`
- Unit tests: 67 passing across all indexing services

---

## Git history (recent commits, newest first)

```
d99ad67 feat: github app integration — webhook endpoint and API adapter
fe87e6f feat: database layer — engine, ORM models, Alembic migration, repositories
ba14a28 feat: domain models, exceptions, and ports
e7c620a chore: phase 0 scaffold — monorepo structure, backend, planning docs
07b3e60 chore: initial project scaffold and planning docs
```

**Remote:** Branch `main` may be **ahead** of `origin/main` if not all commits were pushed.

---

## Known gaps / tech debt (fix when touching related code)

1. **`IGitHubAdapter` vs `GitHubAdapter` signatures**  
   `ports.py` defines methods **without** `installation_id`. `GitHubAdapter` methods **require** `installation_id: int` for auth. The class is declared as implementing the port but the signatures differ — mypy may flag this; align the port (add `installation_id` everywhere) or wrap the adapter behind a thin facade that closes over installation id from the webhook payload.

2. **`RunRepository.create`**  
   `AuditRunORM.user_id` was temporarily set from `run.repo_id` as a placeholder. The orchestrator should set **real** `user_id` (from repo row or JWT) before persist.

3. **`FindingRepository` / domain `UserAction`**  
   Product DDL allows `user_action` values like `ignored` / `custom`; domain enum may be narrower — reconcile when building the findings API.

4. **`tasks/progress.md`**  
   Often empty; project rules say to append milestones when phases ship.

5. **Webhook async work**  
   `BackgroundTasks` is fine for local Docker; on Lambda it is **not** sufficient for long work — plan SQS or `InvokeFunction` Event as in `tasks/todo.md`.

---

## User / process preferences (from conversation)

- **Do not `git commit` without explicit user approval** (user requested this mid-project).
- Commit messages should **not** cite Cursor or Claude as authors/sources.
- **`doc/`** holds `PRODUCT_DOCUMENT.md` and `IMPLEMENTATION_GUIDE.md` (paths in some older notes may say repo root — prefer `doc/`).
- **ngrok:** Optional for local GitHub → localhost webhooks; requires free account + authtoken. Not required until you want live GitHub delivery; production will use API Gateway URL.

---

## How to run and smoke-test

```bash
# From repo root — API in Docker
docker compose up --build

# Health
curl -s http://localhost:8000/health

# Signed webhook (set SECRET to match backend/.env GITHUB_WEBHOOK_SECRET)
SECRET="..."
BODY='{"action":"opened","number":1,"repository":{"full_name":"owner/repo"},"pull_request":{}}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print "sha256="$2}')
curl -s -w "\nHTTP %{http_code}\n" -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-Hub-Signature-256: $SIG" \
  -d "$BODY"
```

Expected: **HTTP 202** and JSON with `status` + `run_id`; logs show `webhook.pull_request.accepted` then `audit.dispatch.placeholder`.

**DB migrations (when `DATABASE_URL` is set):**

```bash
cd backend && uv run alembic upgrade head
```

---

### Phase 5 — LLM Judgment Layer
- `backend/src/domain/models.py` — added `LLMTrace`, `DriftJudgment`, `StyleJudgment`
- `backend/src/adapters/llm_client.py` — `LLMClient.chat_completion(messages, model, response_format, run_id)`; uses `AsyncOpenAI.beta.chat.completions.parse`; emits `LLMTrace` via structlog after every call; `LLMClient.from_settings()` factory
- `backend/src/services/judgment/drift_judge.py` — `DriftJudge.judge(pair, diff_context, run_id)` + `judge_many()`; Claude Haiku default
- `backend/src/services/judgment/style_judge.py` — `StyleJudge.judge(code_block, conventions, run_id)` + `judge_many()`; GPT-4o-mini default; skips blank blocks
- `backend/src/services/judgment/fix_drafter.py` — `FixDrafter.enrich(judgment, run_id)` + `enrich_many()`; skips if fix already present; no mutation — returns new model instance
- 100 unit tests total, all passing

---

## Next work (pick up here)

**Phase 6 — Audit Orchestrator** (`tasks/todo.md`):

- `backend/src/services/audit_orchestrator.py` — `run_audit(repo_full_name, pr_number, head_sha, installation_id, run_id)`; full 14-step pipeline per `tasks/todo.md`
- `backend/src/services/comment_formatter.py` — renders findings as grouped Markdown PR comment
- Integrate `RunRepository` + `FindingRepository` calls into orchestrator

Then Phase 6 (orchestrator), etc., per `tasks/todo.md`.

---

## Files an agent should read at session start (repo rules)

1. `tasks/todo.md`
2. `tasks/lessons.md`
3. `architecture/README.md` (and Mermaid if boundaries change)

---

## One-line summary for another LLM

> DocGuard MVP: Phases 0–5 done (FastAPI + webhook + GitHub adapter + domain + async DB + Alembic + repos + full indexing pipeline + LLM judgment layer). 100 unit tests passing. Next: Phase 6 audit orchestrator. Align `IGitHubAdapter` with `GitHubAdapter` installation_id. Do not commit without user approval. Specs in `doc/` and `tasks/todo.md`.
