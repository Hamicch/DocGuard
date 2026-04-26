# `tasks/` — agent and human coordination

| File | Role |
|------|------|
| [`todo.md`](./todo.md) | Checkable implementation roadmap; check items off as work completes; use "Currently In Progress" for active focus |
| [`progress.md`](./progress.md) | Durable log of shipped milestones (append when phases complete) |
| [`lessons.md`](./lessons.md) | Self-improvement: append after every user correction — agents **must** read at session start |
| [`implementation-guide-gap.md`](./implementation-guide-gap.md) | Reconciles `IMPLEMENTATION_GUIDE.md` with `todo.md` / AGENTS layout (what differs, what to update) |

**Instruction channel:** `AGENTS.md` and `CLAUDE.md` require using these files; `.cursor/rules/workflow.mdc` enforces the same in Cursor.
