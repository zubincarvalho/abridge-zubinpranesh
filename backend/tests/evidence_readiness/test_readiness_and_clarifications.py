"""Readiness calculator and clarification-service tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.contracts import (
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    PolicyCriterion,
)
from app.services.clarifications.service import ClarificationService
from app.services.evidence.mapper import DeterministicEvidenceMapper
from app.services.readiness import calculator
from app.services.readiness.detector import DeterministicGapDetector
from tests.evidence_readiness.conftest import make_candidate

FIXED_TIME = datetime(2026, 7, 18, 16, 0, 0, tzinfo=timezone.utc)

CLINICIAN_ANSWER = (
    "Yes. The patient completed 8 weeks of physical therapy alongside "
    "scheduled naproxen and a home-exercise program, without sufficient "
    "improvement in pain or function."
)


def _assessment(cid: str, status: CriterionStatus, risk: DenialRisk) -> CriterionAssessment:
    return CriterionAssessment(
        criterion_id=cid, status=status, denial_risk=risk, rationale="test"
    )


def _demo_assessments(sources, criteria_by_id, detector):
    """Assess all seven criteria over fixture-derived evidence."""
    mapper = DeterministicEvidenceMapper(sources)
    excerpts = {
        "LM-1": [("note-001", "Suspected lumbar radiculopathy (M54.16)")],
        "LM-2": [("note-001", "ongoing for approximately 8 weeks")],
        "LM-3": [
            ("fhir-ref-pt-001", "Referral to physical therapy"),
            ("fhir-med-001", "Naproxen 500 mg twice daily (NSAID)"),
        ],
        "LM-4": [("note-001", "Straight-leg raise is positive on the left at 40 degrees")],
        "LM-5": [
            (
                "note-001",
                "She denies recent trauma, fever, unexplained weight loss, saddle "
                "anesthesia, and bowel or bladder dysfunction. No history of cancer.",
            )
        ],
        "LM-6": [("note-001", "difficulty sitting through a full workday and interrupted sleep due to pain")],
        "LM-7": [
            (
                "note-001",
                "MRI lumbar spine without contrast ordered to evaluate for nerve "
                "root compression and to assess candidacy for epidural steroid "
                "injection or surgical referral if conservative measures fail",
            )
        ],
    }
    assessments = []
    evidence_by_criterion = {}
    for cid, pairs in excerpts.items():
        criterion = criteria_by_id[cid]
        candidates = [
            make_candidate(cid, sources[sid], text, candidate_id=f"cand-{cid}-{i}")
            for i, (sid, text) in enumerate(pairs)
        ]
        evidence = mapper.map_evidence(criterion, candidates)
        evidence_by_criterion[cid] = evidence
        assessments.append(detector.assess(criterion, evidence, []))
    return assessments, evidence_by_criterion


def test_readiness_is_deterministic(sources):
    detector = DeterministicGapDetector(sources)
    assessments = [
        _assessment("LM-1", CriterionStatus.MET, DenialRisk.LOW),
        _assessment("LM-2", CriterionStatus.WEAK, DenialRisk.MEDIUM),
        _assessment("LM-3", CriterionStatus.MISSING, DenialRisk.HIGH),
    ]
    first = detector.compute_readiness(assessments, "initial")
    second = detector.compute_readiness(assessments, "initial")
    assert first.score == second.score
    assert first.criteria_met == second.criteria_met == 1


def test_readiness_matches_contract_formula():
    """score = round(100 * (met + 0.5*weak) / (total - not_applicable))"""
    assessments = (
        [_assessment(f"LM-{i}", CriterionStatus.MET, DenialRisk.LOW) for i in range(1, 6)]
        + [_assessment("LM-6", CriterionStatus.WEAK, DenialRisk.MEDIUM)]
        + [_assessment("LM-7", CriterionStatus.MISSING, DenialRisk.HIGH)]
    )
    summary = calculator.compute_readiness(assessments, "initial")
    assert summary.score == round(100 * (5 + 0.5 * 1) / 7) == 79
    assert summary.criteria_met == 5
    assert summary.criteria_weak == 1
    assert summary.criteria_missing == 1
    assert summary.criteria_conflicting == 0
    assert summary.criteria_not_applicable == 0
    assert summary.overall_denial_risk == DenialRisk.HIGH


def test_not_applicable_excluded_from_denominator():
    assessments = [
        _assessment("LM-1", CriterionStatus.MET, DenialRisk.LOW),
        _assessment("LM-8", CriterionStatus.NOT_APPLICABLE, DenialRisk.LOW),
    ]
    summary = calculator.compute_readiness(assessments, "initial")
    assert summary.score == 100
    assert summary.criteria_not_applicable == 1


def test_required_criteria_weigh_more_than_optional():
    """A missing required criterion hurts more than a missing optional one."""
    required = PolicyCriterion(
        criterion_id="R-1", policy_id="P", label="req", requirement="r", category="duration"
    )
    optional = PolicyCriterion(
        criterion_id="O-1",
        policy_id="P",
        label="opt",
        requirement="o",
        category="rationale",
        applicability_note="Optional supporting documentation.",
    )
    met_required_missing_optional = [
        _assessment("R-1", CriterionStatus.MET, DenialRisk.LOW),
        _assessment("O-1", CriterionStatus.MISSING, DenialRisk.MEDIUM),
    ]
    met_optional_missing_required = [
        _assessment("R-1", CriterionStatus.MISSING, DenialRisk.HIGH),
        _assessment("O-1", CriterionStatus.MET, DenialRisk.LOW),
    ]
    criteria = [required, optional]
    assert calculator.compute_score(
        met_required_missing_optional, criteria
    ) > calculator.compute_score(met_optional_missing_required, criteria)


def test_unresolved_required_gap_count():
    required = PolicyCriterion(
        criterion_id="R-1", policy_id="P", label="req", requirement="r", category="duration"
    )
    optional = PolicyCriterion(
        criterion_id="O-1",
        policy_id="P",
        label="opt",
        requirement="o",
        category="rationale",
        applicability_note="Optional supporting documentation.",
    )
    assessments = [
        _assessment("R-1", CriterionStatus.MISSING, DenialRisk.HIGH),
        _assessment("O-1", CriterionStatus.WEAK, DenialRisk.MEDIUM),
    ]
    assert calculator.unresolved_required_gaps(assessments, [required, optional]) == 1
    assert calculator.unresolved_required_gaps(assessments) == 2


def test_no_approval_prediction_in_outputs(sources, criteria, criteria_by_id):
    """The score is Documentation Readiness — never approval probability."""
    assert calculator.SCORE_NAME == "Documentation Readiness"
    detector = DeterministicGapDetector(sources)
    assessments, _ = _demo_assessments(sources, criteria_by_id, detector)
    summary = detector.compute_readiness(assessments, "initial")
    forbidden = ("approval", "approve", "guarantee", "probability of payment")
    for text in (
        summary.label,
        *(a.rationale for a in assessments),
    ):
        lowered = text.lower()
        assert not any(term in lowered for term in forbidden)
    # The contract itself documents the boundary.
    assert "NOT a prediction" in type(summary).__doc__


def test_clarification_changes_lm3_to_met(sources, criteria, criteria_by_id):
    """A clinician attestation of completed+failed therapy closes the LM-3 gap."""
    detector = DeterministicGapDetector(sources)
    assessments, evidence_by_criterion = _demo_assessments(sources, criteria_by_id, detector)
    lm3_before = next(a for a in assessments if a.criterion_id == "LM-3")
    assert lm3_before.status in (CriterionStatus.WEAK, CriterionStatus.MISSING)

    questions = detector.generate_clarifications(assessments, criteria)
    lm3_question = next(q for q in questions if "LM-3" in q.criterion_ids)

    service = ClarificationService(sources=dict(sources))
    result = service.apply_clarification(
        question=lm3_question,
        response_text=CLINICIAN_ANSWER,
        author="Dr. Alex Kim",
        criteria=criteria,
        assessments=assessments,
        evidence_by_criterion=evidence_by_criterion,
        previous_readiness=detector.compute_readiness(assessments, "initial"),
        recorded_at=FIXED_TIME,
    )
    lm3_after = next(a for a in result.updated_assessments if a.criterion_id == "LM-3")
    assert lm3_after.status == CriterionStatus.MET
    # The clarification is cited evidence on the re-assessed criterion.
    assert any(
        item.source_id == result.record.clarification.clarification_id
        for item in lm3_after.evidence
    )
    assert result.updated_question.status == "answered"


def test_before_and_after_scores_preserved(sources, criteria, criteria_by_id):
    """Prior assessments and readiness snapshot survive re-analysis unchanged."""
    detector = DeterministicGapDetector(sources)
    assessments, evidence_by_criterion = _demo_assessments(sources, criteria_by_id, detector)
    before = detector.compute_readiness(assessments, "initial")
    questions = detector.generate_clarifications(assessments, criteria)
    lm3_question = next(q for q in questions if "LM-3" in q.criterion_ids)

    service = ClarificationService(sources=dict(sources))
    result = service.apply_clarification(
        question=lm3_question,
        response_text=CLINICIAN_ANSWER,
        author="Dr. Alex Kim",
        criteria=criteria,
        assessments=assessments,
        evidence_by_criterion=evidence_by_criterion,
        previous_readiness=before,
        recorded_at=FIXED_TIME,
    )
    assert result.previous_readiness == before
    assert result.previous_assessments == assessments
    assert result.updated_readiness.label == "post_clarification"
    assert result.updated_readiness.score > before.score
    lm3_before = next(a for a in result.previous_assessments if a.criterion_id == "LM-3")
    assert lm3_before.status in (CriterionStatus.WEAK, CriterionStatus.MISSING)


def test_clarification_recorded_verbatim_with_provenance(sources, criteria, criteria_by_id):
    """The clinician's statement is never rewritten; author+timestamp attach."""
    detector = DeterministicGapDetector(sources)
    assessments, _ = _demo_assessments(sources, criteria_by_id, detector)
    questions = detector.generate_clarifications(assessments, criteria)
    lm3_question = next(q for q in questions if "LM-3" in q.criterion_ids)

    text = "  Pt completed 6+ wks PT & NSAIDs — no sufficient improvement!!  "
    service = ClarificationService(sources=dict(sources))
    record = service.record_clarification(
        lm3_question, text, author="Dr. Alex Kim", recorded_at=FIXED_TIME
    )
    assert record.clarification.response == text  # exact, untrimmed, unrewritten
    assert record.source.content == text
    assert record.evidence_item.excerpt == text
    assert record.clarification.recorded_at == FIXED_TIME
    assert "Dr. Alex Kim" in record.source.label
    assert record.source.source_type.value == "clinician_clarification"
    assert record.source.source_id == record.clarification.clarification_id


def test_empty_clarification_rejected(sources, criteria, criteria_by_id):
    detector = DeterministicGapDetector(sources)
    assessments, _ = _demo_assessments(sources, criteria_by_id, detector)
    questions = detector.generate_clarifications(assessments, criteria)
    service = ClarificationService(sources=dict(sources))
    with pytest.raises(ValueError):
        service.record_clarification(questions[0], "   ", author="Dr. Alex Kim")
