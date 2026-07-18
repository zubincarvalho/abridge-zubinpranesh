# AuthLens Dependency Policy

`backend/pyproject.toml` is **frozen** for parallel agents. Uncoordinated
edits to a shared manifest are the classic parallel-build merge disaster, so
dependency changes flow through request files.

## Already available (no request needed)

Runtime: `fastapi`, `pydantic` (v2), `pydantic-settings`, `anthropic`,
`uvicorn[standard]`. Dev: `pytest`, `pyyaml`, `openapi-spec-validator`,
`httpx`.

## How to request a dependency

1. Append to **your** file in `docs/dependency_requests/` (one file per
   agent — never another agent's file, never a shared file):

   ```markdown
   ## <package>            <!-- e.g. tenacity -->
   - Version constraint: >=8.0
   - Group: runtime | dev
   - Needed by: backend/app/providers/anthropic_provider.py
   - Why: bounded retry with backoff for structured-output validation failures
   - Alternatives considered: hand-rolled retry loop (rejected: reinvents backoff/jitter)
   ```

2. Keep building: guard the import so your module degrades cleanly, or
   temporarily vendor a minimal stub inside your owned tree, and note it in
   your agent report.
3. The **integration agent** reviews all request files, applies approved ones
   to `pyproject.toml` in a single pass, runs `uv sync` + the full test
   suite, and records decisions in `docs/agent_reports/integration.md`.

## Review bar

- Prefer the standard library and already-present packages.
- Permissive licenses only (MIT/BSD/Apache-2.0).
- No packages that transmit data off-host at runtime (beyond the Anthropic
  SDK itself).
- Dev-only helpers go in the `dev` group.

## Never

- Edit `pyproject.toml` or any lockfile as a parallel agent.
- `pip install` into the shared environment and rely on it silently.
- Add a second LLM SDK — all model access goes through the `LLMProvider`
  port (ADR 0001).
