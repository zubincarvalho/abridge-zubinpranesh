# Official Abridge Dataset — Pipeline Reference

Location: **`synthetic-ambient-fhir-25/`** (repo root). Fully synthetic,
labeled as such in-band (`metadata.synthetic: true` on every record,
`summary.json.synthetic: true`). **Read-only for every agent, including the
integration agent** — load it, never modify, reformat, or move its files.

## Verified (2026-07-18, foundation phase)

Continuously enforced by `backend/tests/contracts/test_abridge_dataset.py`:

- `synthetic-ambient-fhir-25.jsonl` parses to **25 records**; the `.json`
  array is byte-identical in content; `summary.json` indexes the same ids.
- Every record maps cleanly into our frozen intake contracts
  (`PatientSummary`, `EncounterNote`, `EncounterTranscript`, `ChartItem`)
  and survives strict (`extra="forbid"`) validation.
- FHIR resource ids are globally unique → safe to use directly as
  `source_id`s for the citation drawer.
- Every FHIR resource group present in the data has a `ChartItem.category`
  mapping; every chart item gets a non-empty display label.
- All `gender` values (`male`/`female`) fall inside our `sex` literal.

## Record shape (per `schema.json`)

| Field | Content |
|---|---|
| `id` | `<patient_id>::<encounter_id>` |
| `metadata` | date, `visit_title`, visit type/status, `synthetic`, resource counts |
| `patient_context` | FHIR `Patient` resource + longitudinal summary (condition/medication labels, per-type counts) |
| `encounter_fhir` | FHIR `Encounter` + `related_resources` grouped by type (Condition, Observation, Procedure, DiagnosticReport, MedicationRequest, Immunization, ImagingStudy) |
| `transcript` | speaker-labeled ambient conversation (`DR:`/`PT:`/…) |
| `note` | SOAP-style clinical note (markdown) |
| `after_visit_summary` (+ provenance) | patient-facing summary extracted from the note |

## Loader specification (Agent A, `backend/app/data/`)

The reference mapping lives in
`backend/tests/contracts/test_abridge_dataset.py` — **if the loader and that
test disagree, the test is authoritative.**

| Dataset field | Contract | Rule |
|---|---|---|
| `metadata.patient_id`, `patient_context.patient` | `PatientSummary` | `display_name` = given + family + " (synthetic)"; `birth_date` = `birthDate`; `sex` = `gender` |
| `note`, `metadata.visit_title` | `EncounterNote` | `source_id` = `note-<encounter_id>` |
| `transcript` | `EncounterTranscript` | `source_id` = `transcript-<encounter_id>` |
| each resource in `encounter_fhir.related_resources` | `ChartItem` | `source_id` = FHIR resource `id`; label from `code.text` → first `coding.display` → generic fallback |

FHIR resourceType → `ChartItem.category`: Condition→`condition`,
MedicationRequest→`medication`, Procedure→`procedure`,
Observation/DiagnosticReport→`observation`, Immunization/ImagingStudy→`other`,
ServiceRequest→`service_request` (none present in this dataset — referrals
appear only as note text).

Known limitation: 23 `MedicationRequest` resources carry a bare
`medicationReference` URN with no display (the referenced `Medication`
resource is not shipped) → label falls back to
`"MedicationRequest (unlabeled)"`; the medication's name, when needed, comes
from the note/transcript text instead.

## How AuthLens uses this data

1. **Canonical demo unchanged.** The lumbar-MRI walkthrough runs on the
   hand-authored fixture (`data/fixtures/`) because its LM-3 gap is
   engineered and span-exact (ADR 0004). The Abridge dataset does not
   replace it.
2. **Additional intake cases.** `POST /api/cases` accepts a `fixture_id`;
   Agent A's loader exposes dataset records as fixtures (e.g.
   `abridge:<record_id>`), turning any of the 25 encounters into an
   `intake_ready` case with chart, note, and transcript panels fully
   populated. Two encounters are natural secondary demos for our domain:
   *"General exam — chronic low back pain and positive depression screen"*
   and *"General exam — hypertension treatment initiation and chronic low
   back pain"*.
3. **Realistic retrieval testing.** Agents C/D use dataset notes and
   transcripts (via the loader, in their own test dirs) to exercise
   evidence retrieval/mapping against text they didn't write — verbatim-
   excerpt and span rules must hold on ambient-style prose, not just our
   curated fixture.
4. **Disclosure-review realism.** Dataset encounters carry rich unrelated
   context (immunizations, screenings, unrelated conditions) — exactly what
   the minimum-necessary disclosure filter must exclude, making Agent E's
   exclusion logic demonstrable beyond the single seeded rhinitis item.
5. **What we do NOT use it for.** No payer policies ship with the dataset —
   policies remain hackathon-authored (`data/policies/`). The
   `after_visit_summary` is patient-facing and unused by AuthLens.
