# AuthLens Frontend Handoff

The frontend is a clinical workflow console rendered **entirely** from
`AuthLensCase` (returned by every case endpoint) plus two auxiliary reads
(`/events`, `/evidence/{source_id}`). No clinical logic lives client-side.

Contract: `contracts/openapi.yaml`. Realistic payloads for building against
without a running backend: `contracts/examples/case_state_*.json`.

## Panel → field mapping

| UI area | Backend source | Notes |
|---|---|---|
| **Patient Chart** | `case.patient` — `display_name`, `birth_date`, `sex`, `chart_items[]` | Each `ChartItem` has `source_id` → clickable into the citation drawer. `category` drives icons (condition/medication/referral/observation/service_request). |
| **Encounter Note** | `case.encounter_note` — `title`, `text`; optional `case.encounter_transcript` | Render `text` as-is. Highlight cited ranges using `EvidenceItem.span` offsets into this exact string. |
| **Payer Policy Criteria** | `case.policy` (header: `payer_name`, `policy_title`, `synthetic`) + `case.criteria[]` | Show `label` + `requirement` per criterion. Empty until `run` completes. Always show a "synthetic policy" badge when `policy.synthetic`. |
| **Agent Timeline** | `case.events[]` (or `GET /events`) | Ordered by `sequence`. `stage` → step name, `status` → icon (started/completed/failed/skipped), `title`/`detail` → text. Never contains chain-of-thought. |
| **Authorization Readiness Matrix** | `case.assessments[]` joined to `case.criteria[]` on `criterion_id` | Row per criterion: `status` chip (met/weak/missing/conflicting/not_applicable), `denial_risk` badge, `rationale`, and `evidence[]` chips linking to the drawer. |
| **Before / After Readiness Scores** | `case.readiness_history[]` | First entry = "before", last = "after/current". Each has `score` (0–100), per-status counts, `overall_denial_risk`. Show delta after clarification (79 → 93 in the demo). |
| **Suggested Clarification Actions** | `case.clarification_questions[]` | Show `question`, `why_needed`, `suggested_action`; `status` open/answered. Answer via `POST /clarifications` with `{question_id, response}` → re-render from the returned case. |
| **Disclosure Review** | `case.disclosure_decisions[]` | `decision` include/exclude, `reason`, optional `phi_category`. Excluded rows are the "unrelated PHI withheld" story — render prominently. |
| **Prior Authorization Form Draft** | `case.form_draft` | `payer_form_name` (labeled MOCK), `fields[]` (`label`/`value`; `source_claim_ids` link back to packet claims), `attestation` rendered verbatim. |
| **Ready for Human Review banner** | `case.status == "ready_for_review"` | Terminal banner. Also show `form_draft.attestation`. There is no submit button to build — do not add one. |
| **Clickable note & FHIR citations** | `EvidenceItem` → `GET /api/cases/{case_id}/evidence/{source_id}` | Drawer shows `label` + `content`; highlight `span.start..span.end` when present; show `fhir_path` for structured items; `excerpt` is guaranteed verbatim. |
| **Packet view** (inside packet/disclosure area) | `case.packet` — `sections[]`, `claims[]`, `status` | Render sections; each claim chip links `evidence_ids` to the drawer. |
| **Verification panel** | `case.verification` — `passed`, `checked_claim_count`, `issues[]` | On failure show `issues` with `severity` and `suggested_resolution`; offer "Regenerate packet" (`POST /generate-packet`). |

## State → screen guide

| `case.status` | What the console shows / enables |
|---|---|
| `intake_ready` | Chart, note, policy header; "Run analysis" button (`POST /run`) |
| `analyzing` / `reanalyzing` | Progress state driven by timeline events (transient during the request) |
| `awaiting_clarification` | Matrix, score, questions; enable "Answer" and "Generate packet" |
| `packet_drafted` | Disclosure panel + packet; enable "Verify" |
| `verification_failed` | Verification issues; enable "Regenerate packet" |
| `verified` | Verified packet; enable "Draft form" |
| `ready_for_review` | Form draft + Ready-for-Review banner; only `demo/reset` remains |

## Error handling

Every non-2xx body is `ApiError`. Map `error_code` to UX:
`invalid_state_transition` / `question_already_answered` → refetch the case
and re-render (the UI was stale); `case_not_found` → return to demo entry;
anything else → toast with `message`.

## Ground rules for the frontend

1. Render only backend fields; never compute readiness, statuses, or risk
   client-side.
2. After any POST, replace local state wholesale with the returned case.
3. Always display the synthetic-data labeling (`case.synthetic`,
   `policy.synthetic`) and the form `attestation`.
4. Do not build any submit-to-payer affordance.
