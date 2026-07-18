# Agent G (API) — completion report

**Date:** 2026-07-18 · **Scope:** FastAPI layer against the frozen API contract

## Delivered

- `backend/app/api/errors.py` — `ApiException` + factories for every documented
  error code; `install_error_handlers` translates them (plus
  `app.repositories.errors.CaseNotFoundError`, `app.data.errors.FixtureNotFoundError`
  / `SourceNotFoundError`, `RequestValidationError`, and any unexpected
  exception) into the frozen `ApiError` envelope. 422 bodies report field
  locations and messages only — submitted values are never echoed; 500 bodies
  carry no exception internals.
- `backend/app/api/schemas.py` — `HealthDetailsResponse(HealthResponse)` adds
  `provider_mode: "live" | "deterministic"` (from Agent B's `DEMO_MODE`
  semantics); no key material or key-presence signal is exposed.
- `backend/app/api/case_service.py` — plumbing only: case creation from
  fixtures (Agent A's `FixtureProvider` via a structural `FixtureSource`
  protocol), demo seeding/reset (stable id `case-demo-001`, lazy re-seed),
  read-only state gates raised **before** the orchestrator is called (wrong
  state never mutates), and evidence-source resolution (clarifications
  verbatim from the case; note/transcript/chart/policy via the fixture
  provider, with a case-derived fallback). Tracks `case_id → fixture_id`
  in memory so the citation drawer resolves per case.
- `backend/app/api/routes.py` — all 12 contract endpoints, thin
  (validate → gate → delegate to `WorkflowOrchestrator` port → return
  contract). No submission endpoint; `ready_for_review` is terminal.
- `backend/app/api_dependencies.py` — DI surface: request-scoped getters over
  `app.state`, default builders (in-memory repository, fixture provider), a
  `PlaceholderWorkflowOrchestrator` that raises a contract-shaped 500 until
  Agent F's engine is bound (marked `INTEGRATION POINT` in
  `build_default_workflow_orchestrator`), CORS origins from
  `AUTHLENS_CORS_ORIGINS` (default `http://localhost:3000`, `http://localhost:5173`).
- `backend/app/main.py` — `create_app(...)` factory with keyword injection of
  every port (used by tests and available to the integration agent), CORS
  middleware, error handlers, startup demo seeding (lazy fallback on
  `GET /api/demo-case`). Run with `uv run uvicorn app.main:app`.

Verified against real Agent A defaults: demo case seeds, evidence resolves
(note, chart items, policy, and raw-FHIR sources for `abridge:*` fixtures),
reset converges; workflow endpoints return 500 `internal_error` until the
orchestrator is bound (expected).

## Tests

- Command: `cd backend && uv run pytest tests/api`
- Result: **62 passed**. Full suite (`uv run pytest tests`, including frozen
  contracts): 292 passed, 1 skipped.
- Coverage: every endpoint; request validation (types, extra fields,
  min-length, missing fields); missing case/question/source/fixture; every
  invalid-state 409; clarification submission + re-answer 409; verification
  failure as HTTP 200 + regenerate path; form-draft verification gate
  (packet_drafted / awaiting_clarification / failed verification / missing
  stored result / double call); events ordering; evidence retrieval incl.
  verbatim clarification content; demo seed/reset semantics; CORS (allowed,
  disallowed, preflight, env-configured, defaults); credential non-exposure
  (health + generated OpenAPI with a planted key); generated-OpenAPI ↔
  `contracts/openapi.yaml` path/method set equality, `CaseStatus` enum
  equality, and no `submit` path.
- Tests use local fakes (`tests/api/conftest.py`) implementing the frozen
  ports and raising the canonical error types.

## Contract-change requests

None. Two documented interpretations (no changes made):

1. **422 error_code** — the known-codes list has no code for body-validation
   failures, so 422 responses use `error_code: "validation_error"` (the
   `ApiError.error_code` description is non-exhaustive, "e.g."). If a
   canonical code is preferred, it is one constant in `app/api/errors.py`.
2. **Unknown fixture on `POST /api/cases`** — returns `404 fixture_not_found`
   (`contracts/openapi.yaml` documents only 201/422 there, but
   `fixture_not_found` is a known code and 404 matches the status-code table's
   "unknown id" semantics).

## Dependency requests

None — see `docs/dependency_requests/api.md`.

## Known gaps / follow-ups for integration

- **Bind Agent F's orchestrator** in
  `app/api_dependencies.py::build_default_workflow_orchestrator` (or pass an
  instance to `create_app(workflow_orchestrator=...)`). Everything else is
  wired.
- Routes pre-check state gates read-only (so documented 409/404 codes are
  guaranteed and wrong-state calls never mutate), then delegate; the
  orchestrator still owns transitions. If Agent F's engine raises typed
  state errors, they surface as 500 unless also translated — if desired, add
  handlers for F's error types in `app/api/errors.py::install_error_handlers`.
- The `case_id → fixture_id` map for evidence resolution is in-process
  (`CaseService`); cases seeded into the repository by other components fall
  back to case-derived sources (note/transcript/chart items resolve; the
  policy document body resolves only for fixture-registered cases).
- `GET /api/health` reads provider mode from env at request time via Agent
  B's `LLMProviderConfig.from_env()`; it does not probe the Anthropic API.
- FastAPI's generated OpenAPI is a superset of the contract at the schema
  level (e.g. `provider_mode` on health, FastAPI's default 422 entries);
  paths/methods and `CaseStatus` are asserted equal in
  `tests/api/test_openapi_compat.py`.
