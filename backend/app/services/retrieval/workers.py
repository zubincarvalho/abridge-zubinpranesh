"""Focused retrieval workers (Agent C).

Each worker searches exactly one source family (encounter note, transcript,
chart-item categories, clarifications, encounter history) and returns typed
``EvidenceCandidate`` records plus a transparent ``WorkerRunSummary``.

Hard rules enforced here:
- Deterministic filtering only — no model call happens inside a worker.
- Excerpts are verbatim: text-source excerpts carry spans into the source;
  chart-item excerpts are the exact ``display``/``detail`` field text with
  ``fhir_path`` naming the field (span optional for structured data).
- Chart workers narrow by resource category and query terms before emitting
  anything, so a dense chart is never forwarded wholesale.
- Workers never decide whether a criterion is satisfied; ``accepted`` stays
  ``None`` and rationales describe term matches only.
- A referral or prescription without documented completion/failure language
  is capped at LOW relevance for conservative-therapy criteria.
- A documented negative clinical finding (e.g. "denies fever") is returned
  as a candidate and flagged as such — distinct from finding nothing.
"""

import re
from dataclasses import dataclass
from typing import Protocol, Sequence

from app.contracts import (
    AuthLensCase,
    ChartItem,
    EvidenceCandidate,
    EvidenceConfidence,
    EvidenceSource,
    PolicyCriterion,
    SourceType,
    TextSpan,
)

from app.services.retrieval.models import (
    NEGATIVE_FINDING_MARKER,
    NO_RESULT_NOTE,
    WorkerOutcome,
    WorkerRunSummary,
)
from app.services.retrieval.queries import QueryPlan
from app.services.retrieval.text_search import find_text_hits

_PROVISIONAL_ID = "cand-unassigned"

_REFERRAL_PRESCRIPTION_NOTE = (
    "This excerpt documents an order, referral, or prescription only; it does not "
    "document completion of therapy or lack of improvement."
)

_NEGATIVE_FINDING_NOTE = (
    f"{NEGATIVE_FINDING_MARKER} — the item is explicitly recorded as absent; "
    "this is different from missing documentation."
)


@dataclass(frozen=True)
class WorkerRun:
    candidates: tuple[EvidenceCandidate, ...]
    summary: WorkerRunSummary


class RetrievalWorker(Protocol):
    name: str
    kind: str

    def run(
        self,
        case: AuthLensCase,
        criterion: PolicyCriterion,
        terms: tuple[str, ...],
        plan: QueryPlan,
        iteration: int,
    ) -> WorkerRun:
        ...


def _score(
    plan: QueryPlan, matched_terms: tuple[str, ...], anchor_matched: bool, text: str
) -> tuple[EvidenceConfidence, str | None]:
    """Deterministic relevance score for one hit, with safety caps."""
    if plan.completion_terms:
        lowered = text.lower()
        if not any(term in lowered for term in plan.completion_terms):
            return EvidenceConfidence.LOW, _REFERRAL_PRESCRIPTION_NOTE
        if anchor_matched or len(matched_terms) >= 2:
            return EvidenceConfidence.HIGH, None
        return EvidenceConfidence.MODERATE, None
    if anchor_matched or len(matched_terms) >= 3:
        return EvidenceConfidence.HIGH, None
    if len(matched_terms) >= 2:
        return EvidenceConfidence.MODERATE, None
    return EvidenceConfidence.LOW, None


def _rationale(
    plan: QueryPlan,
    matched_terms: tuple[str, ...],
    anchor_matched: bool,
    where: str,
    negated: bool,
    cap_note: str | None,
) -> str:
    matched_text = ", ".join(matched_terms) if matched_terms else "duration/code pattern"
    parts = [f"Matched {plan.category} search terms ({matched_text}) in {where}."]
    if anchor_matched:
        parts.append("A category-specific pattern (e.g. an explicit duration or code) also matched.")
    if negated and plan.category == "red_flags":
        parts.append(_NEGATIVE_FINDING_NOTE)
    if cap_note:
        parts.append(cap_note)
    return " ".join(parts)


