# AuthLens Integration Report

**Date:** 2026-07-18 · **Role:** Integration Lead · **Scope:** wire, test, and
finalize the backend across the seven parallel agent branches (A–G).

AuthLens is a point-of-capture prior authorization **readiness** agent. It
never diagnoses, never recommends treatment, never predicts approval, and
**never submits** anything — `ready_for_review` is terminal.

---

## 1. Components integrated

Every stage is bound to its frozen port (`backend/app/ports/`); routes never
touch business implementations directly. The composition root is
`backend/app/api_dependencies.py::build_default_workflow_orchestrator`.

| Capability | Port | Implementation (owner) |
|---|---|---|
| Fixture / FHIR loading | `FixtureSource` | `adapters.fixture_provider.FixtureProvider` (A) |
| Case repository | `CaseRepository` | `repositories.in_memory.InMemoryCaseRepository` (A) |
| LLM provider | `LLMProvider` | `providers.{anthropic_provider,mock_provider}` (B) |
| Policy parser | `PolicyParser` | `agents.policy_parser.build_policy_parser` (C) |
| Evidence retriever | `EvidenceRetriever` | `agents.evidence_retriever.build_evidence_retriever` (C) |
| Evidence mapper | `EvidenceMapper` | `agents.evidence_mapper.build_evidence_mapper` (D) |
| Gap detector / readiness | `GapDetector` | `agents.gap_detector.build_gap_detector` (D) |
| Clarification service | — | `services.clarifications` via orchestrator (D/F) |
| Disclosure filter | `DisclosureFilter` | `agents.disclosure_agent.DisclosureAgent` (E) |
| Packet generator | `PacketGenerator` | `agents.packet_generator.PacketGeneratorAgent` (E) |
| Packet verifier | `PacketVerifier` | `agents.verification_agent.VerificationAgent` (E) |
| Form drafter | `FormDrafter` | `services.form_draft.MockPayerFormDrafter` (E) |
| Orchestrator | `WorkflowOrchestrator` | `orchestration.AuthLensOrchestrator` (F) |
| FastAPI routes | — | `api.routes` + `api.case_service` (G) |

### Integration changes made (and why)

The parallel branches were contract-compatible; three integration seams
needed code, all outside the frozen paths (`contracts/**`, `ports/**`,
`contracts/**`, `data/**`, `pyproject.toml`, `tests/contracts/**` were **not**
touched):

1. **Composition root** — replaced Agent G's temporary
   `PlaceholderWorkflowOrchestrator` with the real `AuthLensOrchestrator` over
   Agents A–E. Created the shared `app/services/__init__.py` and
   `app/agents/__init__.py` (integration agent's responsibility per
   PARALLEL_EXECUTION.md).

2. **Per-operation evidence sources** — Agent D's evidence mapper and gap
   detector are keyed to the case's `EvidenceSource`s, and a clinician
   clarification becomes a citable source **at runtime**. Agent F's
   orchestrator originally took pre-built stage instances. I added optional
   `evidence_mapper_factory` / `gap_detector_factory` parameters to the
   orchestrator; when supplied, it resolves the case's sources fresh each
   operation (`resolve_case_sources`) and builds those two stages per run.
   Fixed-instance construction (used by Agent F's unit tests) is unchanged.

3. **Duration-rubric correctness fix** — the integrated retriever surfaced the
   note's follow-up instruction *"Return in 4 weeks or sooner…"*, and the
   duration rubric mis-read that scheduling interval as a symptom duration,
   producing a false `conflicting` on LM-2. Added
   `duration.is_scheduling_statement` and excluded scheduling sentences from
   the duration decision — a follow-up interval is categorically not a symptom
   duration. This restores the engineered demo (LM-2 = met; readiness 79→93).

### Provider selection (reliability)

- **deterministic** (default; `DEMO_MODE=1` or no key): analysis runs fully in
  code — reproducible, no network, no key. Every safety gate is deterministic.
- **live** (`AUTHLENS_LLM_MODE=live` or `ANTHROPIC_API_KEY` present, without
  `DEMO_MODE`): the LLM-capable stages (retrieval refiner, evidence mapper) use
  the real Anthropic provider; the deterministic gates re-check their output.
- **No hidden fallback:** live mode without a key raises
  `ProviderConfigurationError` at **startup** — it never downgrades to mock
  silently. Timeouts (per-stage wall-clock budget, default 120 s), bounded
  retrieval retries (≤3), and structured-output validation retries all live in
  the stage/provider layers. `GET /api/health` reports the mode; it never
  exposes key material.

---

## 2. Tests run

All from `backend/`:

| Suite | Command | Result |
|---|---|---|
| Full suite | `uv run pytest` | **351 passed, 1 skipped** |
| Frozen contracts & safety | `uv run pytest tests/contracts` | 57 passed |
| Data & FHIR (A) | `uv run pytest tests/data` | 62 passed |
| Providers (B) | `uv run pytest tests/providers` | 30 passed, 1 skipped* |
| Policy & retrieval (C) | `uv run pytest tests/policy_retrieval` | 25 passed |
| Evidence & readiness (D) | `uv run pytest tests/evidence_readiness` | 36 passed |
| Output pipeline (E) | `uv run pytest tests/output_pipeline` | 45 passed |
| Orchestration (F) | `uv run pytest tests/orchestration` | 31 passed |
| API (G) | `uv run pytest tests/api` | 62 passed |
| **Integration (new)** | `uv run pytest tests/integration` | **3 passed** |

\* The single skip is Agent B's live-API test (opt-in: needs `ANTHROPIC_API_KEY`
and `AUTHLENS_RUN_LIVE_LLM_TESTS=1`).

