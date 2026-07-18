# AuthLens Implementation Plan

## Phases

| Phase | Who | Output | Status |
|---|---|---|---|
| 0 — Foundation | Architecture lead | Contracts, ports, OpenAPI, examples, fixture, docs, contract tests | **Done** |
| 1 — Parallel build | Agents A–G concurrently | All implementations + per-agent tests, against fakes | **Done** (see `docs/agent_reports/`) |
| 2 — Integration | Integration agent | Wiring, dependency application, E2E tests, conflict resolution | **Done** (see `docs/INTEGRATION_REPORT.md`; full suite 351 passed, 1 skipped) |
| 3 — Demo hardening | Integration agent + frontend | Live-model spot checks, grounding audit, demo script | Frontend console remaining; backend demo verified end-to-end |

Frontend is built separately against `contracts/openapi.yaml` +
`contracts/examples/` and can start immediately (no backend needed).

## Phase 1 task lists

Every agent: read `CLAUDE.md`, `docs/README.md`, PARALLEL_EXECUTION.md, and
your port docstrings first. Build against fakes for other ports. Definition
of done for each agent: implementations complete, tests green in your
directory, agent report + dependency request files written.

### Agent A — Data & FHIR
1. Fixture loader: `data/fixtures/lumbar_mri_prior_auth.json` →
   `AuthLensCase` (status `intake_ready`) + `EvidenceSource` registry
   (note, transcript, chart items, policy) for the evidence endpoint.
2. In-memory `CaseRepository` implementation (create/get/save/list/reset),
   thread-safe enough for a single demo server.
3. Policy text loader for `data/policies/lumbar_mri_policy.md`.
4. `backend/scripts/` seeding helper (used by demo reset).
5. Read-only loader for the official Abridge dataset
   (`synthetic-ambient-fhir-25/synthetic-ambient-fhir-25.jsonl`): record →
   intake inputs (`note` → `EncounterNote`, `transcript` →
   `EncounterTranscript`, `patient_context` + `encounter_fhir` →
   `PatientSummary` chart items with stable `source_id`s). Never modify
   dataset files; the lumbar fixture remains the canonical demo case.

### Agent B — LLM runtime & prompts
1. `LLMProvider` implementation on the Anthropic Python SDK
   (`claude-opus-4-8` default from config; adaptive thinking left on).
2. `complete_structured`: schema-guided output → Pydantic validation →
   bounded retry (2) → typed error. No logging of prompts/completions.
3. Deterministic `FakeLLMProvider` for all other agents' tests (canned,
   fixture-tuned outputs keyed by stage).
4. Prompt library in `app/prompts/` (one module per stage), each prompt
   embedding the safety rules relevant to its stage.

### Agent C — Policy & retrieval
1. `PolicyParser`: policy markdown → `PolicyCriterion` list (LM-1..LM-7),
   category-tagged, faithful requirement text.
2. `EvidenceRetriever`: per-criterion search over note/transcript/chart/
   clarifications; category-routed query templates; verbatim excerpts with
   spans; bounded loop (max 3) for uncertain passes.

### Agent D — Evidence, gaps, readiness, clarification
1. `EvidenceMapper`: candidate → accepted `EvidenceItem`, verbatim-check
   enforced in code (reject non-verbatim before any LLM judgment).
2. `GapDetector.assess`: category rubrics; hard-coded referral/prescription
   rules for `conservative_therapy`.
3. `GapDetector.generate_clarifications`: precise questions; the LM-3
   question must match the spec wording.
4. `GapDetector.compute_readiness`: deterministic formula from
   DATA_CONTRACTS.md; no LLM call.

### Agent E — Disclosure, packet, verification, form
1. `DisclosureFilter`: decision per candidate item; default exclude;
   reasons required.
2. `PacketGenerator`: sections + claims from INCLUDE'd content only; every
   clinical claim carries evidence_ids.
3. `PacketVerifier`: independent prompt; the four checks in
   SYSTEM_ARCHITECTURE.md §5; blocking vs warning severity.
4. `FormDrafter`: verified-packet-only guard (raise otherwise); fields map
   from claims; fixed attestation text.

### Agent F — Orchestration, cases, timeline
1. `WorkflowOrchestrator` implementation: fixed stage sequences per
   operation; `can_transition` enforced before every status change; no
   mutation on failure.
2. Parallel fan-out for retrieval (asyncio.gather over criteria).
3. Event emission (started/completed/failed) with sequence numbers.
4. Case service: create-from-fixture, demo seeding, reset semantics.

### Agent G — API
1. FastAPI app + the 12 routes exactly as in `contracts/openapi.yaml`.
2. Error handling: every failure → `ApiError` envelope with the documented
   codes and status mapping (409 for state violations, 404 for unknowns).
3. `app/api_dependencies.py`: dependency-injection seams for ports (default
   wiring may point at fakes until integration).
4. Contract-conformance tests against the OpenAPI spec.

## Phase 2 — Integration agent
1. Apply approved dependency requests to `pyproject.toml`; `uv sync`.
2. Wire real implementations into `api_dependencies.py`; shared
   `__init__.py` files for `app/services/` and `app/agents/`.
3. Resolve cross-branch conflicts; apply approved contract-change requests
   (re-running contract tests + regenerating examples if shapes change).
4. E2E suite per EVALUATION_PLAN.md layer 3, incl. fault injection.
5. Final docs pass + `docs/agent_reports/integration.md`.

## Milestone checks

- **M1 (end of phase 1):** `uv run pytest` green across all test dirs with
  fakes; every agent report written.
- **M2 (end of phase 2):** E2E demo path green end-to-end offline.
- **M3 (demo-ready):** live-model run passes the grounding audit; frontend
  renders all panels from real responses.
