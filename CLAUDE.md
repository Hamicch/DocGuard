# Code Review Agent — CLAUDE.md

> Claude-specific project memory. Read at the start of every session.
> This file is the single source of truth for how to work in this repo.

---

## What We're Building

An AI-powered GitHub PR reviewer — **Code Review Agent**.

- Listens for `pull_request` webhooks from GitHub
- Analyzes Python code + Markdown documentation in the changed PR files
- Detects **documentation drift** (code changed, docs didn't) and **style violations** (new code breaks conventions)
- Posts a structured, grouped comment on the PR
- Persists runs + findings to Supabase; surfaces them in an authenticated Next.js dashboard

Full spec: `PRODUCT_DOCUMENT.md` | Architecture project: `architecture/` (`architecture/architecture-final.mermaid`, `architecture/README.md`)

---

## Session Start Checklist

Before touching any code:

1. Read `tasks/todo.md` — find the current phase and next unchecked item
2. Read `tasks/lessons.md` — review mistakes captured from past sessions
3. Skim `architecture/README.md` — confirm diagram path; open the Mermaid file if the task crosses service or deploy boundaries
4. Confirm the task scope with the user before writing a single line

### Hard rules on `tasks/`

- **No shadow plans**: if the work is non-trivial, the checklist lives in `tasks/todo.md`, not only in the chat transcript.
- **Keep files honest**: check off `tasks/todo.md` when done; move active work to "Currently In Progress"; append shipped work to `tasks/progress.md` for milestones.
- **Lessons are mandatory**: any user correction → new entry in `tasks/lessons.md` before closing the topic.
- **Architecture coherency**: if you change how components connect or deploy, update `architecture/` in the same PR/commit series as the code or Terraform.

---

## Repository Structure

```
nest/
├── backend/         # Python 3.12 FastAPI backend → AWS Lambda
│   ├── src/
│   │   ├── domain/       # Pure Pydantic models. No I/O here.
│   │   ├── services/     # Orchestration logic
│   │   ├── adapters/     # GitHub / OpenRouter / Supabase I/O
│   │   ├── repositories/ # SQLAlchemy 2.0 async (repos, runs, findings)
│   │   └── api/          # FastAPI routers + middleware
│   ├── tests/
│   └── pyproject.toml    # uv
├── frontend/        # Next.js 15 dashboard → Vercel
├── infra/           # Terraform (Lambda, API Gateway, env-based config, CloudWatch)
├── architecture/    # System diagrams + architecture index
├── tasks/
│   ├── README.md    # Contract for todo / progress / lessons
│   ├── todo.md      # Sprint tasks — update as you go
│   ├── progress.md  # Completed features log
│   └── lessons.md   # Self-improvement captures
└── .github/
    └── workflows/   # CI: lint → typecheck → test → build → deploy
```

---

## Architecture Flow (Mental Model)

```
PR opened
  → GitHub Webhook → API Gateway → POST /webhooks/github on Lambda (HMAC verified)
  → Fetch PR diff + repo files via GitHub API
  → Python AST Indexer  (symbols from .py)
  → Markdown Indexer    (headings + code blocks from .md)
  → Doc-Code Linker     (match doc sections to symbols)
  → Convention Extractor (LLM: infer style rules from existing files)
  → PR Diff Analyzer    (what changed, what's new)
  → Drift Judge LLM     (doc-code pairs that drifted → structured Findings)
  → Style Judge LLM     (new code vs conventions → structured Findings)
  → Fix Drafter LLM     (proposed fix per Finding)
  → Persist AuditRun + Findings to Supabase
  → Post PR comment (grouped by type + severity)
```

---

## Workflow Rules

### Plan First
- Before any implementation: write or extend the checklist in `tasks/todo.md` (required for non-trivial work)
- Check in with the user before starting — don't implement a plan you haven't confirmed
- Re-plan immediately if something goes sideways; don't keep pushing

### Verify Before Done
- Never mark a task complete without proving it works
- Run `ruff check`, `mypy`, `pytest` before calling anything done
- Ask: "Would a staff engineer approve this?"

### Self-Improvement Loop
- After any user correction: add the lesson to `tasks/lessons.md`
- Format: `## Lesson N — [short title]` + what went wrong + the rule

### Minimal Impact
- Each commit must change only what's needed for the stated task
- If the diff is touching 8 files, stop and ask if you've drifted
- Prefer editing existing files over creating new ones

### Elegance Check
- For non-trivial implementations: ask "is there a more elegant way?"
- Skip for simple, obvious fixes

---

## Commit Convention

```
feat:   new user-visible capability
fix:    bug fix
test:   tests only, no production code
chore:  scaffolding, config, dependency changes
infra:  terraform / docker / CI
docs:   documentation only
```

**Each commit = one logical unit.** No mega-commits.

---

## Code Standards

### Python (`backend/`)
- Ruff for lint + format (line length 100, double quotes)
- mypy strict mode
- All public functions have type annotations
- Async-first: `async def` for anything doing I/O
- Pydantic v2 for all domain models and LLM structured output
- Errors: raise typed exceptions from `domain/exceptions.py`, never bare `Exception`
- Logging: structured JSON via `structlog`, never `print()`

### Next.js (frontend/)
- TypeScript strict mode
- Server Components by default; `"use client"` only when necessary
- shadcn/ui component library
- Supabase client: use `createServerClient` in Server Components, `createBrowserClient` in Client Components

---

## LLM Usage Patterns

All LLM calls go through `adapters/openrouter.py`:
- Drift judgment → Claude Haiku (structured output)
- Style judgment → GPT-4o-mini (structured output)
- Fix drafting → whichever model handled the judgment
- All responses validated against Pydantic schemas before use
- Token counts + cost logged to CloudWatch per run

---

## Database Schema Summary

```
repos        — user_id, full_name, github_installation_id
audit_runs   — repo_id, pr_number, status, finding counts, cost
findings     — run_id, finding_type, severity, file_path, proposed_fix, user_action
```

Full DDL in `PRODUCT_DOCUMENT.md` → "Database Schema" section.

---

## Key MVP Constraints (Do Not Exceed Scope)

| In V1 | Deferred |
|---|---|
| Python only | TS / Go / Rust |
| Markdown only | MDX, Notion, Confluence |
| GitHub only | GitLab, Bitbucket |
| PR-triggered | Scheduled audits |
| PR comments | Auto-fix PRs |
| One repo/user | Multi-repo |
| Email/pass + OAuth | SSO / SAML |

---

## Files to Never Edit Without Thinking Twice

- `backend/src/domain/models.py` — changing shapes here breaks everything downstream
- `backend/alembic/versions/*.py` — migrations are append-only
- `infra/main.tf` — infrastructure changes need explicit user approval
