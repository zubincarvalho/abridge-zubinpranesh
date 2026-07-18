# Agent F (Orchestration, Case State, Agent Timeline) — completion report

**Date:** 2026-07-18 · **Scope:** deterministic workflow orchestrator, case
service + state-machine enforcement, agent event recorder, orchestration tests.

## Delivered

- `backend/app/events/recorder.py` — `EventRecorder`: appends `AgentEvent`
  records with per-case monotonic sequences, deterministic event ids
  (`<case_id>-ev-<seq>`), injectable clock, and a 400-char detail cap.
  Details are orchestrator-authored summaries only (counts, artifact ids,
  public error descriptions) — never chain-of-thought, prompts, or raw
  completions.
- `backend/app/services/cases/` — case service package:
  - `errors.py` — `CaseOperationError` hierarchy; every error carries an
    `error_code` matching the stable ApiError codes so Agent G can map
    exceptions to responses (`case_not_found`, `invalid_state_transition`,
    `question_not_found`, `question_already_answered`,
    `packet_not_verified`, `internal_error`).
  - `transitions.py` — `require_status` / `apply_transition`, the only
    status-write path in Agent F code; both enforce the frozen
    `ALLOWED_TRANSITIONS` table.
  - `service.py` — `CaseService`: `create_case` (intake validation;
    draft → intake_ready with an INTAKE event), `get_case` (translates
    repo not-found to `CaseNotFoundError`), `save_case`, `list_case_ids`,
    `reset_demo` (clears the repository; reseeding is the caller's concern).
- `backend/app/orchestration/` — the deterministic orchestrator:
  - `orchestrator.py` — `AuthLensOrchestrator` implements the frozen
    `WorkflowOrchestrator` port. Fixed stage order per operation:
    run = intake validation → policy parsing → parallel evidence retrieval
    (ThreadPoolExecutor, ≤3 invocation attempts per criterion; the
    reformulation loop inside the retriever is separately bounded at 3 per
    AGENT_WORKFLOWS §5) → mapping → gap detection → deterministic readiness
    → pause in `awaiting_clarification` (CLARIFICATION started event, or
    SKIPPED when no questions). Clarification = verbatim
    `ClinicianClarification` (id `clar-<question_id>`), question marked
    answered, re-retrieve/re-map/re-assess only the affected criteria,
    before→after summary in the GAP_DETECTION event, new readiness snapshot
    appended (history preserves before/after). Packet = disclosure review →
    generation (regeneration from `verification_failed` lets the generator
    see prior issues, then clears `case.verification`). Verify = independent
    verifier; passed → `verified` + packet status VERIFIED; blocking issues
    → `verification_failed` (expected outcome, not an error). Form = only
    from `verified` with a stored passing result matching the packet id;
    ends in terminal `ready_for_review` plus a HUMAN_REVIEW started event.
    Per-case locks make concurrent mutations safe.
  - `gates.py` — programmatic (non-LLM) gates run inside each stage:
    criteria non-empty/unique/policy-matched; evidence excerpts verbatim
    (and span-consistent) against locally resolvable sources; exactly one
    assessment per criterion; readiness counts sum to assessment count;
    disclosure reasons present; packet is DRAFT, clinical claims cite known
    evidence, no excluded-source citations, sections reference real claims;
    verifier pass/fail flag consistent with its own blocking issues.
  - `stage_runner.py` — wall-clock budget per stage (default 120 s,
    injectable); timeout → `StageTimeoutError`, failed event, rollback.
  - `errors.py` — question/packet/stage errors (codes above).
  - Failure posture: any stage exception or timeout records a `failed`
    event and restores the pre-operation case snapshot (timeline events
    kept), so no partial transitions exist and retries re-run every stage
    and every gate. No `submitted` state, no submission code path.
- `backend/tests/orchestration/` — 31 tests with local fakes for every port
  (`fakes.py`; no imports of other agents' implementations): initial run
  pauses for clarification; clarification resumes and updates readiness
  (67 → 100 with the fake scorer); verification failure blocks the form and
  regeneration recovers; full path reaches `ready_for_review`; invalid
  transitions fail without mutation; repeated run calls are safe; event
  order is correct; no submitted state / no submission API; verifier
  timeout does not bypass verification; bounded retrieval retries; rollback
  on stage failure and on failed clarification; verbatim/self-verified/
  ghost-evidence gate rejections; case service and recorder units.

## Tests

- Command: `cd backend && uv run pytest tests/orchestration`
- Result: **31 passed**. Frozen suite `uv run pytest tests/contracts`:
  **57 passed**. Full tree `uv run pytest`: **323 passed, 1 skipped** (the
  skip and the single warning are pre-existing in other agents' suites).

## Contract-change requests

None. All frozen contracts and ports were sufficient.

## Dependency requests

None — see `docs/dependency_requests/orchestration.md`.

## Known gaps / follow-ups for integration

- **Policy text loading:** the orchestrator resolves
  `PayerPolicy.source_document` relative to the repo root by default; an
  injectable `policy_text_loader` is provided if integration prefers Agent
  A's fixture adapter.
- **Wiring:** `AuthLensOrchestrator` takes the repository positionally and
  all stage ports as keyword arguments; Agent G should construct it in
  `api_dependencies.py` with Agent A's `InMemoryCaseRepository` and Agents
  C/D/E implementations. `CaseService.create_case` / `reset_demo` are the
  intended seams for `POST /api/cases` and `POST /api/demo/reset`.
- **Verbatim gate coverage:** the orchestrator can verify excerpts only
  against sources it can resolve locally (note, transcript, chart items,
  clarifications). FHIR-resource excerpts are skipped at the mapping gate
  and rely on the independent verifier (Agent E) — by design, noted here
  for the evaluation plan.
- **Draft-form status codes:** wrong-status `form-draft` raises
  `packet_not_verified` when the case is `packet_drafted`/
  `verification_failed` (per API_CONTRACT's "otherwise 409
  packet_not_verified") and `invalid_state_transition` for unrelated
  statuses. If Agent G prefers a single code, it is a one-line change in
  `draft_form`.
- **Timed-out stages:** a timed-out stage's worker thread is abandoned
  (Python cannot kill it); state is rolled back so this is safe, but a
  long-hanging LLM call could linger until process exit. Demo-acceptable.
- **New clarification questions after re-analysis** are not generated
  (re-run questions from the gap detector are discarded; existing open
  questions persist). The demo scenario needs only the one engineered
  question; revisit if multi-round questioning is wanted.
