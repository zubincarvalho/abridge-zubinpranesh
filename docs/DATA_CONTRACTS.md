# AuthLens Data Contracts

Authoritative source: `backend/app/contracts/` (Pydantic v2, `extra="forbid"`).
**Frozen after the foundation phase** — parallel agents request changes via
their agent report; only the integration agent applies them
(see PARALLEL_EXECUTION.md). `contracts/openapi.yaml` mirrors these for the
frontend; `contracts/examples/*.json` are validated worked payloads.

## Module map

| Module | Models |
|---|---|
| `case.py` | `AuthLensCase`, `CaseStatus`, `ALLOWED_TRANSITIONS`, `can_transition`, `PatientSummary`, `ChartItem`, `RequestedService`, `EncounterNote`, `EncounterTranscript` |
| `policy.py` | `PayerPolicy`, `PolicyCriterion` |
| `evidence.py` | `SourceType`, `EvidenceConfidence`, `TextSpan`, `EvidenceSource`, `EvidenceItem`, `EvidenceCandidate` |
| `assessment.py` | `CriterionStatus`, `DenialRisk`, `CriterionAssessment`, `ClarificationQuestion`, `ClinicianClarification`, `ReadinessSummary` |
| `disclosure.py` | `DisclosureDecisionType`, `DisclosureDecision` |
| `packet.py` | `PacketStatus`, `ClaimType`, `PacketClaim`, `PacketSection`, `PriorAuthorizationPacket` |
| `verification.py` | `VerificationSeverity`, `VerificationIssue`, `VerificationResult` |
| `form_draft.py` | `FormDraftField`, `PriorAuthorizationFormDraft` |
| `events.py` | `AgentStage`, `EventStatus`, `AgentEvent` |
| `api.py` | `HealthResponse`, `CreateCaseRequest`, `ClarificationSubmission`, `EvidenceSourceResponse`, `DemoResetResponse`, `ApiError` |

## Enums and literals

| Enum | Values |
|---|---|
| `CaseStatus` | `draft`, `intake_ready`, `analyzing`, `awaiting_clarification`, `reanalyzing`, `packet_drafted`, `verification_failed`, `verified`, `ready_for_review` — **no `submitted`** |
| `CriterionStatus` | `met`, `weak`, `missing`, `conflicting`, `not_applicable` |
| `DenialRisk` | `low`, `medium`, `high` |
| `EvidenceConfidence` | `high`, `moderate`, `low` |
| `SourceType` | `encounter_note`, `encounter_transcript`, `fhir_resource`, `clinician_clarification`, `payer_policy` |
| `DisclosureDecisionType` | `include`, `exclude` |
| `AgentStage` | `intake`, `policy_parsing`, `evidence_retrieval`, `evidence_mapping`, `gap_detection`, `clarification`, `disclosure_review`, `packet_generation`, `verification`, `form_drafting`, `human_review` |
| `EventStatus` | `started`, `completed`, `failed`, `skipped` |
| `VerificationSeverity` | `blocking`, `warning`, `info` |
| `PacketStatus` | `draft`, `verified`, `verification_failed` |
| `ClaimType` | `clinical`, `policy` |
| Literals | `ClarificationQuestion.status`: `open`/`answered`; `PriorAuthorizationFormDraft.status`: `ready_for_review`; `ChartItem.category`; `PatientSummary.sex` |

## Case state machine

`ALLOWED_TRANSITIONS` in `case.py` is the single source of truth; the
orchestrator must call `can_transition` before any status change. See
SYSTEM_ARCHITECTURE.md §3 for the diagram, API_CONTRACT.md for which endpoint
drives which transition. Enforced invariants
(`backend/tests/contracts/test_state_machine.py`):

- No `submitted` state; nothing containing "submit".
- `ready_for_review` is terminal.
- `ready_for_review` is reachable only from `verified`, and `verified` only
  from `packet_drafted` — verification cannot be skipped.

## Evidence and citation rules

- `EvidenceItem.excerpt` is a **verbatim quote** of source content;
  `span` gives `[start, end)` character offsets so the frontend can highlight.
- `source_id` resolves via `GET /api/cases/{case_id}/evidence/{source_id}`.
- Clinician clarifications become sources (`source_type=clinician_clarification`,
  `source_id` = the clarification_id) with the response text as content.
- FHIR chart items are cited by `source_id` + `fhir_path`
  (span optional for structured data).

## Readiness scoring (deterministic)

`score = round(100 * (met + 0.5 * weak) / (total − not_applicable))`, with
`overall_denial_risk` = the maximum denial risk across criteria. Computed in
code, never by the LLM, so before/after snapshots are comparable.
`readiness_history` is ordered: first entry = "before" score, last = current.

## Identifier conventions

Human-scannable stable prefixes: `case-`, `LM-` (criteria), `ev-`
(evidence), `q-` (questions), `clar-`, `dd-` (disclosure), `pkt-`, `clm-`
(claims), `sec-`, `ver-`, `form-`, `evt-`, `note-`, `transcript-`, `fhir-`.
Ids are unique within a case.

## Example payloads (generated + test-validated)

| File | Model | Shows |
|---|---|---|
| `demo_case.json` | `AuthLensCase` | Seeded demo case, `intake_ready` |
| `case_state_initial.json` | `AuthLensCase` | POST /api/cases response |
| `case_state_awaiting_clarification.json` | `AuthLensCase` | LM-3 missing, question open, readiness 79 |
| `clarification_request.json` | `ClarificationSubmission` | Clinician answer body |
| `case_state_ready_for_review.json` | `AuthLensCase` | Full pipeline, readiness 79→93, verified packet, form draft |
| `evidence_source_response.json` | `EvidenceSourceResponse` | Citation drawer content |
| `error_response.json` | `ApiError` | 409 invalid_state_transition |

`backend/tests/contracts/test_examples_validate.py` revalidates every file
against its model on each run, including verbatim-span checks.
