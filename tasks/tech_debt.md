# Tech Debt

> Written at the end of each phase. Each entry explains what the shortcut was,
> why we moved on, and what "paying it back" looks like.

---

## Phase 2 — Database

### `RunRepository.create` — placeholder `user_id`

`AuditRunORM.user_id` is currently set from `run.repo_id` as a stopgap.
The ORM column is `NOT NULL`, so something must go there.

**Why we moved on:** `user_id` is resolved from the auth layer (Phase 7
Supabase JWT middleware). It wasn't available at Phase 2.

**Paying it back:** When the API layer (Phase 7) wires Supabase JWT auth,
the orchestrator caller will look up the `Repo` row by `installation_id`
and pass the real `user_id` when creating the `AuditRun`.

---

## Phase 3 — GitHub

### Webhook `BackgroundTasks` — not Lambda-safe

The webhook handler uses FastAPI `BackgroundTasks` to fire `_trigger_audit`.
This works locally (Docker) but on Lambda the invocation can freeze before
async work completes.

**Why we moved on:** Lambda deployment is Phase 9. The placeholder is correct
behaviour for local development.

**Paying it back:** Wire an SQS queue or async `lambda:InvokeFunction` call
in the webhook handler before deploying to Lambda (Phase 9).

**Status (2026-04-27):** ✅ Paid down.
- Added `AuditDispatcher` (`backend/src/services/audit_dispatcher.py`) with
  env-driven modes:
  - `background` (local dev)
  - `lambda_async` (Lambda `InvocationType='Event'`)
  - `sqs` (SQS enqueue)
- Webhook router now dispatches through this service and returns `503` if
  dispatch infrastructure is misconfigured, instead of silently relying on
  in-process background execution semantics in production.

---

## Phase 6 — Orchestrator

### `repo_full_name` passed via `pr_title` field

`AuditRun.pr_title` is currently overloaded to carry `"owner/repo"` so the
orchestrator knows which repo to query without an extra DB lookup.

**Why we moved on:** The `Repo` table lookup (via `installation_id →
repo_full_name`) belongs in the API layer (Phase 7), which isn't built yet.

**Paying it back:** Phase 7 wires `RepoRepository.get_by_installation()` in
the webhook handler; pass `repo_full_name` to the orchestrator directly and
stop misusing `pr_title`.

### Cost accumulation not wired — always `0.0`

`LLMTrace` is emitted per call but the orchestrator passes `cost_usd=0.0` to
`finalize_run`. Token counts appear in CloudWatch logs but aren't summed.

**Why we moved on:** OpenRouter doesn't return per-call cost in the standard
SDK response. A proper implementation needs either the OpenRouter `/generation`
endpoint or a per-model pricing table.

**Paying it back:** Add a cost accumulator to `AuditOrchestrator` that sums
`LLMTrace.cost_usd` across all calls; wire the total into `finalize_run`.

### Style finding `file_path` is always `"(PR diff)"`

The style judge operates on raw diff code blocks that don't carry their source
file path. Findings are persisted with `file_path="(PR diff)"`.

**Why we moved on:** The diff analyzer returns `new_code_blocks` as plain
strings without file context — extracting file attribution requires parsing
the `@@` hunk headers and tracking which file each hunk belongs to.

**Paying it back:** Extend `DiffResult.new_code_blocks` to be
`list[tuple[str, str]]` (file_path, code) and update the diff analyzer,
style judge call site, and `_style_to_finding` accordingly.

### `FindingRepository` `UserAction` enum may be narrower than DDL

Product DDL allows `user_action` values `ignored` / `custom`; the domain
`UserAction` enum only has `accepted`, `dismissed`, `pending`.

**Why we moved on:** The user action flow is built in Phase 7 (API layer).
The enum will be reconciled when `POST /api/findings/{id}/action` is implemented.

**Paying it back:** Add `ignored` and `custom` to `UserAction`; update the
`POST /api/findings/{id}/action` handler; re-run migrations if needed.
