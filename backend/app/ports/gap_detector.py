"""Gap detector port: criterion classification, clarifications, readiness.

Hard rules implementations must enforce (see docs/SAFETY_AND_HUMAN_REVIEW.md):
- A referral is never proof of completed therapy.
- A prescription is never proof of treatment failure.
- Either may support at most WEAK for a completed-therapy criterion.
- Classification rationale must cite only the provided evidence.
"""

from typing import Protocol

from app.contracts import (
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    EvidenceItem,
    PolicyCriterion,
    ReadinessSummary,
)


class GapDetector(Protocol):
    def assess(
        self,
        criterion: PolicyCriterion,
        evidence: list[EvidenceItem],
        clarifications: list[ClinicianClarification],
    ) -> CriterionAssessment:
        """Classify one criterion as met/weak/missing/conflicting/not_applicable."""
        ...

    def generate_clarifications(
        self, assessments: list[CriterionAssessment], criteria: list[PolicyCriterion]
    ) -> list[ClarificationQuestion]:
        """Produce precise point-of-capture questions for weak/missing criteria."""
        ...

    def compute_readiness(
        self, assessments: list[CriterionAssessment], label: str
    ) -> ReadinessSummary:
        """Deterministically score documentation readiness (no LLM call)."""
        ...
