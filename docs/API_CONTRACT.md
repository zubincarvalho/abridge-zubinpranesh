# AuthLens API Contract

Machine-readable spec: `contracts/openapi.yaml`. Worked payloads:
`contracts/examples/`. Authoritative schemas: `backend/app/contracts/`.

## Global rules

- **Base path:** `/api`. JSON only.
- **Full-case responses:** every case-mutating endpoint returns the complete
  `AuthLensCase` so the frontend renders all panels from one response and
  never re-derives clinical logic.
- **Errors:** every non-2xx body is `ApiError`
  `{error_code, message, detail?, case_id?}`. Known codes: `case_not_found`,
  `source_not_found`, `question_not_found`, `question_already_answered`,
  `invalid_state_transition`, `packet_not_verified`, `fixture_not_found`,
  `internal_error`.
- **State enforcement:** an operation called in the wrong case status returns
  `409 invalid_state_transition` and does not mutate the case.
- **No submission:** there is no submission endpoint and no `submitted`
  state. `ready_for_review` is terminal.
- **Auth:** none (hackathon demo, synthetic data only).

## Endpoints

| Endpoint | Purpose | Requires status | Transition | Idempotent |
|---|---|---|---|---|
| `GET /api/health` | Liveness | — | — | Yes |
| `GET /api/demo-case` | Seeded demo case, current state | — | — | Yes (read) |
| `POST /api/cases` | Create case from fixture | — | → `intake_ready` | **No** (new case per call) |
| `GET /api/cases/{case_id}` | Full case state | — | — | Yes |
| `POST /api/cases/{case_id}/run` | Analysis pipeline | `intake_ready` | → `analyzing` → `awaiting_clarification` | No (2nd call → 409) |
| `POST /api/cases/{case_id}/clarifications` | Answer a question, re-evaluate | `awaiting_clarification` | → `reanalyzing` → `awaiting_clarification` | No (re-answer → 409 `question_already_answered`) |
| `POST /api/cases/{case_id}/generate-packet` | Disclosure review + packet draft | `awaiting_clarification` or `verification_failed` (regenerate) | → `packet_drafted` | No |
| `POST /api/cases/{case_id}/verify` | Verify every claim | `packet_drafted` | → `verified` \| `verification_failed` | No |
| `POST /api/cases/{case_id}/form-draft` | Mock payer form | `verified` **(requires passing verification)** | → `ready_for_review` (terminal) | No (2nd call → 409) |
| `GET /api/cases/{case_id}/events` | Agent timeline | — | — | Yes |
| `GET /api/cases/{case_id}/evidence/{source_id}` | Resolve a citation source | — | — | Yes |
| `POST /api/demo/reset` | Reset demo state | — | reseeds demo case | Yes (converges to seeded state) |

### Verification requirement

Only `POST /form-draft` requires prior verification: status `verified` and a
stored passing `VerificationResult`; otherwise `409 packet_not_verified`.
`generate-packet` and `verify` require no prior verification —
they are the steps that produce it.

## Requests and responses

| Endpoint | Request body | 2xx | Response body | Example |
|---|---|---|---|---|
| `GET /api/health` | — | 200 | `HealthResponse` | — |
| `GET /api/demo-case` | — | 200 | `AuthLensCase` | `demo_case.json` |
| `POST /api/cases` | `CreateCaseRequest` `{fixture_id}` | **201** | `AuthLensCase` | `case_state_initial.json` |
| `GET /api/cases/{id}` | — | 200 | `AuthLensCase` | any `case_state_*.json` |
| `POST .../run` | — (empty) | 200 | `AuthLensCase` | `case_state_awaiting_clarification.json` |
| `POST .../clarifications` | `ClarificationSubmission` `{question_id, response}` | 200 | `AuthLensCase` | request: `clarification_request.json` |
| `POST .../generate-packet` | — | 200 | `AuthLensCase` | — |
| `POST .../verify` | — | 200 | `AuthLensCase` (check `verification.passed`) | — |
| `POST .../form-draft` | — | 200 | `AuthLensCase` | `case_state_ready_for_review.json` |
| `GET .../events` | — | 200 | `AgentEvent[]` | `events` field of examples |
| `GET .../evidence/{source_id}` | — | 200 | `EvidenceSourceResponse` | `evidence_source_response.json` |
| `POST /api/demo/reset` | — | 200 | `DemoResetResponse` | — |

## Status codes

| Code | When |
|---|---|
| 200 | Successful read or workflow operation |
| 201 | Case created (`POST /api/cases`) |
| 404 | Unknown `case_id`, `source_id`, or `question_id` |
| 409 | Wrong case status; already-answered question; unverified packet |
| 422 | Body fails contract validation (FastAPI/Pydantic) |
| 500 | Unexpected failure (`internal_error`); case state left unchanged |

Note: a `verify` call that *finds blocking issues* is still HTTP 200 — the
outcome is in `verification.passed` and status `verification_failed`. Errors
are for misuse, not for negative results.

## Frontend flow (demo happy path)

```
GET  /api/demo-case                     → render console (intake_ready)
POST /api/cases/{id}/run                → matrix + question + score 79
POST /api/cases/{id}/clarifications     → score 93, LM-3 met
POST /api/cases/{id}/generate-packet    → disclosure panel + packet draft
POST /api/cases/{id}/verify             → verification panel (passed)
POST /api/cases/{id}/form-draft         → form + Ready-for-Review banner
POST /api/demo/reset                    → start over
```
