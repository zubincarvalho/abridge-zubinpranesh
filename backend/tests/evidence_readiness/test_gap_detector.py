"""Gap Detector tests: safety classifications, gaps, conflicts, questions."""

from __future__ import annotations

from app.contracts import (
    CriterionStatus,
    EvidenceConfidence,
    EvidenceItem,
    PolicyCriterion,
    SourceType,
)
from app.services.evidence.mapper import DeterministicEvidenceMapper
from app.services.readiness.detector import DeterministicGapDetector
from app.services.readiness.questions import LM3_QUESTION
from tests.evidence_readiness.conftest import make_candidate


def _map(sources, criterion, candidates):
    return DeterministicEvidenceMapper(sources).map_evidence(criterion, candidates)


def _item(source_id, source_type, excerpt, evidence_id="ev-test-001"):
    return EvidenceItem(
        evidence_id=evidence_id,
        source_id=source_id,
        source_type=source_type,
        excerpt=excerpt,
        confidence=EvidenceConfidence.MODERATE,
    )


def test_pt_referral_insufficient_for_lm3(sources, criteria_by_id):
    """A PT referral never satisfies completed-and-failed conservative therapy."""
    detector = DeterministicGapDetector(sources)
    criterion = criteria_by_id["LM-3"]
    evidence = _map(
        sources,
        criterion,
        [make_candidate("LM-3", sources["fhir-ref-pt-001"], "Referral to physical therapy")],
    )
    assessment = detector.assess(criterion, evidence, [])
    assert assessment.status in (CriterionStatus.WEAK, CriterionStatus.MISSING)
    assert assessment.status != CriterionStatus.MET
    assert "referral" in assessment.rationale.lower()


def test_nsaid_prescription_insufficient_for_lm3(sources, criteria_by_id):
    """A prescription on the medication list is never proof of treatment failure."""
    detector = DeterministicGapDetector(sources)
    criterion = criteria_by_id["LM-3"]
    evidence = _map(
        sources,
        criterion,
        [make_candidate("LM-3", sources["fhir-med-001"], "Naproxen 500 mg twice daily (NSAID)")],
    )
    assessment = detector.assess(criterion, evidence, [])
    assert assessment.status in (CriterionStatus.WEAK, CriterionStatus.MISSING)
    assert assessment.status != CriterionStatus.MET


def test_lumbar_fixture_lm3_initially_weak_or_missing(sources, criteria_by_id):
    """The engineered demo gap: referral + NSAID together still fail LM-3."""
    detector = DeterministicGapDetector(sources)
    criterion = criteria_by_id["LM-3"]
    evidence = _map(
        sources,
        criterion,
        [
            make_candidate(
                "LM-3", sources["fhir-ref-pt-001"], "Referral to physical therapy",
                candidate_id="cand-ref",
            ),
            make_candidate(
                "LM-3", sources["fhir-med-001"], "Naproxen 500 mg twice daily (NSAID)",
                candidate_id="cand-med",
            ),
        ],
    )
    assessment = detector.assess(criterion, evidence, [])
    assert assessment.status in (CriterionStatus.WEAK, CriterionStatus.MISSING)


def test_completion_without_outcome_is_not_failure(sources, criteria_by_id):
    """Documented PT completion alone (no outcome) never satisfies LM-3."""
    detector = DeterministicGapDetector(sources)
    criterion = criteria_by_id["LM-3"]
    item = _item(
        "note-001",
        SourceType.ENCOUNTER_NOTE,
        "Patient completed eight weeks of physical therapy",
    )
    assessment = detector.assess(criterion, [item], [])
    assert assessment.status == CriterionStatus.WEAK
    assert assessment.status != CriterionStatus.MET


def test_missing_duration(sources, criteria_by_id):
    """No evidence bearing on duration → missing, never inferred."""
    detector = DeterministicGapDetector(sources)
    assessment = detector.assess(criteria_by_id["LM-2"], [], [])
    assert assessment.status == CriterionStatus.MISSING
    assert "missing" in assessment.rationale.lower()


def test_vague_duration_language_is_not_met(sources, criteria_by_id):
    """'Persistent pain' does not prove six weeks."""
    detector = DeterministicGapDetector(sources)
    item = _item("note-001", SourceType.ENCOUNTER_NOTE, "persistent low back pain")
    assessment = detector.assess(criteria_by_id["LM-2"], [item], [])
    assert assessment.status == CriterionStatus.WEAK


