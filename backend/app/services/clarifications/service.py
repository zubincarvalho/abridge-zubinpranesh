"""Clinician Clarification Service (Agent D).

Records a clinician's answer to a clarification question and re-runs the
relevant assessment logic. Hard rules:

- The clinician's text is recorded VERBATIM — never rewritten, trimmed of
  meaning, normalized, or paraphrased (docs/SAFETY_AND_HUMAN_REVIEW.md,
  human checkpoint 1).
- Every clarification carries provenance: author and timestamp, and becomes
  a citable evidence source (source_type=clinician_clarification,
  source_id = the clarification_id).
- Prior assessments and readiness snapshots are preserved unchanged so the
  frontend can render the before-and-after comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.contracts import (
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    EvidenceConfidence,
    EvidenceItem,
    EvidenceSource,
    PolicyCriterion,
    ReadinessSummary,
    SourceType,
    TextSpan,
)
from app.services.readiness import calculator, rubrics


@dataclass(frozen=True)
class ClarificationRecord:
    """One recorded clarification with its provenance and evidence source."""

    clarification: ClinicianClarification
    author: str
    source: EvidenceSource
    evidence_item: EvidenceItem


@dataclass(frozen=True)
class ReassessmentResult:
    """Outcome of recording a clarification and re-running assessment logic.

    ``previous_assessments`` and ``previous_readiness`` are the untouched
    inputs; ``updated_assessments`` contains a new object per re-assessed
    criterion. Nothing prior is mutated.
    """

    record: ClarificationRecord
    previous_assessments: list[CriterionAssessment]
    updated_assessments: list[CriterionAssessment]
    previous_readiness: ReadinessSummary | None
    updated_readiness: ReadinessSummary
    updated_question: ClarificationQuestion


@dataclass
class ClarificationService:
    """Accepts clinician answers verbatim and re-runs relevant assessments."""

    sources: dict[str, EvidenceSource] = field(default_factory=dict)
    _counter: int = 0

    def record_clarification(
        self,
        question: ClarificationQuestion,
        response_text: str,
        author: str,
        recorded_at: datetime | None = None,
    ) -> ClarificationRecord:
        """Record the clinician's exact text with author and timestamp."""
        if not response_text.strip():
            raise ValueError("clarification response must contain text")
        self._counter += 1
        clarification_id = f"clar-{self._counter:03d}"
        timestamp = recorded_at or datetime.now(timezone.utc)
        clarification = ClinicianClarification(
            clarification_id=clarification_id,
            question_id=question.question_id,
            response=response_text,  # verbatim — never rewritten
            recorded_at=timestamp,
        )
        source = EvidenceSource(
            source_id=clarification_id,
            source_type=SourceType.CLINICIAN_CLARIFICATION,
            label=f"Clinician clarification by {author} at {timestamp.isoformat()}",
            content=response_text,
        )
        evidence_item = EvidenceItem(
            evidence_id=f"ev-{clarification_id}",
            source_id=clarification_id,
            source_type=SourceType.CLINICIAN_CLARIFICATION,
            excerpt=response_text,
            span=TextSpan(start=0, end=len(response_text)),
            confidence=EvidenceConfidence.HIGH,
            note=f"Clinician-attested statement recorded verbatim; author: {author}.",
        )
        self.sources[clarification_id] = source
        return ClarificationRecord(
            clarification=clarification,
            author=author,
            source=source,
            evidence_item=evidence_item,
        )

    def apply_clarification(
        self,
        question: ClarificationQuestion,
        response_text: str,
        author: str,
        criteria: list[PolicyCriterion],
        assessments: list[CriterionAssessment],
        evidence_by_criterion: dict[str, list[EvidenceItem]],
        previous_readiness: ReadinessSummary | None = None,
        recorded_at: datetime | None = None,
        readiness_label: str = "post_clarification",
    ) -> ReassessmentResult:
        """Record the answer, re-assess the question's criteria, re-score.

        Only criteria named in ``question.criterion_ids`` are re-assessed;
        every other assessment object is carried through untouched. The
        supplied ``assessments`` and ``previous_readiness`` are returned
        as-is for the before-and-after display.
        """
        record = self.record_clarification(question, response_text, author, recorded_at)
        criteria_by_id = {c.criterion_id: c for c in criteria}

        updated: list[CriterionAssessment] = []
        for assessment in assessments:
            if assessment.criterion_id not in question.criterion_ids:
                updated.append(assessment)
                continue
            criterion = criteria_by_id[assessment.criterion_id]
            evidence = list(evidence_by_criterion.get(assessment.criterion_id, []))
            evidence.append(record.evidence_item)
            reassessed = rubrics.assess_criterion(
                criterion,
                evidence,
                [record.clarification],
                self.sources,
            )
            updated.append(reassessed)

        updated_readiness = calculator.compute_readiness(
            updated, readiness_label, criteria
        )
        return ReassessmentResult(
            record=record,
            previous_assessments=list(assessments),
            updated_assessments=updated,
            previous_readiness=previous_readiness,
            updated_readiness=updated_readiness,
            updated_question=question.model_copy(update={"status": "answered"}),
        )
