# Agent E (Output Safety Pipeline) — completion report

**Date:** 2026-07-18 · **Scope:** minimum-necessary disclosure filter,
packet generator, independent packet verifier, single safe revision, mock
payer form drafter.

## Delivered

- `backend/app/services/disclosure/`
  - `sources.py` — resolves every addressable source in a case (note,
    transcript, chart items, clinician clarifications) to its exact
    content; maps each cited source to the criteria it supports. Shared by
    all three downstream stages so excerpt checks are against real text.
  - `filter.py` — `MinimumNecessaryDisclosureFilter`: one decision per
    candidate item; **default EXCLUDE**; INCLUDE only when the item's
    evidence is linked to a policy criterion by an assessment (or it is the
    requested service order itself); every reason names the criteria that
    need the item; keyword-based `phi_category` detection (behavioral
    health, substance use, reproductive, infectious, genetic) flags
    sensitive items for clinician review whether included or excluded.
    Blanket includes are structurally impossible (per-item review only).
- `backend/app/services/packet/builder.py` —
  `EvidenceGroundedPacketGenerator`: deterministic assembly from typed
  artifacts only. Refuses to run before disclosure review. Ten sections:
  patient/request summary, requested service, clinical indication,
  medical-necessity narrative, criterion-by-criterion evidence matrix
  (verbatim quotes + source labels), exact citations (evidence id, source,
  span/fhir_path), remaining gaps (missing/weak/conflicting — conflicts
  stated explicitly), disclosure summary (include/exclude/flag counts,
  excluded content withheld), clinician attestation placeholder, and a
  human-review warning ending with the fixed sentence
  **"Requires clinician review before submission."** Clinical claims carry
  the assessment's evidence ids filtered to INCLUDE'd sources; policy
  claims restate parsed criteria verbatim. Output is always `DRAFT`.
- `backend/app/services/verification/`
  - `verifier.py` — `IndependentPacketVerifier`: shares no composition
    logic with the generator; re-derives all indexes from the case. Checks:
    every clinical claim cites resolving evidence; cited evidence belongs
    to the claim's criterion; excerpts are verbatim in their source;
    referral ≠ completion and prescription ≠ failure (claims asserting a
    therapy outcome need a documenting source — note/transcript/
    clarification); every applicable criterion represented; policy claims
    match parsed criteria (word-overlap check catches invented
    requirements); conflicting assessments remain visible; no EXCLUDE'd
    source is cited and no excluded text appears; no approval-guarantee
    language (with negated-idiom scrubbing so "not a guarantee of approval"
    passes); packet ends with the fixed human-review sentence. `passed`
    only with zero BLOCKING issues.
  - `revision.py` — `SafePacketReviser`: at most **one** revision per
    packet id, acting only on issues prefixed `Formatting:` /
    `Citation placement:` (append missing review sentence; drop dangling
    claim refs). Never touches claim text, evidence, or statuses — a
    missing fact can never be revised into a satisfied fact (tested).
- `backend/app/services/form_draft/drafter.py` — `MockPayerFormDrafter`:
  hard gate raising `UnverifiedPacketError` unless packet status is
  `VERIFIED`, the verification result matches the packet id, and
  `passed` is True with no blocking issues; also rejects non-typed input
  (arbitrary prose) and, via `draft_by_id`, any packet id not on the case.
  Fields are drawn from packet claims (`source_claim_ids`); unresolved
  warnings surface in an `f-warnings` field; fixed attestation; status
  literal `ready_for_review`; no submit action or field exists anywhere
  (tested by API-surface scan).
- `backend/app/agents/{disclosure_agent,packet_generator,verification_agent}.py`
  — thin port-facing entry points satisfying `DisclosureFilter`,
  `PacketGenerator`, `PacketVerifier`; `VerificationAgent.revise_once`
  exposes the safe revision.
- `backend/tests/output_pipeline/` — 45 tests (conftest builds a synthetic
  case with relevant, unrelated, and sensitive chart items plus an
  answered clarification).

## Tests

- Command: `cd backend && uv run pytest tests/output_pipeline`
- Result: **45 passed**. Full suite (incl. frozen `tests/contracts`):
  **201 passed, 1 skipped** — contract suite untouched and green.
- Required scenarios covered: unrelated info excluded · relevant evidence
  retained · unsupported claim blocked · invalid citation blocked ·
  invented policy requirement blocked · referral-as-completion blocked ·
  prescription-as-failure blocked · unverified packet cannot create form ·
  verified packet creates form · final state `ready_for_review` · no
  submission field or action exists · safe revision fixes formatting once
  and never a missing fact · hidden conflict blocked · approval guarantee
  blocked · sensitive item flagged for human review.

## Contract-change requests

None. All contracts and ports were sufficient as frozen.

## Dependency requests

None — see `docs/dependency_requests/output-pipeline.md`.

## Known gaps / follow-ups for integration

- All four implementations are **deterministic (no LLM calls)**: the
  upstream artifacts (assessments with verbatim evidence, parsed criteria)
  already contain everything the output pipeline needs, and deterministic
  logic makes the safety gates testable and non-bypassable. If integration
  wants LLM-polished narrative prose, it should be added as a *presentation
  layer on top of* the claims — the verifier as written will re-check any
  such text (verbatim excerpts, exclusions, guarantees), so it composes
  safely.
- Orchestration notes (Agent F): call order is
  `DisclosureAgent.review` → store decisions on the case →
  `PacketGeneratorAgent.generate` → `VerificationAgent.verify`; on pass,
  the orchestrator sets packet status to `VERIFIED` (the generator and
  verifier never do) and stores the `VerificationResult`; `FormDrafter`
  then accepts it. `VerificationAgent.revise_once` is available for a
  single presentation-only fix before re-verifying; anything else goes
  through the explicit regenerate path (`verification_failed` →
  `packet_drafted`).
- `MockPayerFormDrafter.draft_by_id(case, packet_id)` is provided beyond
  the port so Agent G can honor "accepts a verified packet ID" without
  re-plumbing objects; the port-shaped `draft(...)` remains authoritative.
- `SafePacketReviser` tracks revised packet ids in memory; if the API layer
  constructs a new agent per request, the one-revision bound should be
  enforced per stored packet (e.g., keep the reviser in the composition
  root or persist a `revised` marker with the packet).
- Packet ids are `pkt-<case_id>` (deterministic per case). If a case can
  regenerate packets multiple times and history must be kept, integration
  may want a sequence suffix.