class TextSourceWorker:
    """Base worker for free-text sources; excerpts carry verbatim spans."""

    kind = "text"
    unavailable_note = "Source not available on this case."

    def __init__(self, name: str) -> None:
        self.name = name

    def _sources(self, case: AuthLensCase) -> list[tuple[str, SourceType, str, str]]:
        """Return (source_id, source_type, label, content) tuples."""
        raise NotImplementedError

    def run(
        self,
        case: AuthLensCase,
        criterion: PolicyCriterion,
        terms: tuple[str, ...],
        plan: QueryPlan,
        iteration: int,
    ) -> WorkerRun:
        sources = self._sources(case)
        if not sources:
            return WorkerRun(
                candidates=(),
                summary=WorkerRunSummary(
                    worker=self.name,
                    kind=self.kind,
                    iteration=iteration,
                    sources_total=0,
                    sources_considered=0,
                    candidates_found=0,
                    outcome=WorkerOutcome.SOURCE_UNAVAILABLE,
                    note=self.unavailable_note,
                ),
            )
        candidates: list[EvidenceCandidate] = []
        for source_id, source_type, label, content in sources:
            for hit in find_text_hits(content, terms, plan.anchor_patterns):
                confidence, cap_note = _score(
                    plan, hit.matched_terms, hit.anchor_matched, hit.sentence.text
                )
                candidates.append(
                    EvidenceCandidate(
                        candidate_id=_PROVISIONAL_ID,
                        criterion_id=criterion.criterion_id,
                        source_id=source_id,
                        source_type=source_type,
                        excerpt=hit.sentence.text,
                        span=TextSpan(start=hit.sentence.start, end=hit.sentence.end),
                        confidence=confidence,
                        relevance_rationale=_rationale(
                            plan, hit.matched_terms, hit.anchor_matched, label, hit.negated, cap_note
                        ),
                    )
                )
        return WorkerRun(
            candidates=tuple(candidates),
            summary=WorkerRunSummary(
                worker=self.name,
                kind=self.kind,
                iteration=iteration,
                sources_total=len(sources),
                sources_considered=len(sources),
                candidates_found=len(candidates),
                outcome=(
                    WorkerOutcome.CANDIDATES_FOUND
                    if candidates
                    else WorkerOutcome.NO_RESULT_FOUND
                ),
                note=None if candidates else NO_RESULT_NOTE,
            ),
        )


class EncounterNoteWorker(TextSourceWorker):
    unavailable_note = "No encounter note attached to this case."

    def __init__(self) -> None:
        super().__init__("encounter_note")

    def _sources(self, case: AuthLensCase) -> list[tuple[str, SourceType, str, str]]:
        note = case.encounter_note
        return [(note.source_id, SourceType.ENCOUNTER_NOTE, note.title, note.text)]


class TranscriptWorker(TextSourceWorker):
    unavailable_note = "No transcript attached to this case."

    def __init__(self) -> None:
        super().__init__("transcript")

    def _sources(self, case: AuthLensCase) -> list[tuple[str, SourceType, str, str]]:
        transcript = case.encounter_transcript
        if transcript is None:
            return []
        return [
            (
                transcript.source_id,
                SourceType.ENCOUNTER_TRANSCRIPT,
                "encounter transcript",
                transcript.text,
            )
        ]


class ClarificationsWorker(TextSourceWorker):
    """Recorded clinician clarifications, cited verbatim by clarification_id."""

    unavailable_note = "No clinician clarifications recorded on this case."

    def __init__(self) -> None:
        super().__init__("clarifications")

    def _sources(self, case: AuthLensCase) -> list[tuple[str, SourceType, str, str]]:
        return [
            (
                clarification.clarification_id,
                SourceType.CLINICIAN_CLARIFICATION,
                f"clinician clarification {clarification.clarification_id}",
                clarification.response,
            )
            for clarification in case.clarifications
        ]


class EncounterHistoryWorker(TextSourceWorker):
    """Prior-encounter sources, searched where available.

    The demo case carries a single encounter, so this worker reports
    ``source_unavailable`` unless prior-encounter ``EvidenceSource`` records
    are injected at construction time (integration seam for the Abridge
    multi-encounter dataset).
    """

    unavailable_note = "No prior-encounter history is attached to this case."

    def __init__(self, extra_sources: Sequence[EvidenceSource] = ()) -> None:
        super().__init__("encounter_history")
        self._extra_sources = tuple(extra_sources)

    def _sources(self, case: AuthLensCase) -> list[tuple[str, SourceType, str, str]]:
        return [
            (source.source_id, source.source_type, source.label, source.content)
            for source in self._extra_sources
        ]


