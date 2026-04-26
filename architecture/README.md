# Architecture — Code Review Agent

Canonical location for **system architecture** artifacts. Product intent and scope live in the repo root [`PRODUCT_DOCUMENT.md`](../PRODUCT_DOCUMENT.md).

## Contents

| File | Purpose |
|------|---------|
| [`architecture-final.mermaid`](./architecture-final.mermaid) | End-to-end system diagram: GitHub → API Gateway → FastAPI on **Lambda** → OpenRouter → Supabase → Next.js dashboard → CI/CD |

## When to update this folder

- **Diagram** (`architecture-final.mermaid`): whenever flows, components, or deployment boundaries change in a meaningful way.
- **This README**: when you add new diagrams, ADRs, or supplementary architecture docs.

## Related

- **Sprint execution**: [`../tasks/todo.md`](../tasks/todo.md) — implementation phases must stay aligned with this architecture; if you change architecture, update `tasks/todo.md` (or add ADRs) before large implementation swings.
- **PR audit step order** (API-based, no clone): [`../IMPLEMENTATION_GUIDE.md`](../IMPLEMENTATION_GUIDE.md) § *Core Service Logic (canonical pipeline)* matches Phase 6 in `tasks/todo.md`.
