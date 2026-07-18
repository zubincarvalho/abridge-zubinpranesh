# AuthLens Build Log

Chronological record of build phases. Newest first.

## 2026-07-18 — Phase 2: Integration (Integration Lead)

Wired the seven parallel branches into a running backend. Full detail in
[`docs/INTEGRATION_REPORT.md`](docs/INTEGRATION_REPORT.md).

- **Composition root** (`app/api_dependencies.py`): replaced the placeholder
  orchestrator with the real `AuthLensOrchestrator` over Agents A–E; created
  the shared `app/services/__init__.py` and `app/agents/__init__.py`.
- **Provider selection**: explicit deterministic (default) vs live modes; live
  without a key fails at startup — no hidden fallback to the mock. `/api/health`
  reports the mode.
- **Orchestrator** (`app/orchestration/orchestrator.py`): added per-operation
  evidence-mapper / gap-detector factories so a runtime clarification becomes a
  citable evidence source (`resolve_case_sources`).
- **Correctness fix** (`app/services/evidence/duration.py`,
  `app/services/readiness/rubrics.py`): a follow-up interval ("return in 4
  weeks") is no longer mis-read as a symptom duration
  (`is_scheduling_statement`). Restores LM-2 = met, readiness 79 → 93.
- **Tests**: added `tests/integration/` — full-demo E2E, PT-referral safety
  regression, and unsupported-claim verification regression. Updated two
  Agent-G tests whose premise changed (health mode semantics; placeholder
  removed). No safety test weakened.
- **Result**: `uv run pytest` → **351 passed, 1 skipped** (opt-in live LLM).
  Demo verified end-to-end through the FastAPI test client and the live server:
  `intake_ready → awaiting_clarification (79) → … → verified (93) →
  ready_for_review`. No submission path exists.
- **Frozen paths untouched**: `contracts/**`, `app/contracts/**`, `app/ports/**`,
  `data/**`, `pyproject.toml`, `tests/contracts/**`.
- **Dependencies**: all seven agent dependency requests were "none"; no
  `pyproject.toml` / lockfile change needed.
- **Frontend examples**: generated real payloads into `docs/frontend_examples/`.

## Earlier — Phase 1: Parallel build (Agents A–G)

Seven agents implemented their subtrees against the frozen contracts/ports and
local fakes. Per-agent detail: `docs/agent_reports/*.md`.

## Earlier — Phase 0: Foundation (Architecture lead)

Froze contracts, ports, OpenAPI, examples, the synthetic fixture/policy, docs,
and the contract/safety test suite.
