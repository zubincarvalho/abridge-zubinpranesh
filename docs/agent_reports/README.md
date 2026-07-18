# Agent completion reports

Every agent writes its report to **its own file** listed in
PARALLEL_EXECUTION.md before finishing. Do not edit another agent's report.

## Template

```markdown
# <Agent name> — completion report

**Date:** <date> · **Scope:** <one line>

## Delivered
- <files/modules created, what each does>

## Tests
- Command: `cd backend && uv run pytest tests/<your-dir>`
- Result: <N passed / failures explained>

## Contract-change requests (if any)
- <file + model/port>: <exact proposed change> — <why>. NOT applied; for the
  integration agent.

## Dependency requests
- See docs/dependency_requests/<your-file>.md (or "none").

## Known gaps / follow-ups for integration
- <anything the integration agent must know>
```
