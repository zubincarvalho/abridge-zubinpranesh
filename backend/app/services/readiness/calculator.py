"""Deterministic Documentation Readiness calculator. No LLM calls.

The score is labeled **Documentation Readiness**: it measures documentation
completeness against the payer policy. It is never a prediction, estimate,
or guarantee of payer approval (docs/SAFETY_AND_HUMAN_REVIEW.md rule 3).

Base formula (docs/DATA_CONTRACTS.md):

    score = round(100 * (met + 0.5 * weak) / (total - not_applicable))

Weighting: required criteria count fully; optional criteria (those whose
``applicability_note`` marks them optional) count at half weight, so a
required gap always moves the score more than an optional one. When no
criteria metadata is supplied every criterion is treated as required and the
formula reduces exactly to the base formula above.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone

from app.contracts import (
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    PolicyCriterion,
    ReadinessSummary,
)

SCORE_NAME = "Documentation Readiness"

REQUIRED_WEIGHT = 1.0
OPTIONAL_WEIGHT = 0.5

_STATUS_CREDIT = {
    CriterionStatus.MET: 1.0,
    CriterionStatus.WEAK: 0.5,
    CriterionStatus.MISSING: 0.0,
    CriterionStatus.CONFLICTING: 0.0,
}

_RISK_ORDER = {DenialRisk.LOW: 0, DenialRisk.MEDIUM: 1, DenialRisk.HIGH: 2}

_OPTIONAL_MARKERS = ("optional", "not required", "if available")

_UNRESOLVED_STATUSES = (
    CriterionStatus.WEAK,
    CriterionStatus.MISSING,
    CriterionStatus.CONFLICTING,
)


def is_optional(criterion: PolicyCriterion) -> bool:
    note = (criterion.applicability_note or "").lower()
    return any(marker in note for marker in _OPTIONAL_MARKERS)


def criterion_weights(
    assessments: Sequence[CriterionAssessment],
    criteria: Sequence[PolicyCriterion] | None,
) -> dict[str, float]:
    """Weight per criterion_id; required=1.0, optional=0.5, unknown=required."""
    optional_ids = {c.criterion_id for c in criteria or () if is_optional(c)}
    return {
        a.criterion_id: OPTIONAL_WEIGHT if a.criterion_id in optional_ids else REQUIRED_WEIGHT
        for a in assessments
    }


def status_counts(assessments: Sequence[CriterionAssessment]) -> dict[CriterionStatus, int]:
    counts = {status: 0 for status in CriterionStatus}
    for assessment in assessments:
        counts[assessment.status] += 1
    return counts


def unresolved_required_gaps(
    assessments: Sequence[CriterionAssessment],
    criteria: Sequence[PolicyCriterion] | None = None,
) -> int:
    """Required criteria still weak, missing, or conflicting."""
    optional_ids = {c.criterion_id for c in criteria or () if is_optional(c)}
    return sum(
        1
        for a in assessments
        if a.status in _UNRESOLVED_STATUSES and a.criterion_id not in optional_ids
    )


def compute_score(
    assessments: Sequence[CriterionAssessment],
    criteria: Sequence[PolicyCriterion] | None = None,
) -> int:
    """Weighted Documentation Readiness score, 0-100, deterministic."""
    weights = criterion_weights(assessments, criteria)
    denominator = sum(
        weights[a.criterion_id]
        for a in assessments
        if a.status != CriterionStatus.NOT_APPLICABLE
    )
    if denominator == 0:
        return 0
    numerator = sum(
        weights[a.criterion_id] * _STATUS_CREDIT[a.status]
        for a in assessments
        if a.status != CriterionStatus.NOT_APPLICABLE
    )
    return round(100 * numerator / denominator)


def overall_denial_risk(assessments: Sequence[CriterionAssessment]) -> DenialRisk:
    """Maximum denial risk across applicable criteria (documentation risk only)."""
    applicable = [a for a in assessments if a.status != CriterionStatus.NOT_APPLICABLE]
    if not applicable:
        return DenialRisk.LOW
    return max((a.denial_risk for a in applicable), key=_RISK_ORDER.__getitem__)


def compute_readiness(
    assessments: Sequence[CriterionAssessment],
    label: str,
    criteria: Sequence[PolicyCriterion] | None = None,
    computed_at: datetime | None = None,
) -> ReadinessSummary:
    """Snapshot Documentation Readiness. Same inputs always give the same score.

    The result measures documentation completeness only — it is not payer
    approval probability and must never be presented as one.
    """
    counts = status_counts(assessments)
    return ReadinessSummary(
        label=label,
        score=compute_score(assessments, criteria),
        criteria_met=counts[CriterionStatus.MET],
        criteria_weak=counts[CriterionStatus.WEAK],
        criteria_missing=counts[CriterionStatus.MISSING],
        criteria_conflicting=counts[CriterionStatus.CONFLICTING],
        criteria_not_applicable=counts[CriterionStatus.NOT_APPLICABLE],
        overall_denial_risk=overall_denial_risk(assessments),
        computed_at=computed_at or datetime.now(timezone.utc),
    )
