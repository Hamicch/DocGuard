# Code Review Agent — Product Document

> **AI-powered agent that watches GitHub PRs and enforces both documentation accuracy AND code style conventions, learning a codebase's standards and flagging deviations before merge.**

---

## The Problem

Software teams have two persistent issues that compound over time:

1. **Documentation drifts from code.** Functions get renamed, signatures change, examples become stale. Docs lie. New engineers and API consumers get burned.
2. **Code style drifts across contributors.** Conventions exist informally — in senior engineers' heads — but new code violates them constantly. Reviews waste 40% of their time on style. Consistency erodes as teams grow.

Existing tools handle parts of this poorly:
- **Linters** check syntax, not whether docs match reality or whether code matches conventions
- **Doc generators** work for API references but not conceptual guides
- **Manual reviews** are slow, inconsistent, and senior-engineer-bottlenecked

## The Solution

A single agent that watches every PR and produces structured feedback on **three dimensions**:

1. **Documentation drift** — code changes that invalidate the docs
2. **Style conventions** — new code that doesn't match the codebase's established patterns
3. **Structural conventions** — file size, component breakdown, error handling patterns

The agent learns conventions from the existing codebase by example — no rulebook required.

---

## Target User

- Engineering teams of 5+ where consistency matters
- Open-source projects that want contributor-friendly enforcement
- Companies onboarding new engineers (the agent serves as a continuous tutor)
- Organizations with public APIs where doc accuracy is customer-facing

---

## Full Vision (V2+)

### Code Analysis Capabilities

**Multi-Language Support**
- Python, TypeScript / JavaScript, Go, Rust, Java / Kotlin
- OpenAPI / GraphQL schemas as first-class
- Tools: tree-sitter, language-native parsers

**Multi-Format Documentation**
- Markdown, MDX, reStructuredText, AsciiDoc
- Docusaurus / VitePress / MkDocs frontmatter
- Notion, Confluence sync
- READMEs, CHANGELOGs, ARCHITECTURE docs

**Semantic Linking**
- Explicit references (code blocks, inline mentions)
- Inferred references via embeddings (pgvector)
- API endpoint linking
- Configuration / env var tracking

### Detection Capabilities

**Documentation Drift**
- Signature changes, renames, removals
- Behavior changes that affect documented contracts
- Example drift (code blocks in docs that no longer compile)
- Configuration drift, dependency drift, error drift

**Code Style & Conventions**
- Naming conventions (camelCase vs snake_case, verb-first)
- Control flow patterns (.map vs for-loops, optional chaining)
- Data structure choices (Set vs Array, Map vs Object)
- Error handling patterns
- Import ordering and grouping
- Comment style and density

**Structural Conventions**
- Component / file size limits (e.g., max 200 lines per component)
- Single Responsibility violations
- Circular dependencies
- Module boundary violations
- Test colocation patterns

### Output Capabilities

**PR Integration**
- Inline comments on PRs (GitHub-native suggested-change blocks)
- PR-level summary with severity grouping
- Blocking gates on critical drift
- Auto-PRs with proposed doc fixes

**Dashboard**
- Audit run history with click-into-details
- Per-finding view: current code, current doc, proposed fix, reasoning
- Accept / ignore / customize actions per finding
- Coverage metrics: % of public APIs documented, drift trend over time
- Most-drifted areas surfaced for refactoring

**Notifications**
- Slack / Discord / email digests
- Weekly health reports
- Critical drift alerts

### Integration Capabilities

- **Source**: GitHub, GitLab, Bitbucket
- **Notifications**: Slack, Discord, email, Teams
- **Project tracking**: Linear, Jira (auto-create doc tickets)
- **Wikis**: Confluence, Notion sync
- **IDE**: VS Code extension

### Governance & Enterprise

- SSO / SAML
- Role-based reviewer requirements
- Audit log to SIEM
- Self-hosted option (BYOK encryption)
- SOC 2 posture

### AI / Learning

- Style learning from codebase examples
- Per-project voice preservation for generated docs
- Feedback loop: accepted fixes improve future suggestions
- Doc quality insights (clarity, reading level, accessibility)

---

## MVP Scope (8-Hour Build)

> **Goal**: Demoable, deployed, production-shaped system that detects doc drift AND style violations on real GitHub PRs.

### What We're Building

**Single-Language**: Python only (`ast` stdlib — zero deps)
**Single-Format**: Markdown only (`markdown-it-py`)
**Single-Source**: GitHub only (REST API + webhooks)
**Single-User**: Authenticated via Supabase Auth, but one repo configured per user for V1

