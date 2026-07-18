"""Evidence retrieval tests (Agent C).

Covers parallel aggregation, per-source-family retrieval (medication, PT
referral, note duration, red-flag text), source-ID preservation, dense-chart
filtering, the negative-finding vs no-result distinction, the code-level
guarantee that workers never decide readiness, and the fail-open LLM refiner
(local fake provider — no real model call, no provider edit).
"""

from __future__ import annotations

import pytest

from app.agents.evidence_retriever import build_evidence_retriever
from app.contracts import (
    AuthLensCase,
    EvidenceCandidate,
    EvidenceConfidence,
    PolicyCriterion,
    SourceType,
)
from app.services.retrieval.models import (
    NEGATIVE_FINDING_MARKER,
    WorkerOutcome,
)
from app.services.retrieval.refiner import LLMCandidateRefiner, RefinerSelection

from tests.policy_retrieval.conftest import KNOWN_SOURCE_IDS

# A candidate that has been graded as "met"/"satisfied" would be a readiness
# decision leaking into retrieval — forbidden. These cues must never appear.
_DECISION_CUES = ("satisfied", "criterion is met", "criterion met", "ready for review")


# --------------------------------------------------------------------------- #
# Local fakes — Agent C tests never touch Agent B's provider implementation.
# --------------------------------------------------------------------------- #
class _KeepSubsetProvider:
    """Structured call returns a fixed subset of candidate ids to keep."""

    def __init__(self, keep_ids: list[str]) -> None:
        self._keep_ids = keep_ids

    def complete(self, *, system: str, prompt: str, max_tokens=None) -> str:  # pragma: no cover
        raise NotImplementedError

    def complete_structured(self, *, system, prompt, output_model, max_tokens=None):
        return output_model(keep_candidate_ids=list(self._keep_ids))


class _RaisingProvider:
    """Structured call always fails — the refiner must fall open to honesty."""

    def complete(self, *, system: str, prompt: str, max_tokens=None) -> str:  # pragma: no cover
        raise NotImplementedError

    def complete_structured(self, *, system, prompt, output_model, max_tokens=None):
        raise RuntimeError("provider unavailable")


def _make_candidates(criterion_id: str, n: int) -> list[EvidenceCandidate]:
    return [
        EvidenceCandidate(
            candidate_id=f"cand-{i}",
            criterion_id=criterion_id,
            source_id="note-001",
            source_type=SourceType.ENCOUNTER_NOTE,
            excerpt=f"excerpt {i}",
            confidence=EvidenceConfidence.MODERATE,
            relevance_rationale="matched terms",
        )
        for i in range(1, n + 1)
    ]


