"""GapDetector port implementation (deterministic).

Classification runs the category rubrics over cited evidence and verbatim
clinician clarifications; question generation and readiness scoring are
plain code. Hard rules (referral ≠ completion, prescription ≠ failure,
conflicts stay conflicting until reviewed) live in the rubrics.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts import (
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    EvidenceItem,
    EvidenceSource,
    PolicyCriterion,
    ReadinessSummary,
)
from app.services.readiness import calculator, questions, rubrics


class DeterministicGapDetector:
    """Code-only GapDetector. Same inputs always produce the same outputs."""

    def __init__(self, sources: Mapping[str, EvidenceSource] | None = None) -> None:
        self._sources = dict(sources or {})

    def assess(
        self,
        criterion: PolicyCriterion,
        evidence: list[EvidenceItem],
        clarifications: list[ClinicianClarification],
    ) -> CriterionAssessment:
        assessment = rubrics.assess_criterion(
            criterion, evidence, clarifications, self._sources
        )
        if questions.needs_question(assessment):
            assessment = assessment.model_copy(
                update={
                    "clarification_question_id": questions.question_id_for(
                        criterion.criterion_id
                    )
                }
            )
        return assessment

    def generate_clarifications(
        self, assessments: list[CriterionAssessment], criteria: list[PolicyCriterion]
    ) -> list[ClarificationQuestion]:
        return questions.generate_clarifications(assessments, criteria)

    def compute_readiness(
        self, assessments: list[CriterionAssessment], label: str
    ) -> ReadinessSummary:
        return calculator.compute_readiness(assessments, label)

    def compute_readiness_weighted(
        self,
        assessments: list[CriterionAssessment],
        label: str,
        criteria: list[PolicyCriterion],
    ) -> ReadinessSummary:
        """Readiness with required-vs-optional criterion weighting applied."""
        return calculator.compute_readiness(assessments, label, criteria)