def select_chart_items(
    items: Sequence[ChartItem], categories: tuple[str, ...], terms: tuple[str, ...]
) -> list[tuple[ChartItem, tuple[str, ...], str]]:
    """Deterministic prefilter: resource category first, then term matching.

    Returns (item, matched_terms, matched_field) for surviving items. This is
    the narrowing step that keeps a dense chart from ever being forwarded
    wholesale — anything failing the category or keyword filter is dropped
    before candidates (or any future model payload) are built.
    """
    selected: list[tuple[ChartItem, tuple[str, ...], str]] = []
    for item in items:
        if item.category not in categories:
            continue
        display = item.display.lower()
        detail = (item.detail or "").lower()
        detail_matches = tuple(term for term in terms if term in detail)
        display_matches = tuple(term for term in terms if term in display)
        if not detail_matches and not display_matches:
            continue
        if len(detail_matches) >= len(display_matches) and item.detail:
            selected.append((item, detail_matches, "detail"))
        else:
            selected.append((item, display_matches, "display"))
    return selected


class ChartItemWorker:
    """Base worker for structured chart items of specific categories."""

    kind = "chart"

    def __init__(self, name: str, categories: tuple[str, ...]) -> None:
        self.name = name
        self.categories = categories

    def run(
        self,
        case: AuthLensCase,
        criterion: PolicyCriterion,
        terms: tuple[str, ...],
        plan: QueryPlan,
        iteration: int,
    ) -> WorkerRun:
        items = case.patient.chart_items
        in_scope = [item for item in items if item.category in self.categories]
        selected = select_chart_items(items, self.categories, terms)
        anchors = [re.compile(pattern, re.IGNORECASE) for pattern in plan.anchor_patterns]
        candidates: list[EvidenceCandidate] = []
        for item, matched_terms, matched_field in selected:
            excerpt = item.detail if matched_field == "detail" else item.display
            assert excerpt is not None
            anchor_matched = any(anchor.search(excerpt) for anchor in anchors)
            confidence, cap_note = _score(plan, matched_terms, anchor_matched, excerpt)
            lowered = excerpt.lower()
            negated = any(cue in lowered for cue in ("denies", "denied", "no ", "without", "negative"))
            candidates.append(
                EvidenceCandidate(
                    candidate_id=_PROVISIONAL_ID,
                    criterion_id=criterion.criterion_id,
                    source_id=item.source_id,
                    source_type=SourceType.FHIR_RESOURCE,
                    excerpt=excerpt,
                    span=None,
                    fhir_path=matched_field,
                    confidence=confidence,
                    relevance_rationale=_rationale(
                        plan,
                        matched_terms,
                        anchor_matched,
                        f"chart item ({item.category})",
                        negated,
                        cap_note,
                    ),
                )
            )
        return WorkerRun(
            candidates=tuple(candidates),
            summary=WorkerRunSummary(
                worker=self.name,
                kind=self.kind,
                iteration=iteration,
                sources_total=len(in_scope),
                sources_considered=len(selected),
                candidates_found=len(candidates),
                outcome=(
                    WorkerOutcome.CANDIDATES_FOUND
                    if candidates
                    else WorkerOutcome.NO_RESULT_FOUND
                ),
                note=None if candidates else NO_RESULT_NOTE,
            ),
        )


class ConditionsWorker(ChartItemWorker):
    def __init__(self) -> None:
        super().__init__("conditions", ("condition",))


class MedicationsWorker(ChartItemWorker):
    def __init__(self) -> None:
        super().__init__("medications", ("medication",))


class ProceduresReferralsWorker(ChartItemWorker):
    def __init__(self) -> None:
        super().__init__("procedures_referrals", ("procedure", "referral"))


class ServiceRequestsWorker(ChartItemWorker):
    def __init__(self) -> None:
        super().__init__("service_requests", ("service_request",))


class ObservationsDiagnosticsWorker(ChartItemWorker):
    """Observations and DiagnosticReport-style items (chart category 'other')."""

    def __init__(self) -> None:
        super().__init__("observations_diagnostics", ("observation", "other"))


def default_workers(
    encounter_history_sources: Sequence[EvidenceSource] = (),
) -> tuple[RetrievalWorker, ...]:
    """The full focused-worker fleet, one worker per source family."""
    return (
        EncounterNoteWorker(),
        TranscriptWorker(),
        ConditionsWorker(),
        MedicationsWorker(),
        ProceduresReferralsWorker(),
        ServiceRequestsWorker(),
        ObservationsDiagnosticsWorker(),
        ClarificationsWorker(),
        EncounterHistoryWorker(encounter_history_sources),
    )