def test_conflicting_duration_stays_conflicting(sources, criteria_by_id):
    """Contradictory documented durations remain conflicting until reviewed."""
    detector = DeterministicGapDetector(sources)
    items = [
        _item("note-001", SourceType.ENCOUNTER_NOTE, "ongoing for approximately 8 weeks", "ev-a"),
        _item("transcript-001", SourceType.ENCOUNTER_TRANSCRIPT, "pain started two weeks ago", "ev-b"),
    ]
    assessment = detector.assess(criteria_by_id["LM-2"], items, [])
    assert assessment.status == CriterionStatus.CONFLICTING
    assert "conflict" in assessment.rationale.lower()


def test_diagnosis_code_is_not_exam_finding(sources, criteria_by_id):
    """An ICD code alone never satisfies the examination-findings criterion."""
    detector = DeterministicGapDetector(sources)
    item = _item(
        "note-001", SourceType.ENCOUNTER_NOTE, "Suspected lumbar radiculopathy (M54.16)"
    )
    assessment = detector.assess(criteria_by_id["LM-4"], item and [item], [])
    assert assessment.status == CriterionStatus.WEAK
    assert "diagnosis" in assessment.rationale.lower()


def test_absent_red_flag_documentation_is_not_negative_screen(sources, criteria_by_id):
    """Text that never documents a screen can't make red-flag screening met."""
    detector = DeterministicGapDetector(sources)
    item = _item("note-001", SourceType.ENCOUNTER_NOTE, "Return in 4 weeks or sooner if red-flag symptoms develop")
    assessment = detector.assess(criteria_by_id["LM-5"], [item], [])
    assert assessment.status == CriterionStatus.WEAK


def test_documented_negative_screen_is_met(sources, criteria_by_id):
    detector = DeterministicGapDetector(sources)
    item = _item(
        "note-001",
        SourceType.ENCOUNTER_NOTE,
        "She denies recent trauma, fever, unexplained weight loss, saddle "
        "anesthesia, and bowel or bladder dysfunction. No history of cancer.",
    )
    assessment = detector.assess(criteria_by_id["LM-5"], [item], [])
    assert assessment.status == CriterionStatus.MET


def test_not_applicable_conditional_criterion(sources):
    """A conditional criterion with no triggering evidence is not_applicable."""
    detector = DeterministicGapDetector(sources)
    conditional = PolicyCriterion(
        criterion_id="LM-8",
        policy_id="MHP-IMG-2201",
        label="Prior imaging comparison",
        requirement="If prior lumbar imaging exists, the record documents comparison.",
        category="rationale",
        applicability_note="Applies only if prior lumbar imaging exists.",
    )
    assessment = detector.assess(conditional, [], [])
    assert assessment.status == CriterionStatus.NOT_APPLICABLE


def test_lm3_clarification_question_wording_and_limits(sources, criteria, criteria_by_id):
    """The LM-3 gap yields exactly one question with the spec wording."""
    detector = DeterministicGapDetector(sources)
    criterion = criteria_by_id["LM-3"]
    evidence = _map(
        sources,
        criterion,
        [make_candidate("LM-3", sources["fhir-ref-pt-001"], "Referral to physical therapy")],
    )
    assessment = detector.assess(criterion, evidence, [])
    questions = detector.generate_clarifications([assessment], criteria)
    lm3_questions = [q for q in questions if "LM-3" in q.criterion_ids]
    assert len(lm3_questions) == 1
    assert lm3_questions[0].question == LM3_QUESTION
    assert lm3_questions[0].status == "open"


def test_at_most_one_question_per_gapped_criterion(sources, criteria, criteria_by_id):
    detector = DeterministicGapDetector(sources)
    assessments = [
        detector.assess(criteria_by_id["LM-2"], [], []),
        detector.assess(criteria_by_id["LM-3"], [], []),
    ]
    questions = detector.generate_clarifications(assessments, criteria)
    for cid in ("LM-2", "LM-3"):
        assert sum(1 for q in questions if cid in q.criterion_ids) == 1


def test_questions_never_recommend_treatment(sources, criteria, criteria_by_id):
    """Questions ask what was documented/done — never what should be done."""
    detector = DeterministicGapDetector(sources)
    assessments = [detector.assess(c, [], []) for c in criteria]
    questions = detector.generate_clarifications(assessments, criteria)
    assert questions
    forbidden = ("you should", "we recommend", "consider prescribing", "start the patient")
    for q in questions:
        lowered = q.question.lower()
        assert not any(phrase in lowered for phrase in forbidden)
