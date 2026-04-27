# Lessons learned — Code Review Agent

> **Mandatory for agents:** read this file at the start of every session (after `tasks/todo.md`).  
> After **any** user correction or missed expectation, append a new lesson here.

## How to add a lesson

Use this shape (increment `N`):

```markdown
## Lesson N — [short title]

- **What went wrong**: …
- **Rule**: …
```

---

## Lesson 1 — Always commit after each phase

- **What went wrong**: Phase 7 was fully implemented, tested, and verified but not committed. The user had to ask explicitly.
- **Rule**: After every phase ships (ruff clean, mypy clean, tests passing), stage and commit immediately — do not wait for the user to ask.

## Lesson 2 — Never write tech_debt.md before implementing

- **What went wrong**: Tech debt file was started before code existed for that phase.
- **Rule**: Write `tasks/tech_debt.md` entries only after implementing a phase, if actual shortcuts were taken.

## Lesson 3 — Keep context handoff and progress.md in sync at phase boundaries

- **What went wrong**: `tasks/progress.md` was empty despite phases 0–7 shipping; `CONTEXT_HANDOFF.md` was updated but `progress.md` was not.
- **Rule**: When a phase ships, update both `tasks/progress.md` (milestone entry) and `doc/CONTEXT_HANDOFF.md` (phase detail + one-line summary) in the same commit series.