### Core MVP Features

**1. GitHub App Integration**
- Webhook receives `pull_request` events (opened, synchronize)
- Signature verification on incoming webhooks
- Posts findings as a single PR comment
- Updates comment on subsequent commits to the same PR

**2. Code Indexing**
- Python AST parser extracts: function signatures, class definitions, public exports
- Tracks: name, signature, file path, line number, docstring, last-modified commit

**3. Doc Indexing**
- Markdown parser extracts: headings, code blocks, inline `code` references
- Identifies which docs reference which code symbols

**4. Convention Inference**
- Single LLM call analyzing 5-10 representative files
- Extracts: naming style, control flow preferences, file size norms, error handling patterns
- Cached per commit to avoid re-running

**5. PR Diff Analysis**
- Fetches the PR diff via GitHub API
- Identifies changed code symbols and new code added

**6. Drift Detection** (LLM judgment)
- For each linked (doc_section, code_entity) pair where code changed:
  - LLM judges: drift detected? severity? what to fix?
- Returns structured Pydantic output

**7. Style Violation Detection** (LLM judgment)
- For each new code section:
  - LLM compares against extracted conventions
  - Flags violations with reasoning and suggested fix

**8. PR Comment Posting**
- Single comment groups findings by type:
  - Documentation drift
  - Style violations
  - Convention violations
- Each finding includes: file, line, current state, proposed fix, reasoning

**9. Authenticated Dashboard**
- Login via Supabase Auth
- List of past audit runs (most recent first)
- Click into run → see all findings with proposed fixes
- View: current code, current doc, proposed fix, reasoning per finding

**10. Run History Persistence**
- Every audit run stored: status, timing, finding counts, cost
- Every finding stored with full context for replay

**11. Production Infrastructure**
- Containerized (Docker)
- Deployed via Terraform
- AWS Lambda (+ API Gateway) for the API service
- Supabase for both auth and Postgres
- GitHub Actions CI/CD

---

## MVP Tech Stack (Locked Decisions)

| Layer | Tool | Why |
|---|---|---|
| Language | Python 3.12 | Backend |
| Package mgmt | uv | Fastest dependency tool |
| API framework | FastAPI | Async, Pydantic-native, OpenAPI docs free |
| Validation | Pydantic v2 | Domain models + LLM structured output |
| LLM SDK | OpenAI SDK | Industry standard, OpenRouter-compatible |
| LLM router | OpenRouter | Multi-model flexibility (Haiku, GPT-4o-mini, etc.) |
| Code parsing | `ast` (stdlib) | Zero deps for Python |
| Doc parsing | markdown-it-py | Robust markdown parser |
| ORM | SQLAlchemy 2.0 async | Standard, async-native |
| Migrations | Alembic | Schema versioning |
| Auth | **Supabase Auth** | Production-ready in 30 lines, free tier |
| Database | **Supabase Postgres** | Same vendor as auth, free tier |
| GitHub | PyGithub + httpx | API + webhook handling |
| Containers | Docker | Local dev and CI; Lambda may use zip artifact or container image |
| Compute | **AWS Lambda** (+ API Gateway) | Scale to zero, pay per use; use SQS or async invoke if audits approach timeout limits |
| Registry | **ECR** (optional) | Only if Lambda is deployed as a **container image**; zip-based Lambda skips ECR |
| IaC | Terraform | All AWS infra |
| CI/CD | GitHub Actions | Build + test + deploy |
| Logs | CloudWatch | Structured JSON logs |
| Frontend | Next.js 15 + Tailwind + shadcn/ui | Modern stack |
| Frontend host | Vercel | Fastest path |
| Lint/format | Ruff | Speed + simplicity |
| Type check | mypy | Type safety |
| Tests | pytest + pytest-asyncio | Standard |

---

## Out of MVP Scope (Explicitly Deferred)

- Multi-language (TS, Go, Rust)
- MDX, RST, AsciiDoc, Confluence, Notion
- Semantic / embedding-based linking
- Auto-PRs with fixes (only PR comments for V1)
- Scheduled audits (only PR-triggered)
- Multi-repo per user
- Slack / Discord / Jira integrations
- VS Code extension
- Complex severity tiers (just high / medium / low)
- Block-merge gating
- Replay mode
- SSO / SAML / SOC 2
- Doc coverage metrics
- Cross-repo doc tracking

---

## Database Schema