# --------------------------------------------------------------------------- #
# Retrieval behaviour
# --------------------------------------------------------------------------- #
def test_parallel_retrieval_aggregation(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    retriever = build_evidence_retriever()
    candidates, summary = retriever.retrieve_with_summary(case, criteria_by_id["LM-3"])
    assert candidates, "conservative-therapy criterion should surface candidates"
    # Candidates aggregate across more than one worker/source family.
    assert len({c.source_id for c in candidates}) >= 2
    workers_run = {run.worker for run in summary.worker_runs}
    assert {"encounter_note", "medications", "procedures_referrals"} <= workers_run
    # Every candidate gets a deterministic, criterion-scoped id.
    assert all(c.candidate_id.startswith("cand-LM-3-") for c in candidates)
    assert summary.iterations >= 1


def test_medication_retrieval_capped_low(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    candidates = build_evidence_retriever().retrieve(case, criteria_by_id["LM-3"])
    meds = [c for c in candidates if c.source_id == "fhir-med-001"]
    assert meds, "the Naproxen medication item should be retrieved for LM-3"
    for candidate in meds:
        assert "Naproxen" in candidate.excerpt
        # A prescription alone is never proof of completed/failed therapy.
        assert candidate.confidence is EvidenceConfidence.LOW
        assert "does not document completion" in candidate.relevance_rationale


def test_pt_referral_retrieval_capped_low(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    candidates = build_evidence_retriever().retrieve(case, criteria_by_id["LM-3"])
    referrals = [c for c in candidates if c.source_id == "fhir-ref-pt-001"]
    assert referrals, "the PT referral item should be retrieved for LM-3"
    for candidate in referrals:
        assert "physical therapy" in candidate.excerpt.lower()
        # A referral is never proof of completed therapy.
        assert candidate.confidence is EvidenceConfidence.LOW
        assert "does not document completion" in candidate.relevance_rationale


def test_note_duration_retrieval(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    candidates = build_evidence_retriever().retrieve(case, criteria_by_id["LM-2"])
    note_hits = [c for c in candidates if c.source_id == "note-001"]
    assert note_hits, "duration criterion should cite the note"
    assert any("weeks" in c.excerpt for c in note_hits)
    # An explicit duration anchor ("8 weeks") makes at least one hit high-confidence.
    assert any(c.confidence is EvidenceConfidence.HIGH for c in note_hits)


def test_red_flag_text_retrieval_flags_negative_finding(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    candidates = build_evidence_retriever().retrieve(case, criteria_by_id["LM-5"])
    note_hits = [c for c in candidates if c.source_id == "note-001"]
    assert note_hits, "red-flag screening is documented in the note"
    # 'denies ... trauma, fever ...' is a documented negative finding, flagged
    # as such — distinct from finding nothing.
    assert any(
        NEGATIVE_FINDING_MARKER in c.relevance_rationale for c in note_hits
    )


def test_source_id_preservation_and_verbatim_excerpts(
    case: AuthLensCase, criteria: list[PolicyCriterion]
) -> None:
    text_sources = {
        "note-001": case.encounter_note.text,
        "transcript-001": case.encounter_transcript.text,
    }
    retriever = build_evidence_retriever()
    for criterion in criteria:
        for candidate in retriever.retrieve(case, criterion):
            assert candidate.source_id in KNOWN_SOURCE_IDS
            if candidate.source_id in text_sources:
                content = text_sources[candidate.source_id]
                # Verbatim quote, and the recorded span reproduces it exactly.
                assert candidate.excerpt in content
                assert candidate.span is not None
                assert content[candidate.span.start : candidate.span.end] == candidate.excerpt


def test_dense_chart_filtering_excludes_unrelated_items(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    retriever = build_evidence_retriever()
    candidates, summary = retriever.retrieve_with_summary(case, criteria_by_id["LM-1"])
    # The unrelated 'seasonal allergic rhinitis' condition is never forwarded.
    assert all(c.source_id != "fhir-cond-002" for c in candidates)
    conditions_runs = [r for r in summary.worker_runs if r.worker == "conditions"]
    assert conditions_runs, "conditions worker should have run"
    # Two conditions exist but only the relevant one survives the prefilter.
    assert all(r.sources_total == 2 for r in conditions_runs)
    assert all(r.sources_considered < r.sources_total for r in conditions_runs)


def test_workers_never_decide_readiness(
    case: AuthLensCase, criteria: list[PolicyCriterion]
) -> None:
    retriever = build_evidence_retriever()
    for criterion in criteria:
        for candidate in retriever.retrieve(case, criterion):
            # 'accepted' is a downstream (Agent D) decision; retrieval leaves it open.
            assert candidate.accepted is None
            lowered = candidate.relevance_rationale.lower()
            assert not any(cue in lowered for cue in _DECISION_CUES)


def test_no_result_distinct_from_source_unavailable(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    _, summary = build_evidence_retriever().retrieve_with_summary(
        case, criteria_by_id["LM-5"]
    )
    outcomes = {run.worker: run.outcome for run in summary.worker_runs}
    # No clinician clarifications on the demo case -> source unavailable.
    assert outcomes["clarifications"] is WorkerOutcome.SOURCE_UNAVAILABLE
    # The note documents red flags -> candidates found. The two are different
    # outcomes, so "nothing to search" is never conflated with "found nothing".
    assert outcomes["encounter_note"] is WorkerOutcome.CANDIDATES_FOUND
    assert WorkerOutcome.SOURCE_UNAVAILABLE is not WorkerOutcome.NO_RESULT_FOUND


# --------------------------------------------------------------------------- #
# LLM relevance refiner — safe by construction
# --------------------------------------------------------------------------- #
def test_refiner_only_drops_candidates() -> None:
    candidates = _make_candidates("LM-3", 4)
    refiner = LLMCandidateRefiner(_KeepSubsetProvider(["cand-1", "cand-3"]))
    kept = refiner.refine(_criterion_stub(), candidates)
    kept_ids = {c.candidate_id for c in kept}
    assert kept_ids == {"cand-1", "cand-3"}
    # Only originals survive — nothing added or rewritten.
    assert all(c in candidates for c in kept)


def test_refiner_fails_open_on_provider_error() -> None:
    candidates = _make_candidates("LM-3", 4)
    refiner = LLMCandidateRefiner(_RaisingProvider())
    kept = refiner.refine(_criterion_stub(), candidates)
    assert kept == candidates  # deterministic result stands unchanged


def test_refiner_keeps_everything_when_model_selects_nothing() -> None:
    candidates = _make_candidates("LM-3", 4)
    refiner = LLMCandidateRefiner(_KeepSubsetProvider([]))
    kept = refiner.refine(_criterion_stub(), candidates)
    assert kept == candidates  # never silently drops all evidence


def test_refiner_skips_short_lists() -> None:
    candidates = _make_candidates("LM-3", 2)
    # Below the threshold the model is never called (raising provider proves it).
    refiner = LLMCandidateRefiner(_RaisingProvider())
    assert refiner.refine(_criterion_stub(), candidates) == candidates


def test_retriever_with_provider_fails_open(
    case: AuthLensCase, criteria_by_id: dict[str, PolicyCriterion]
) -> None:
    deterministic = build_evidence_retriever().retrieve(case, criteria_by_id["LM-3"])
    with_provider = build_evidence_retriever(_RaisingProvider()).retrieve(
        case, criteria_by_id["LM-3"]
    )
    assert with_provider == deterministic


def _criterion_stub() -> PolicyCriterion:
    return PolicyCriterion(
        criterion_id="LM-3",
        policy_id="MHP-IMG-2201",
        label="Completed and failed conservative treatment",
        requirement="The patient has completed conservative treatment.",
        category="conservative_therapy",
    )
