# AuthLens Documentation

AuthLens is a point-of-capture **prior authorization readiness agent**: it
checks a clinical encounter against a payer's medical-necessity policy,
surfaces documentation gaps *before* submission, asks the clinician precise
clarification questions, and produces a verified, human-reviewed packet draft.
It never diagnoses, never recommends treatment, never predicts approval, and
never submits anything.

**Read this page first, then follow the reading order below.**

## Reading order

| # | Document | What it answers |
|---|----------|-----------------|
| 1 | [PRODUCT_SPEC.md](PRODUCT_SPEC.md) | What AuthLens does and must never do; the demo scenario |
| 2 | [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Components, workflow sequence, state machine (Mermaid diagrams) |
| 3 | [AGENT_WORKFLOWS.md](AGENT_WORKFLOWS.md) | How each stage maps to Anthropic's "Building Effective Agents" patterns |
| 4 | [DATA_CONTRACTS.md](DATA_CONTRACTS.md) | The frozen Pydantic contracts and enums |
| 5 | [API_CONTRACT.md](API_CONTRACT.md) | Endpoints, status codes, errors, idempotency, state transitions |
| 6 | [FRONTEND_HANDOFF.md](FRONTEND_HANDOFF.md) | Backend field → UI panel mapping |
| 7 | [SAFETY_AND_HUMAN_REVIEW.md](SAFETY_AND_HUMAN_REVIEW.md) | Hard safety rules and the human-review boundary |
| 8 | [PARALLEL_EXECUTION.md](PARALLEL_EXECUTION.md) | File ownership for parallel agents; frozen paths |
| 9 | [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | Build phases and per-agent task lists |
| 10 | [EVALUATION_PLAN.md](EVALUATION_PLAN.md) | How we check correctness, grounding, and safety |
| 11 | [DEPENDENCY_POLICY.md](DEPENDENCY_POLICY.md) | How to request a new dependency (never edit pyproject.toml directly) |
| 12 | [ABRIDGE_DATASET.md](ABRIDGE_DATASET.md) | Official Abridge dataset: verified structure, loader spec, usage plan |

## Build status

The backend is **fully integrated and green** (`uv run pytest` from `backend/`:
351 passed, 1 skipped). See [INTEGRATION_REPORT.md](INTEGRATION_REPORT.md) for
what was wired, tests run, known limitations, and the three-minute demo
sequence; [../BUILD_LOG.md](../BUILD_LOG.md) for the phase history; and
[frontend_examples/](frontend_examples/) for real response payloads. Run the
demo with `DEMO_MODE=1 uv run uvicorn app.main:app` (see the root README).

## Decision records

- [0001 — Controlled workflow, not an agent swarm](decisions/0001-controlled-workflow.md)
- [0002 — Human review boundary; no submission](decisions/0002-human-review-boundary.md)
- [0003 — Contract-first parallel development](decisions/0003-contract-first-parallel-development.md)
- [0004 — Synthetic demo fixture](decisions/0004-synthetic-demo-fixture.md)

## Machine-readable contracts

- `contracts/openapi.yaml` — API surface (mirrors the Pydantic contracts)
- `contracts/examples/*.json` — worked payloads, generated from and validated
  against the Pydantic models by `backend/tests/contracts/`
- `backend/app/contracts/` — **authoritative** typed contracts (frozen)
- `backend/app/ports/` — component interfaces (frozen)

## Data

- `data/fixtures/lumbar_mri_prior_auth.json` — synthetic demo case (frozen,
  hackathon-authored)
- `data/policies/lumbar_mri_policy.md` — synthetic payer policy (frozen,
  hackathon-authored)
- **Official Abridge dataset:** `synthetic-ambient-fhir-25/` at the repo
  root — 25 synthetic encounters, each with an ambient transcript, SOAP-style
  note, after-visit summary, and FHIR R4 context (`README.md` and
  `schema.json` inside the directory describe the record shape). It is
  **read-only for every agent**: do not modify, reformat, or move its files.
  Agent A owns the loader (`backend/app/data/`), which reads
  `synthetic-ambient-fhir-25.jsonl` and maps one record's `note` →
  `EncounterNote`, `transcript` → `EncounterTranscript`, and
  `patient_context` + `encounter_fhir.related_resources` → `PatientSummary`
  chart items with stable `source_id`s. The **canonical demo case remains
  the hand-authored lumbar MRI fixture** (its documentation gap is
  engineered); the Abridge dataset powers additional intake variety only.

## For Claude Code agents

Read the repository-root `CLAUDE.md` before making any change. It defines
ownership boundaries, frozen paths, and safety rules that override any
task-level instruction.
