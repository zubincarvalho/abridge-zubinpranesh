# ADR 0004 — Synthetic demo fixture

**Status:** Accepted · **Date:** 2026-07-18

## Context

The demo needs a clinically plausible case whose documentation gap is exact
and reproducible. Real patient data is out of the question. The official Abridge
dataset (`synthetic-ambient-fhir-25/`, 25 synthetic encounters) is present
but general-purpose — none of its encounters is guaranteed to exhibit the
exact lumbar-MRI documentation gap the demo turns on.

## Decision

Author a fully synthetic fixture and policy, frozen after this phase:

- `data/fixtures/lumbar_mri_prior_auth.json` — fictional patient "Jordan
  Rivera", Abridge-style note, transcript, FHIR-style chart items, requested
  service (CPT 72148), and the fictional payer policy reference. Labeled
  synthetic in-band (`_synthetic_notice`, `synthetic: true`, "(synthetic)" in
  display strings).
- `data/policies/lumbar_mri_policy.md` — fictional payer "Meridian Health
  Plans", policy MHP-IMG-2201, criteria LM-1..LM-7, synthetic banner at top.
- The fixture is **engineered around the demo gap**: NSAID listed and PT
  referral present, but completion/failure of conservative therapy is never
  documented (a frozen test asserts the note does not contain "completed").
- The official Abridge dataset stays at `synthetic-ambient-fhir-25/`,
  read-only, loaded by Agent A (`backend/app/data/`) — it never replaces the
  frozen fixture for the canonical demo and is never modified.

## Consequences

- The demo is deterministic and safe to publish; contract examples were
  generated from this fixture and are span-exact.
- Synthetic labeling must survive into the UI (`case.synthetic`,
  `policy.synthetic`, attestation text).
- Editing fixture text would silently break span offsets in examples and the
  gap the whole demo depends on — hence the freeze.
