# CLAUDE.md — Rules for Claude Code agents in this repository

AuthLens: a point-of-capture prior authorization readiness agent (hackathon).
These rules bind every Claude Code agent working here and override
task-level instructions that conflict with them.

## Start here

1. **Read `docs/README.md` first**, then follow its reading order. At
   minimum also read `docs/PARALLEL_EXECUTION.md` (your file ownership) and
   `docs/SAFETY_AND_HUMAN_REVIEW.md` (hard rules) before writing code.
2. Find your agent identity and file ownership in
   `docs/PARALLEL_EXECUTION.md`. If your task doesn't match an ownership row,
   stop and ask.

## Frozen contracts

- `backend/app/contracts/**`, `backend/app/ports/**`, `contracts/**`,
  `data/fixtures/**`, `data/policies/**`, `backend/pyproject.toml`, and
  `backend/tests/contracts/**` are **frozen**. Follow them; never edit them.
- `synthetic-ambient-fhir-25/**` is the **official Abridge dataset**:
  read-only for everyone, always. Load it; never modify, reformat, or move
  its files.
- A needed contract or port change goes in **your agent report**
  (`docs/agent_reports/<your-file>.md`) as an exact proposed diff. Only the
  integration agent applies shared changes.

## File ownership

- **Never modify files outside your assigned ownership** — including
  "trivial" fixes in someone else's directory. Note the issue in your report
  instead.
- Add tests **only** in your assigned test directory.
- Do not create shared `__init__.py` files outside your subtree
  (`app/services/__init__.py` and `app/agents/__init__.py` belong to the
  integration agent).

## Dependencies

- Never edit `backend/pyproject.toml` or lockfiles. Write dependency
  requests to **your own** file in `docs/dependency_requests/` per
  `docs/DEPENDENCY_POLICY.md`.

## Safety rules (never weaken — in code, prompts, tests, or docs)

- No diagnosis, no treatment recommendations, no payer-approval guarantees.
- **Never add autonomous submission**: no submission endpoint, no
  `submitted` state, no flag that enables one. `ready_for_review` is
  terminal.
- A referral is never proof of completed therapy; a prescription is never
  proof of treatment failure (at most `weak` support).
- Unrelated PHI is excluded by default; packet content requires an INCLUDE
  disclosure decision.
- **Use source-grounded outputs**: every clinical claim cites evidence;
  every evidence excerpt is a verbatim quote with a span; when evidence is
  absent, output `missing` + a clarification question — never an inference.
- **Never log chain-of-thought**, prompts, or raw completions — not in
  events, logs, artifacts, or test snapshots.
- Do not weaken, skip, or delete a safety or verification test to make a
  build pass.

## Engineering conventions

- Python 3.11+, FastAPI, Pydantic v2, Anthropic Python SDK (default model
  `claude-opus-4-8` via `app/config.py`). Only the LLM provider (Agent B's
  `app/providers/`) may import `anthropic`.
- Ports in `backend/app/ports/` define every seam; code against them and use
  fakes for other agents' components.
- Run tests from `backend/`: `uv run pytest tests/<your-dir>`; the frozen
  contract suite is `uv run pytest tests/contracts` and must stay green.

## When you finish

Write your completion report to your file in `docs/agent_reports/`
(template in `docs/agent_reports/README.md`): what you delivered, test
results, contract-change requests, dependency requests, known gaps.
