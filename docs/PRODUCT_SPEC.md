# AuthLens Product Specification

## One-line pitch

AuthLens is a point-of-capture prior authorization readiness agent that helps
clinicians prevent avoidable denials **before** submission — while the
patient is still in the room and the documentation gap can still be closed.

## Problem

Prior authorization denials are frequently caused not by inappropriate care
but by missing documentation: the payer's policy requires a specific fact
(e.g., "six weeks of conservative therapy completed and failed") that the
chart implies but never states. By the time the denial arrives, the encounter
is over and closing the gap costs days of back-and-forth.

## What AuthLens does

AuthLens runs downstream of an Abridge-style encounter note. Its inputs:

1. Encounter note
2. Encounter transcript (when available)
3. Structured FHIR patient context
4. Requested service
5. Clinical indication
6. Payer medical-necessity policy

Its pipeline (see SYSTEM_ARCHITECTURE.md):

1. **Parse** the payer policy into discrete medical-necessity criteria.
2. **Search** the note, transcript, and FHIR record for supporting evidence
   (parallel, per criterion).
3. **Map** criteria to exact cited evidence — verbatim excerpts with spans.
4. **Classify** each criterion: `met`, `weak`, `missing`, `conflicting`, or
   `not_applicable`, each with a denial-risk grade.
5. **Ask** precise point-of-capture clarification questions for gaps.
6. **Re-evaluate** readiness when the clinician answers (answers are recorded
   verbatim as new evidence).
7. **Exclude** unrelated patient information (explicit minimum-necessary
   disclosure decisions).
8. **Generate** a focused prior authorization packet where every clinical and
   policy statement is a claim linked to cited evidence.
9. **Verify** every claim independently before anything moves forward.
10. **Populate** a mock payer form from the verified packet.
11. **Stop** at "Ready for Clinician Review."

## What AuthLens must never do

These are hard product boundaries, enforced in contracts, ports, tests, and
docs (see SAFETY_AND_HUMAN_REVIEW.md):

- Diagnose the patient.
- Recommend treatment.
- Guarantee or predict payer approval (readiness ≠ approval odds).
- Submit to a real payer (no submission endpoint; no `submitted` state).
- Treat a referral as proof of completed therapy.
- Treat a prescription as proof of treatment failure.
- Expose unrelated PHI (default is exclusion).
- Operate as a generic chatbot or a basic RAG system — every output is a
  typed artifact in a deterministic workflow, grounded in cited sources.

## Primary demo: lumbar-spine MRI readiness

Single demonstration workflow, driven entirely by synthetic data
(`data/fixtures/lumbar_mri_prior_auth.json`, `data/policies/lumbar_mri_policy.md`).

**Patient (synthetic):** chronic lower-back pain with radicular symptoms.
The chart contains: low-back pain radiating down the leg; positive
straight-leg raise; suspected lumbar radiculopathy; MRI lumbar spine ordered;
an NSAID on the medication list; a physical-therapy referral.

**Policy (synthetic, MHP-IMG-2201):** seven criteria — appropriate
indication (LM-1), ≥6 weeks symptom duration (LM-2), completed **and failed**
conservative treatment (LM-3), neurologic/exam findings (LM-4), red-flag
screening (LM-5), functional limitation (LM-6), clinical rationale for MRI
(LM-7).

**The central gap:** an NSAID prescription and a PT referral do **not** prove
the patient completed six weeks of conservative therapy without improvement.
AuthLens classifies LM-3 as `missing` (high denial risk) and asks:

> "Have you completed at least six weeks of physical therapy,
> anti-inflammatory medication, or a home-exercise program without sufficient
> improvement?"

After the clinician confirms, LM-3 becomes `met` (evidence: the recorded
clarification), and documentation readiness rises (79 → 93 in the canonical
example payloads). The case then flows through disclosure review, packet
generation, verification, and form drafting, ending at **Ready for Clinician
Review**.

## Demo walkthrough (API calls)

1. `GET /api/demo-case` — seeded case, status `intake_ready`.
2. `POST /api/cases/{id}/run` — analysis; status `awaiting_clarification`;
   readiness matrix shows LM-3 missing; question surfaced.
3. `POST /api/cases/{id}/clarifications` — clinician answers; re-evaluation;
   readiness increases.
4. `POST /api/cases/{id}/generate-packet` — disclosure review + packet draft.
5. `POST /api/cases/{id}/verify` — every claim checked; status `verified`.
6. `POST /api/cases/{id}/form-draft` — mock form; status `ready_for_review`.
7. `POST /api/demo/reset` — back to step 1.

## Success criteria for the hackathon demo

- The LM-3 gap is detected and explained with the referral/prescription
  distinction stated explicitly.
- The clarification question matches the spec wording.
- Readiness visibly increases after clarification (before/after scores).
- Every claim in the packet is clickable back to a verbatim source excerpt.
- The unrelated chart item (allergic rhinitis) is visibly excluded with a reason.
- The workflow stops at Ready for Clinician Review.
