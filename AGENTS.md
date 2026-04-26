# Code Review Agent — AGENTS.md

> Instruction channel for all AI coding agents (Codex, Claude, Cursor, etc.).
> Read this file at the start of every session.

---

## Mandatory: `tasks/` + architecture

These rules are **non-optional**. Skipping them is a process failure.

1. **Session start** — Before writing or changing production code, read in order:
   - `tasks/todo.md` — current phase and next unchecked item
   - `tasks/lessons.md` — prior corrections and rules
   - `architecture/README.md` — where diagrams live; open `architecture/architecture-final.mermaid` when the task touches system boundaries
2. **During work** — Keep `tasks/todo.md` truthful: check off completed items; move active work to the "Currently In Progress" section; do not claim completion without verification (tests, logs, or explicit user acceptance).
3. **When a phase or milestone ships** — Append or update `tasks/progress.md` so humans and agents share the same completed-work record.
4. **After any user correction** — Append a lesson to `tasks/lessons.md` using the template in that file.
5. **Architecture changes** — Update `architecture/` (diagram and/or `architecture/README.md`) in the **same** change set as the code or infra that reflects the new reality; if the plan changes, update `tasks/todo.md` before continuing implementation.

---

## Project Overview

An AI-powered GitHub PR reviewer that:
1. Watches for `pull_request` events via GitHub Webhooks
2. Analyzes Python source + Markdown docs for **documentation drift** and **style violations**
3. Posts structured findings as a PR comment
4. Persists runs and findings to a Supabase-backed dashboard

**Product document**: `PRODUCT_DOCUMENT.md`  
**Architecture project**: `architecture/` — diagram: `architecture/architecture-final.mermaid` (see `architecture/README.md`)

---

## Repository Layout

```
nest/
├── backend/                   # Python FastAPI backend (AWS Lambda)
│   ├── src/
│   │   ├── domain/            # Pydantic domain models (no I/O)
│   │   ├── services/          # Business logic / orchestrator
│   │   ├── adapters/          # GitHub, OpenRouter, Supabase clients
│   │   ├── repositories/      # SQLAlchemy async repos
│   │   └── api/               # FastAPI routers
│   ├── tests/
│   ├── pyproject.toml         # uv-managed dependencies
│   ├── Dockerfile
│   └── alembic/               # DB migrations
├── frontend/                  # Next.js 15 dashboard (Vercel)
│   ├── app/
│   ├── components/
│   └── package.json
├── infra/                     # Terraform (API Gateway, Lambda, IAM, env-based config, CloudWatch)
│   └── main.tf
├── architecture/              # System diagrams + architecture index (see README.md)
├── tasks/
│   ├── README.md              # What each tasks/* file is for (agents must follow)
│   ├── todo.md                # Current sprint — check before starting
│   ├── progress.md            # Completed work log
│   └── lessons.md             # Self-improvement loop captures
└── .github/
    └── workflows/ci.yml       # Lint → test → build → deploy
```

---

## Tech Stack (Locked)

| Layer | Tool |
|---|---|
| Language | Python 3.12 |
| Package mgmt | uv |
| API | FastAPI + Pydantic v2 |
| LLM SDK | OpenAI SDK → OpenRouter |
| Code parsing | `ast` stdlib |
| Doc parsing | `markdown-it-py` |
| ORM | SQLAlchemy 2.0 async |
| Migrations | Alembic |
| Auth | Supabase Auth (JWT) |
| Database | Supabase Postgres |
| GitHub | PyGithub + httpx |
| Frontend | Next.js 15 + Tailwind + shadcn/ui |
| Infra | Terraform → AWS Lambda + API Gateway |
| CI/CD | GitHub Actions |
| Lint/format | Ruff |
| Type check | mypy |
| Tests | pytest + pytest-asyncio |

---

## Workflow Orchestration

### 1. Plan First
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan — don't keep pushing
- Write detailed specs upfront to reduce ambiguity
- Use plan mode for verification steps, not just building

### 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

### 3. Self-Improvement Loop
- After ANY correction from the user: update `tasks/lessons.md` with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review `tasks/lessons.md` at session start

### 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes — don't over-engineer
- Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests — then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

---

## Task Management (must use `tasks/` files)

1. **Plan First**: Write or extend the plan in `tasks/todo.md` with checkable items — do not keep a parallel plan only in chat.
2. **Verify Plan**: Check in with the user before starting non-trivial implementation.
3. **Track Progress**: Check items in `tasks/todo.md` as you go; use the "Currently In Progress" section for active work.
4. **Explain Changes**: High-level summary at each step (in chat and, for milestones, in `tasks/todo.md` Review Log).
5. **Document Results**: Add a short entry to the Review Log in `tasks/todo.md` when a phase completes; mirror major milestones in `tasks/progress.md`.
6. **Capture Lessons**: Update `tasks/lessons.md` after any user correction — no exceptions.

---

## Core Principles

- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

---

## Commit Convention

Each commit must be **small and independently deployable**. Follow this prefix scheme:

```
feat:   new capability
fix:    bug fix
test:   tests only
chore:  scaffolding, config, deps
infra:  terraform / docker / ci changes
docs:   documentation only
```

One logical unit per commit. If you need `&&` to describe what changed, split it.

---

## Domain Glossary

| Term | Meaning |
|---|---|
| `AuditRun` | One analysis triggered by a PR event |
| `Finding` | A single detected issue (drift / style / convention) |
| `Drift` | A code change that invalidates existing documentation |
| `Convention` | An inferred style rule extracted from existing codebase files |
| `Judge` | An LLM call that returns structured `Finding` output |
| `Drafter` | An LLM call that proposes a concrete fix for a finding |

---

## Key Constraints

- Python only for MVP (no TS/Go analysis yet)
- Markdown only for docs (no Notion/Confluence yet)
- GitHub only (no GitLab/Bitbucket yet)
- One repo per user for V1
- No auto-PRs with fixes — PR comments only
- No block-merge gating in V1
- No scheduled audits — PR-triggered only