**Static checks:** `python -m py_compile` over all app modules — clean;
`import app.main` — clean. No type checker or linter is configured in this repo
(no `[tool.ruff]`/`[tool.mypy]`), so none was run. **OpenAPI:**
`tests/api/test_openapi_compat.py` asserts the FastAPI-generated schema's
paths/methods and `CaseStatus` enum equal `contracts/openapi.yaml` (and that no
`submit` path exists); `contracts/openapi.yaml` parses as OpenAPI 3.0.3.

### New integration tests (`tests/integration/test_end_to_end_demo.py`)

1. `test_full_demo_flow_through_api` — the complete demo through the FastAPI
   test client (acceptance criteria 1–20 below).
2. `test_pt_referral_alone_cannot_satisfy_conservative_therapy` — safety
   regression: a PT referral (+ NSAID prescription) in the record is capped at
   LOW with a limitation note and the conservative-therapy criterion is never
   `met` on that basis.
3. `test_unsupported_packet_claim_cannot_reach_form_draft` — verification
   regression: an unsupported/overstated claim injected into a real packet
   fails the independent verifier (BLOCKING) and the form drafter refuses it.

No test or safety check was weakened. Two Agent-G tests were updated because
their premise changed: the health provider-mode tests now assert the corrected
selection semantics, and the placeholder-orchestrator test was replaced with
one asserting the real orchestrator is wired (the placeholder was removed).

---

## 3. Final API endpoints

Base path `/api`. Full schema: `contracts/openapi.yaml`. There is **no
submission endpoint** and none may be added.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service + `provider_mode` (`live`/`deterministic`) |
| GET | `/demo-case` | Seed/return the lumbar-MRI demo case |
| POST | `/cases` | Create a case from a fixture id → 201 |
| GET | `/cases/{id}` | Full `AuthLensCase` state |
| POST | `/cases/{id}/run` | `intake_ready → awaiting_clarification` |
| POST | `/cases/{id}/clarifications` | Record answer; re-assess |
| POST | `/cases/{id}/generate-packet` | Disclosure review → packet draft |
| POST | `/cases/{id}/verify` | `packet_drafted → verified \| verification_failed` |
| POST | `/cases/{id}/form-draft` | `verified → ready_for_review` (terminal) |
| GET | `/cases/{id}/events` | Agent timeline, ordered by sequence |
| GET | `/cases/{id}/evidence/{source_id}` | Citation drawer (verbatim source) |
| POST | `/demo/reset` | Drop in-memory cases, reseed demo |

---

## 4. End-to-end acceptance flow — verified

All 20 steps pass in `test_full_demo_flow_through_api` and via the live server:

1. `GET /demo-case` → lumbar MRI case (`MHP-IMG-2201`, CPT 72148). ✔
2. `POST /cases` creates the case. ✔
3. `POST /run` starts analysis. ✔
4. Policy parsed into **7 cited criteria** (each with verbatim requirement). ✔
5. Note + FHIR retrieval runs (parallel per criterion). ✔
6. PT referral and NSAID evidence found. ✔
7. Conservative therapy stays **missing** (referral ≠ completion; prescription ≠ failure — capped LOW). ✔
8. Case enters `awaiting_clarification`. ✔
9. Response includes **one** focused clarification question (LM-3). ✔
10. `POST /clarifications` records the six-weeks-PT/NSAID answer. ✔
11. Clarification carries author, timestamp, and provenance (citable source). ✔
12. LM-3 updates `missing → met`. ✔
13. Documentation readiness increases **79 → 93**. ✔
14. Before/after readiness snapshots both retained. ✔
15. Disclosure excludes unrelated info (e.g. seasonal allergic rhinitis). ✔
16. Packet generated; every clinical claim cites evidence. ✔
17. Verification passes (0 issues). ✔
18. Mock form draft produced. ✔
19. Case reaches `ready_for_review`. ✔
20. No endpoint or state submits; `ready_for_review` is terminal (further
    workflow POSTs → 409). ✔

