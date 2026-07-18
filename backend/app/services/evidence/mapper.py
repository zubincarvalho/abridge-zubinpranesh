"""Deterministic evidence mapper (EvidenceMapper port implementation).

Turns retrieval candidates into accepted, cited EvidenceItem records for one
criterion. Gatekeeping is pure code:

1. Unknown source, or an excerpt that is not verbatim in its source → reject.
2. No deterministic relevance signal for the criterion's category → reject.
3. Referral/prescription evidence on a completed-therapy criterion is capped
   at LOW confidence with an explicit limitation note — never proof of
   completion or failure.
4. Patient-reported statements are labeled and capped at MODERATE.

Source citations (source_id, span, fhir_path) are preserved unchanged;
excerpts are never edited.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts import (
    EvidenceCandidate,
    EvidenceConfidence,
    EvidenceItem,
    EvidenceSource,
    PolicyCriterion,
    SourceType,
)
from app.services.evidence import rules
from app.services.evidence.relevance import CATEGORY_KEYWORDS, has_relevance_signal
from app.services.evidence.verbatim import resolve_verbatim_span

_CONFIDENCE_ORDER = {
    EvidenceConfidence.LOW: 0,
    EvidenceConfidence.MODERATE: 1,
    EvidenceConfidence.HIGH: 2,
}

COMPLETED_THERAPY_CATEGORY = "conservative_therapy"


def criterion_key(criterion_id: str) -> str:
    """'LM-3' → 'lm3', matching the repo's id conventions."""
    return criterion_id.lower().replace("-", "")


def cap_confidence(
    confidence: EvidenceConfidence, ceiling: EvidenceConfidence
) -> EvidenceConfidence:
    if _CONFIDENCE_ORDER[confidence] > _CONFIDENCE_ORDER[ceiling]:
        return ceiling
    return confidence


def apply_safety_caps(
    item: EvidenceItem, criterion: PolicyCriterion, source_content: str | None
) -> EvidenceItem:
    """Cap confidence and attach limitation notes required by the hard rules."""
    updates: dict = {}
    if criterion.category == COMPLETED_THERAPY_CATEGORY:
        signals = rules.therapy_signals(item.excerpt)
        if signals.referral_or_prescription_only:
            updates["confidence"] = EvidenceConfidence.LOW
            if signals.referral:
                updates["note"] = rules.REFERRAL_LIMITATION_NOTE
            else:
                updates["note"] = rules.PRESCRIPTION_LIMITATION_NOTE
    if "note" not in updates and rules.is_patient_reported(
        item.excerpt, source_content, item.source_type
    ):
        updates["confidence"] = cap_confidence(item.confidence, EvidenceConfidence.MODERATE)
        updates["note"] = rules.PATIENT_REPORTED_NOTE
    return item.model_copy(update=updates) if updates else item


class DeterministicEvidenceMapper:
    """Code-only EvidenceMapper. No LLM call; usable in tests and demo mode."""

    def __init__(self, sources: Mapping[str, EvidenceSource]) -> None:
        self._sources = dict(sources)

    def map_evidence(
        self, criterion: PolicyCriterion, candidates: list[EvidenceCandidate]
    ) -> list[EvidenceItem]:
        accepted: list[EvidenceItem] = []
        seen: set[tuple[str, str]] = set()
        key = criterion_key(criterion.criterion_id)
        for candidate in candidates:
            if candidate.criterion_id != criterion.criterion_id:
                continue
            source = self._sources.get(candidate.source_id)
            if source is None:
                continue
            span = resolve_verbatim_span(source.content, candidate.excerpt, candidate.span)
            if span is None:
                continue
            if not has_relevance_signal(criterion.category, candidate.excerpt):
                continue
            dedupe = (candidate.source_id, candidate.excerpt)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            item = EvidenceItem(
                evidence_id=f"ev-{key}-{len(accepted) + 1:03d}",
                source_id=candidate.source_id,
                source_type=candidate.source_type,
                excerpt=candidate.excerpt,
                span=span if candidate.source_type != SourceType.FHIR_RESOURCE else candidate.span,
                fhir_path=candidate.fhir_path,
                confidence=candidate.confidence,
                note=None,
            )
            accepted.append(apply_safety_caps(item, criterion, source.content))
        return accepted


__all__ = [
    "CATEGORY_KEYWORDS",
    "COMPLETED_THERAPY_CATEGORY",
    "DeterministicEvidenceMapper",
    "apply_safety_caps",
    "cap_confidence",
    "criterion_key",
]
