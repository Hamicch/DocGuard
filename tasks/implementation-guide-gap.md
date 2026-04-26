# Implementation guide vs current plan — gap analysis

Compares `IMPLEMENTATION_GUIDE.md` with `tasks/todo.md`, `AGENTS.md` / `CLAUDE.md` repo layout, and `PRODUCT_DOCUMENT.md` level behavior. Use this to decide what to align (guide vs repo) and what to add to `tasks/todo.md`.

---

## 1. Same or aligned (no action unless you want pin parity)

- **Product intent**: GitHub PR webhooks, drift + style, PR comment, Supabase auth + Postgres, FastAPI on **AWS Lambda** (+ API Gateway), OpenRouter, Next.js dashboard, Terraform + CI/CD.
- **Core tables**: `repos`, `audit_runs`, `findings` and column shapes match the product doc (guide migration matches closely).
- **API surface**: `/webhooks/github`, `/api/runs`, `/api/runs/{id}`, `/api/findings/{id}/action`, repos list/connect (guide contracts align with product doc).
- **Stack**: Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy async, Alembic, structlog, Next 15, Supabase.

---

## 2. Repository and layout differences

| Topic | `IMPLEMENTATION_GUIDE.md` | Current plan (`tasks/todo.md` + `AGENTS.md`) |
|--------|---------------------------|-----------------------------------------------|
| Root project name | `code-review-agent/` | `nest/` (rename only if you care) |
| Python package root | `backend/` as the app root (`backend.main:app`) | `backend/src/` as source tree (`backend/src/...`) |
| Root `pyproject.toml` / `uv.lock` | At **repo root** (single project) | Under **`backend/`** only |
| Dockerfile | **`Dockerfile.api`** at root, build context `.` | **`backend/Dockerfile`** |
| Domain models | Split files: `repo.py`, `audit_run.py`, `finding.py`, `pr_event.py` | Single module `backend/src/domain/models.py` (+ exceptions, ports) |
| Service decomposition | `audit_service`, `indexer_service`, `convention_service`, `drift_service`, `style_service`, `github_service` | `audit_orchestrator`, `comment_formatter`, indexing package, `judgment/` (drift/style/drafter) |
| Adapters layout | Nested: `adapters/parsers/`, `adapters/llm/`, `adapters/github/`, `adapters/auth/` | Flatter: e.g. `adapters/github.py`, `adapters/openrouter.py`; indexing under `services/` |
| API layout | `api/webhooks/github.py`, `api/routers/*.py`, `api/schemas/` | `api/routers/webhooks.py`, optional separate routers; schemas not called out in todo |
| Alembic location | `backend/db/migrations/` (alembic inside `db/`) | `backend/alembic/` (conventional top-level under backend) |
| ORM / session files | `backend/db/models.py`, `backend/db/session.py` | `backend/src/db/orm.py`, `backend/src/db/engine.py` |
| Extra folders | `scripts/`, `docs/` (SETUP, DEPLOYMENT, API, ARCHITECTURE) | Not in todo; `architecture/` + `tasks/` used instead of `docs/ARCHITECTURE.md` |
| Tests | Includes **`e2e/test_full_webhook_flow.py`** | Todo lists unit + integration only; **no e2e task** |

**Update options**

- Either **revise the guide** to match `backend/src/` and current folder names, or **revise todo/AGENTS** to match the guide’s flat `backend/` layout. Pick one source of truth.
- Add todo items if you want: **`api/schemas/`**, **split domain modules**, **`scripts/`**, or **e2e** explicitly.

---

## 3. Runtime and pipeline (resolved)

The **canonical audit pipeline** (ordered steps, GitHub API file fetch and in-memory index, no clone) is documented in **`IMPLEMENTATION_GUIDE.md`** (§ Core Service Logic) and **`tasks/todo.md`** Phase 6. If you adopt on-disk clones later, update those files and **`PRODUCT_DOCUMENT.md`** together.

---

## 4. Webhook and HTTP contract (mostly aligned)

| Topic | Guide | Current plan |
|--------|-------|----------------|
| Success response body | JSON `{ "status": "triggered", "run_id": "uuid" }` | Same optional body on **202** (see `tasks/todo.md` Phase 3) |
| Status code | Was implied from old snippet | **202 Accepted** after enqueue (`IMPLEMENTATION_GUIDE.md` § API Contracts updated) |

---

## 5. Frontend route and UX differences

| Topic | Guide | Current plan |
|--------|-------|----------------|
| Home | `/` → redirect to `/dashboard` | Not specified at root |
| Runs list | `/dashboard` | **`/runs`** |
| Run detail | `/dashboard/runs/[id]` | **`/runs/[id]`** |
| Repo connect | Not a top-level route in tree (may be implied elsewhere) | **`/settings`** |

