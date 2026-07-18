"""Criterion assessment, clarification, and readiness contracts.

A CriterionAssessment classifies one policy criterion against the cited
evidence. Missing or weak criteria produce ClarificationQuestion records;
clinician answers arrive as ClinicianClarification and trigger re-analysis.
ReadinessSummary snapshots power the before/after readiness scores.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field

from app.contracts._base import ContractModel
from app.contracts.evidence import EvidenceItem


class CriterionStatus(str, Enum):
    MET = "met"
    WEAK = "weak"
    MISSING = "missing"
    CONFLICTING = "conflicting"
    NOT_APPLICABLE = "not_applicable"


class DenialRisk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CriterionAssessment(ContractModel):
    """Classification of one criterion with exact cited evidence.

    ``rationale`` must be grounded in the cited evidence only. A referral or
    prescription can support at most WEAK for a completed-therapy criterion —
    never MET (see docs/SAFETY_AND_HUMAN_REVIEW.md).
    """

    criterion_id: str
    status: CriterionStatus
    denial_risk: DenialRisk
    rationale: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    clarification_question_id: str | None = None


class ClarificationQuestion(ContractModel):
    """A precise point-of-capture question the clinician can answer in one line."""

    question_id: str
    criterion_ids: list[str]
    question: str
    why_needed: str = Field(description="Which documentation gap this closes, in plain language")
    suggested_action: str | None = Field(
        default=None, description="Optional one-line suggested fix shown in the UI"
    )
    status: Literal["open", "answered"] = "open"


class ClinicianClarification(ContractModel):
    """A clinician's answer to a clarification question. Recorded verbatim."""

    clarification_id: str
    question_id: str
    response: str
    recorded_at: datetime


class ReadinessSummary(ContractModel):
    """A point-in-time documentation-readiness snapshot (0-100).

    Readiness measures documentation completeness against the payer policy.
    It is NOT a prediction or guarantee of payer approval.
    """

    label: str = Field(description="Snapshot label, e.g. 'initial' or 'post_clarification'")
    score: int = Field(ge=0, le=100)
    criteria_met: int = Field(ge=0)
    criteria_weak: int = Field(ge=0)
    criteria_missing: int = Field(ge=0)
    criteria_conflicting: int = Field(ge=0)
    criteria_not_applicable: int = Field(ge=0)
    overall_denial_risk: DenialRisk
    computed_at: datetime
