# Agent D — Evidence, Gaps, Readiness, Clarification — completion report

**Date:** 2026-07-18 · **Scope:** Evidence Mapper, Gap Detector, deterministic
Documentation Readiness calculator, Clinician Clarification Service.

## Delivered

- `backend/app/services/evidence/`
  - `verbatim.py` — verbatim-citation gate (`span_matches`, `locate`,
    `resolve_verbatim_span`); every accepted excerpt must appear
    character-for-character in its source.
  - `rules.py` — deterministic clinical-documentation rules: referral ≠
    completion, prescription ≠ adherence/failure, completion ≠ failure,
    diagnosis code ≠ exam finding, negative-screen detection,
    patient-reported detection (SUBJECTIVE section / `Patient:` turns),
    explicit-duration parsing separated from vague temporal language.
  - `relevance.py` — per-category relevance signals; candidates with no
    signal are rejected (unsupported mappings never become evidence).
  - `duration.py` — explicit duration parsing to days; "persistent/chronic"
    is detected but never converted to a number of weeks.
  - `mapper.py` — `DeterministicEvidenceMapper` (EvidenceMapper port):
    verbatim gate → relevance gate → dedupe → safety caps. Referral or
    prescription-only support on a `conservative_therapy` criterion is
    capped at LOW confidence with an explicit limitation note;
    patient-reported statements are labeled and capped at MODERATE.
    Citations (source_id, span, fhir_path) preserved unchanged.
  - `envelopes.py` — `EvidenceMappingEnvelope` (list wrapper for
    `complete_structured`).
- `backend/app/agents/evidence_mapper.py` — `LLMEvidenceMapper`: uses Agent
  B's `evidence_mapping` prompt via the frozen `LLMProvider` port, then
  re-applies every code gate to the model's output (an LLM answer can never
  weaken the verbatim or referral/prescription rules; invented items — not
  among submitted candidates — are dropped). `build_evidence_mapper` factory
  defaults to the deterministic mapper.
- `backend/app/services/readiness/`
  - `rubrics.py` — category rubrics producing `CriterionAssessment`
    (met/weak/missing/conflicting/not_applicable). Conservative-therapy
    rubric hard-codes: referral/prescription-only → **missing**; completion
    without documented outcome → **weak**; completion + "without sufficient
    improvement" (incl. via verbatim clinician clarification) → met;
    contradictory improvement statements → **conflicting** (stays until
    reviewed). Duration rubric: explicit durations only; conflicting
    documented durations → **conflicting**; vague temporal language → weak.
    Conditional criteria (applicability_note "only if…") with no triggering
    evidence → not_applicable.
  - `calculator.py` — deterministic Documentation Readiness score
    (`SCORE_NAME = "Documentation Readiness"`), base formula from
    DATA_CONTRACTS.md (`round(100*(met+0.5*weak)/(total−NA))`), optional
    criteria weighted 0.5 vs required 1.0 (reduces to the base formula when
    no criteria metadata is passed, keeping demo scores 79→93 exact),
    `status_counts`, `unresolved_required_gaps`, max denial risk. Never
    labeled or described as approval probability.
  - `questions.py` — clarification-question generation: at most one focused
    question per gapped criterion; raised for missing/conflicting criteria
    and high-denial-risk weak ones (matches the frozen examples where LM-6
    weak/medium gets no question); LM-3 wording matches
    `expected_demo_clarification` exactly; questions ask what was
    documented/done, never what should be done.
  - `detector.py` — `DeterministicGapDetector` (GapDetector port).
- `backend/app/agents/gap_detector.py` — port wiring surface
  (`build_gap_detector`); classification/scoring stay deterministic per
  AGENT_WORKFLOWS.md §6.
- `backend/app/services/clarifications/service.py` —
  `ClarificationService`: records the clinician's exact text verbatim
  (whitespace and all; empty text rejected), attaches author + timestamp,
  creates a provenance-bearing `clinician_clarification` EvidenceSource +
  EvidenceItem (source_id = clarification_id per DATA_CONTRACTS.md),
  re-runs assessment only for the question's criteria, and returns both the
  untouched prior assessments/readiness and the updated ones for the
  before-and-after display.

## Tests

- Command: `cd backend && uv run pytest tests/evidence_readiness`
- Result: **36 passed**. Frozen suite `uv run pytest tests/contracts`:
  **57 passed** (unchanged).
- Coverage of the required scenarios: PT referral insufficient; NSAID
  prescription insufficient; fixture LM-3 initially weak/missing; completion
  without outcome ≠ failure; missing duration; vague duration ≠ six weeks;
  conflicting duration stays conflicting; diagnosis code ≠ exam finding;
  absent red-flag documentation ≠ negative screen; not-applicable
  conditional criterion; clarification changes LM-3 to met with the
  clarification cited as evidence; before/after assessments and scores
  preserved (79 → 93 on the demo path, matching
  `contracts/examples/case_state_ready_for_review.json`); verbatim +
  provenance recording; citation preservation; unsupported/non-verbatim/
  invented/unknown-source evidence rejected (deterministic and LLM paths);
  no approval prediction in any output; ≤1 question per criterion with the
  exact LM-3 wording.

## Contract-change requests

None. One note for the integration agent (not a change request): the
`GapDetector.compute_readiness` port signature takes no `criteria`, so the
port method uses uniform weighting (identical to the DATA_CONTRACTS.md
formula). The optional-vs-required weighting is exposed as
`DeterministicGapDetector.compute_readiness_weighted(assessments, label,
criteria)` if the orchestrator wants it; the demo policy has no optional
criteria, so both paths give identical scores there.

## Dependency requests

- See `docs/dependency_requests/evidence-and-readiness.md` — none.

## Known gaps / follow-ups for integration

- `LLMEvidenceMapper` imports Agent B's `app.prompts.library` registry
  (read-only, inside methods) and codes against the `LLMProvider` port; it
  never imports `anthropic`. Wiring choice (deterministic vs LLM mapper) is
  the integration agent's via `build_evidence_mapper(sources, provider)`.
- `DeterministicGapDetector` and `DeterministicEvidenceMapper` take a
  `sources` mapping (`source_id → EvidenceSource`); the orchestrator should
  build it from Agent A's loaders (note, transcript, chart items) plus
  clarification sources from `ClarificationService.sources`.
- Rubric rationales interpolate short verbatim quotes from cited evidence —
  by design (source-grounded), but the packet generator should rely on the
  `evidence` list, not parse rationale text.
- `ClarificationService` assigns `clar-NNN` ids per service instance; the
  orchestrator should hold one instance per case (ids are unique within a
  case per DATA_CONTRACTS.md).
- Patient-reported detection is heuristic (SOAP headers, transcript turns,
  "patient reports" phrasing). It correctly labels the demo fixture; broader
  Abridge-dataset notes with different section headers may need more
  patterns — noted for evaluation, not a blocker.