**Update options**: Align `IMPLEMENTATION_GUIDE.md` tree with `/runs` **or** align todo with `/dashboard` (purely routing; pick one for AGENTS/todo/guide).

---

## 6. Infrastructure and secrets (aligned on env vars)

| Topic | Guide | Current plan |
|--------|-------|----------------|
| Terraform shape | **Modules** under `infra/modules/...`, **S3 backend** in `main.tf` snippet | **Flat** `infra/*.tf` files (`lambda.tf`, `apigateway.tf`, optional `ecr.tf`, …); guide HCL block is **placeholder** until rewritten for Lambda |
| Secrets | Lambda **environment variables** (Terraform / CI-injected) | Same: **no AWS Secrets Manager** for MVP (`tasks/todo.md` Phase 9, diagram, `IMPLEMENTATION_GUIDE.md`) |
| Local DB | **docker-compose** includes **Postgres 16** service + `DATABASE_URL` to it | Compose describes **API + env**; hosted Supabase implied (no local Postgres in todo) |

**Update options**

- If you keep **modules**, add Phase 9 todo bullets for module layout and S3 state backend (or document “flat tf for MVP”).
- If local Postgres is desired, add a **Phase 0** compose task; otherwise state in the guide that Supabase pooler is the default dev DB.

---

## 7. CI/CD differences

| Topic | Guide | Current plan |
|--------|-------|----------------|
| Workflows | **`ci.yml`** + **`deploy.yml`** (separate) | Single **`ci.yml`** with jobs including deploy |
| Test command | `pytest --cov=backend` from root with `uv` at root | `backend/tests`, ruff/mypy scoped to backend |

**Update options**: Split workflows in todo **or** merge guide into one pipeline doc.

---

## 8. Dependencies and tooling in guide but not in todo

Guide pins or adds (todo does not list each explicitly):

- `pydantic-settings`, `python-jose[cryptography]`, `asyncpg`, `uvicorn`, `python-multipart`
- Dev: `pytest-cov`, `respx`, `faker`

**Update options**: Add a **Phase 0** checklist line “lock deps per guide or PRODUCT stack table” or trim the guide to match a minimal `pyproject.toml` you actually want.

---

## 9. Process and agent workflow (guide silent, repo enforced)

| Topic | Guide | Repo today |
|--------|-------|------------|
| `tasks/todo.md`, `lessons.md`, `progress.md` | Not mentioned | **Mandatory** in AGENTS / Cursor rules |
| `architecture/` diagram | Not in guide tree | **`architecture/architecture-final.mermaid`** |
| Commit style | “Hour N: …” for 8-hour build | **Conventional commits** (`feat:`, `chore:`, …) per AGENTS |

**Update options**: Add a short “Agent workflow” section to `IMPLEMENTATION_GUIDE.md` pointing at `tasks/` and `architecture/`, **or** treat the guide as technical-only and keep process solely in AGENTS/CLAUDE.

---

## 10. Recommended update sequence (practical)

1. ~~**Decide clone vs GitHub API**~~ **Done**: guide § Core Service Logic + `tasks/todo.md` Phase 6 use API-only pipeline; Hour 4–5 note updated.
2. **Unify layout**: either rename paths in the guide to `backend/src/...` or change AGENTS/todo to flat `backend/` (pick one).
3. ~~**Unify secrets story**~~ **Done**: **Lambda env vars only** (no Secrets Manager) in guide, todo, and architecture diagram; Terraform HCL example still ECS-shaped until rewritten for Lambda.
4. **Unify frontend routes** in guide vs todo (`/runs` vs `/dashboard`).
5. ~~**Webhook response**~~ **Done**: `202` + optional JSON in Phase 3, guide § API Contracts, and § Core Service Logic note.
6. **Extend todo** if you want parity: **e2e test**, **`scripts/`**, **`api/schemas/`**, **Terraform modules**, **second workflow file**.
7. **Trim or pin** the guide’s `pyproject.toml` block to match whatever you commit in `backend/pyproject.toml`.

---

## Quick reference: file path mapping (if keeping current plan)

| Guide path | Current plan path |
|------------|-------------------|
| `backend/main.py` | `backend/src/main.py` |
| `backend/domain/*.py` | `backend/src/domain/models.py` (+ exceptions, ports) |
| `backend/services/audit_service.py` | `backend/src/services/audit_orchestrator.py` |
| `backend/adapters/parsers/python_parser.py` | `backend/src/services/indexing/ast_indexer.py` (or adapters if you move parsers) |
| `backend/adapters/llm/openrouter.py` | `backend/src/adapters/openrouter.py` |
| `backend/db/migrations/` | `backend/alembic/versions/` |
| `Dockerfile.api` (root) | `backend/Dockerfile` |
| Root `pyproject.toml` | `backend/pyproject.toml` |

---

_Last reviewed: gap between `IMPLEMENTATION_GUIDE.md` and `tasks/todo.md` + `AGENTS.md`._