```sql
-- Users come from Supabase Auth, referenced by user_id (UUID)

CREATE TABLE repos (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    full_name TEXT NOT NULL,           -- "owner/repo"
    github_installation_id BIGINT,     -- GitHub App installation ID
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, full_name)
);

CREATE TABLE audit_runs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    repo_id UUID REFERENCES repos(id),
    pr_number INT NOT NULL,
    pr_title TEXT,
    pr_author TEXT,
    pr_url TEXT,
    head_sha TEXT,                     -- commit being analyzed
    
    status TEXT NOT NULL,              -- pending | running | completed | failed
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    duration_ms INT,
    error_message TEXT,
    
    total_findings INT DEFAULT 0,
    doc_drift_count INT DEFAULT 0,
    style_violation_count INT DEFAULT 0,
    convention_violation_count INT DEFAULT 0,
    
    llm_tokens_used INT DEFAULT 0,
    cost_estimate_usd NUMERIC(10, 4) DEFAULT 0,
    
    pr_comment_id BIGINT,              -- GitHub comment ID, for updates
    pr_comment_url TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_runs_user_recent ON audit_runs(user_id, created_at DESC);
CREATE INDEX idx_runs_repo_pr ON audit_runs(repo_id, pr_number);

CREATE TABLE findings (
    id UUID PRIMARY KEY,
    run_id UUID REFERENCES audit_runs(id) ON DELETE CASCADE,
    
    finding_type TEXT NOT NULL,        -- doc_drift | style_violation | convention
    severity TEXT NOT NULL,            -- high | medium | low
    
    file_path TEXT NOT NULL,
    line_number INT,
    
    title TEXT NOT NULL,               -- short summary
    description TEXT,                  -- what's wrong
    current_code TEXT,                 -- snippet of current state
    current_doc TEXT,                  -- relevant doc snippet (for drift)
    proposed_fix TEXT,                 -- the suggested change
    reasoning TEXT,                    -- why it's a problem
    
    confidence NUMERIC(3,2),           -- 0.00-1.00
    
    user_action TEXT,                  -- null | accepted | ignored | custom
    user_action_at TIMESTAMPTZ,
    user_custom_fix TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_findings_run ON findings(run_id);
CREATE INDEX idx_findings_type_severity ON findings(finding_type, severity);
```

---

## API Endpoints

```
POST /webhooks/github
  - Receives GitHub PR events
  - Verifies HMAC signature
  - Triggers async audit run
  - Returns 202 Accepted immediately

GET /api/runs
  - Auth required (Supabase JWT)
  - Returns user's audit runs (paginated, recent first)

GET /api/runs/{id}
  - Auth required
  - Returns run details + all findings

POST /api/findings/{id}/action
  - Auth required
  - Body: { action: "accepted" | "ignored" | "custom", custom_fix?: string }

GET /api/repos
  - Auth required
  - Returns user's connected repos

POST /api/repos
  - Auth required
  - Body: { full_name, github_installation_id }
  - Connects a new repo to the user
```

---

## Demo Plan (15-Minute Capstone)

**Pre-demo**: A test PR is already open on the configured repo. Agent has already analyzed it. Comment is posted. Dashboard has data.

**Live demo flow** (4 minutes):

1. **Show the dashboard** — list of past audit runs, recent first
2. **Click into a run** — show findings: doc drift + style violations + convention issues
3. **Show one finding in detail** — current code, current doc, proposed fix, reasoning
4. **Switch to GitHub** — show the actual PR with the agent's comment
5. **Optional**: live-trigger by adding a commit to the PR. Agent re-runs in ~30-45 seconds while you talk through architecture.

**Architecture walkthrough** (6 minutes):
- Show the Mermaid diagram (`architecture/architecture-final.mermaid`)
- Walk through the flow: PR opens → webhook → agent → LLM judgment → comment + storage
- Highlight: ports/adapters for swappable LLMs, structured output via Pydantic, production deployment

**Q&A** (5 minutes).

---

## Success Criteria

The MVP is "done" when:

- [ ] User can sign up via Supabase Auth
- [ ] User can connect a GitHub repo
- [ ] Opening a PR on that repo triggers the agent automatically
- [ ] Agent posts a structured comment with findings within 60 seconds
- [ ] Findings include: doc drift, style violations, and convention violations
- [ ] User can view run history and finding details on the dashboard
- [ ] Everything is deployed to AWS via Terraform
- [ ] CI/CD pipeline lints, tests, and deploys on push to main
