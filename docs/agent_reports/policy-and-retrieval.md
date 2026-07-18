# Agent C — Policy & Retrieval — completion report

**Date:** 2026-07-18 · **Scope:** Deterministic payer-policy parser
(`PolicyParser` port) and parallel per-criterion evidence retriever
(`EvidenceRetriever` port).

## Delivered

- `backend/app/services/policy/`
  - `markdown_parser.py` — mechanical markdown extraction of
    `### <ID>. <label>` criterion sections with their verbatim body text and
    exact character offsets (`policy_text[body_start:body_end] == body`).
    `conditional_sentence` returns the verbatim sentence carrying a
    multi-word conditionality marker (`only if`, `if applicable`, `unless`,
    …) — a bare "if" inside an example never reclassifies a required
    criterion.
  - `routes.py` — routing registry. `PolicyRoute` / `CategoryRule` /
    `PolicyRouter` resolve a `PayerPolicy` to a parsing configuration by
    policy id first, then service code. Ships exactly one supported route
    (`LUMBAR_MRI_ROUTE` — MHP-IMG-2201, CPT 72148, `LM-\d+` ids, label→category
    keyword rules). `register()` is an extensibility seam; an unmatched policy
    raises `UnsupportedPolicyError` — no unsupported specialty is ever guessed.
  - `parser.py` — `DeterministicPolicyParser` (implements the frozen
    `PolicyParser` port). No model call. Rejects a policy with no criterion
    sections, duplicate criterion ids, ids not matching the route pattern,
    criteria with no citable body (`MissingCitationError`), and labels
    matching no category rule ("refusing to guess"). Separates
    required vs conditional and, as a final self-check, re-verifies every
    recorded span still equals the requirement text before returning.
  - `models.py` — `ParsedCriterion` (service-internal; carries source
    location + `RequirementKind`) with `to_contract()` → frozen
    `PolicyCriterion`; `PolicySourceLocation`; `RequirementKind` enum.
  - `errors.py` — `PolicyParseError` base + `UnsupportedPolicyError`,
    `DuplicateCriterionError`, `MissingCitationError` (parsing fails loudly,
    never invents or silently drops a requirement).
- `backend/app/agents/policy_parser.py` — wiring surface
  (`build_policy_parser(router=None)`); the orchestrator binds this to the
  `PolicyParser` port. Fully deterministic, never sees patient data.
- `backend/app/services/retrieval/`
  - `workers.py` — focused workers, one per source family (encounter note,
    transcript, clarifications, prior-encounter history, and chart-item
    workers for conditions / medications / procedures-referrals /
    service-requests / observations-diagnostics). Deterministic filtering
    only — no model call inside a worker. Text excerpts carry verbatim spans;
    chart excerpts are the exact `display`/`detail` field with `fhir_path`
    naming the field. `select_chart_items` narrows by resource category then
    query terms so a dense chart is never forwarded wholesale. Safety cap:
    on `conservative_therapy` criteria, a referral/prescription with no
    completion/failure language is capped at LOW with an explicit note.
    Documented negative findings (e.g. "denies fever") are kept and flagged,
    distinct from "no result found".
  - `queries.py` — category-routed cumulative query tiers + anchor patterns
    (explicit-duration regex, `m54.x` code, straight-leg-raise). `plan_for`
    falls back to terms derived from the criterion's own language for unknown
    categories. `completion_terms` exist solely to enforce the
    conservative-therapy safety rule.
  - `text_search.py` — sentence splitter with exact offsets and lowercase
    term / anchor matching; every hit is a verbatim slice of the source.
  - `retriever.py` — `ParallelEvidenceRetriever` (implements the frozen
    `EvidenceRetriever` port). Fans workers out concurrently
    (`ThreadPoolExecutor`), merges + dedupes typed candidates, assigns stable
    `cand-<criterion>-NNN` ids, and records a transparent
    `RetrievalEventSummary`. Bounded loop (`MAX_ITERATIONS = 3`): broadens
    query tiers only when a **required** criterion's pass is uncertain (no
    candidate at MODERATE+); conditional criteria never loop; the honest
    result — possibly empty — is always returned. Never classifies a
    criterion as met.
  - `refiner.py` — optional `LLMCandidateRefiner` (via the frozen
    `LLMProvider` port). Runs strictly after deterministic filtering; sees
    only already-filtered excerpts; may only *drop* candidates by id (cannot
    add text, rewrite an excerpt, raise confidence, or judge fulfilment); on
    any provider error or empty/unknown-id selection the deterministic result
    stands unchanged (fail open to honesty).
  - `models.py` — `WorkerOutcome`, `WorkerRunSummary`, `RetrievalEventSummary`
    (counts + human-readable notes only — never prompts, completions, or
    chain-of-thought, never a readiness decision).
- `backend/app/agents/evidence_retriever.py` — wiring surface
  (`build_evidence_retriever(provider=None, …)`); deterministic by default,
  pass a `provider` to enable the safe refiner, `encounter_history_sources`
  to inject prior-encounter text for the multi-encounter dataset.

## Tests

- Command: `cd backend && uv run pytest tests/policy_retrieval`
- Result: **25 passed** (11 policy parser + 14 retrieval). Frozen suite
  `uv run pytest tests/contracts`: **57 passed** (unchanged).
- Coverage: lumbar-MRI section extraction; verbatim requirement text equals
  its recorded source span; required vs conditional separation from exact
  policy language; duplicate-id / unsupported-policy / missing-citation /
  unknown-category rejection; routing by policy id and by service code.
  Retrieval: parallel aggregation and dedupe; per-source-family retrieval
  (medication, PT referral, transcript, chart categories, clarifications);
  verbatim spans on text excerpts and `fhir_path` on chart excerpts;
  chart narrowing before emission; referral/prescription capped at LOW on
  conservative-therapy criteria; documented negative finding kept and flagged
  vs "no result found"; bounded loop broadens only for uncertain required
  criteria; refiner can only drop and fails open on provider error.

## Contract-change requests

None. `DeterministicPolicyParser` and `ParallelEvidenceRetriever` implement
the frozen `PolicyParser` / `EvidenceRetriever` ports as written.

## Dependency requests

- See `docs/dependency_requests/policy-and-retrieval.md` — none.

## Known gaps / follow-ups for integration

- **Wiring is deterministic by default.** `build_policy_parser()` needs no
  provider. `build_evidence_retriever()` is deterministic unless the
  integration agent passes an `LLMProvider`, which only enables the
  drop-only refiner — retrieval correctness never depends on the model.
- **Source-id → text mapping for spans.** Text candidates carry
  `(source_id, span)` into the encounter note / transcript / clarification
  text; the integration agent / evidence mapper must resolve spans against
  the same source content Agent A loads (source-id conventions per
  DATA_CONTRACTS.md).
- **Prior-encounter history.** `EncounterHistoryWorker` reports
  `source_unavailable` on the single-encounter demo case; pass
  `encounter_history_sources` (built from Agent A's loaders) to search prior
  encounters in the broader Abridge dataset.
- **Chart-item categories** are matched against the `ChartItem.category`
  values Agent A emits (`condition`, `medication`, `procedure`, `referral`,
  `service_request`, `observation`, `other`); a new category from the loader
  needs a matching worker (add one — no contract change).
- **New payer specialties** register a `PolicyRoute` via
  `build_policy_parser(PolicyRouter(routes=…))`; unsupported policies raise
  `UnsupportedPolicyError` rather than being parsed on a guess.
- `RetrievalEventSummary.as_event_detail()` is ready for the orchestrator to
  attach to an `AgentEvent.detail` (counts/notes only, no CoT).