---

## 5. Known limitations

- **Persistence is in-memory** (process-local). Restarting the server clears
  cases; the demo reseeds. The `CaseRepository` port allows swapping later.
- **One supported policy family.** The policy router ships the lumbar-MRI route
  only (`MHP-IMG-2201`); unsupported policies raise `UnsupportedPolicyError`
  rather than being guessed. Abridge dataset cases (`abridge:<id>`) reuse the
  demo lumbar policy as their assessment frame (the dataset ships no orders or
  policies).
- **Deterministic analysis is the default and the tested path.** Live LLM mode
  is wired and gate-protected but is only smoke-testable with a real key; the
  reproducible demo uses deterministic mode.
- **Single-round clarification.** Re-analysis updates the affected criteria;
  new questions are not generated on re-runs (the demo needs exactly one). The
  engineered gap is conservative therapy (LM-3).
- **Timed-out stages** abandon their worker thread (Python cannot kill it);
  state is safely rolled back, but a hung live LLM call could linger until
  process exit. Demo-acceptable.
- **LM-6 (rationale) remains `weak`** on the demo by design — it does not block
  readiness from reaching 93 and needs no clarification.

---

## 6. Synthetic-data disclosures

- **All** patient, clinician, and payer data is synthetic and
  hackathon-authored (`data/fixtures/`, `data/policies/`; ADR 0004). Cases
  carry `synthetic: true`.
- The **official Abridge dataset** (`synthetic-ambient-fhir-25/`) is synthetic
  and is treated as **read-only**: loaded, never modified, reformatted, or
  moved.
- The payer "Meridian Health Plans" and its policy are fictional.
- The mock form draft is labelled a MOCK and is **never** transmitted to any
  payer. Its attestation states it is a draft for clinician review only and
  that readiness is not a guarantee of approval.
- Logs and timeline events carry counts, artifact ids, and public error
  descriptions only — never prompts, completions, chain-of-thought, or keys
  (SAFETY_AND_HUMAN_REVIEW rule 9).

---

## 7. Frontend handoff notes

- The frontend renders everything from the single `AuthLensCase` response
  (`GET /cases/{id}`) plus the timeline (`/events`) and citation drawer
  (`/evidence/{source_id}`). Field → panel mapping: `docs/FRONTEND_HANDOFF.md`.
- **Realistic example payloads** generated from the live pipeline are in
  [`frontend_examples/`](frontend_examples/):
  `01_case_intake` · `02_case_awaiting_clarification` · `03_events_after_run` ·
  `04_case_after_clarification` · `05_case_ready_for_review` ·
  `06_events_full_timeline` · `07_evidence_source_clarification` · `08_health`.
- Readiness: render `readiness_history[0]` as the "before" score and
  `readiness_history[-1]` as "after"; both persist through to
  `ready_for_review`.
- The "Ready for Clinician Review" banner is driven by
  `status == "ready_for_review"`; there is no "submit" affordance to render.
- Remaining work is **frontend-only**: build the React console panels against
  these payloads and `contracts/openapi.yaml`. No backend work is outstanding
  for the demo.

---

## 8. Three-minute demo sequence

Run the server in deterministic mode: `DEMO_MODE=1 uv run uvicorn app.main:app`.

1. **(0:00) Open the demo case.** `GET /api/demo-case` — a lumbar-spine MRI
   request for chronic low back pain with left-leg radiculopathy. Show the
   patient chart, encounter note, and the 7 payer criteria.
2. **(0:30) Run analysis.** `POST /cases/{id}/run`. Walk the agent timeline:
   policy parsed → parallel retrieval → mapping → gap detection → readiness.
   Readiness lands at **79/100**; six criteria met/weak, **conservative
   therapy is missing** because the chart only shows a PT *referral* and an
   NSAID *prescription* — neither proves completed-and-failed therapy.
3. **(1:15) One precise question.** Show the single clarification question for
   LM-3. This is human checkpoint #1.
4. **(1:45) Clinician answers.** `POST /clarifications` with *"Patient
   completed six weeks of physical therapy and daily NSAID therapy without
   meaningful improvement."* Show it recorded verbatim with provenance;
   LM-3 flips **missing → met**; readiness rises **79 → 93**; the before/after
   scores sit side by side.
5. **(2:15) Build the packet.** `POST /generate-packet` — the unrelated
   allergic-rhinitis condition is excluded (minimum-necessary); every clinical
   claim cites verbatim evidence. `POST /verify` → **verified, 0 issues** (the
   independent verifier re-checks every claim).
6. **(2:45) Ready for review.** `POST /form-draft` → mock payer form,
   `ready_for_review`. Emphasize the terminal state: **AuthLens stops here — a
   human clinician acts outside the system; nothing is submitted, and no
   submission path exists.**
