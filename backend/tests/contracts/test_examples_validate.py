"""Every JSON example in contracts/examples/ must validate against its contract."""

import pytest

from app.contracts import (
    ApiError,
    AuthLensCase,
    CaseStatus,
    ClarificationSubmission,
    CriterionStatus,
    EvidenceSourceResponse,
)
from tests.contracts.conftest import EXAMPLES_DIR, load_example

EXAMPLE_MODELS = {
    "demo_case.json": AuthLensCase,
    "case_state_initial.json": AuthLensCase,
    "case_state_awaiting_clarification.json": AuthLensCase,
    "case_state_ready_for_review.json": AuthLensCase,
    "clarification_request.json": ClarificationSubmission,
    "evidence_source_response.json": EvidenceSourceResponse,
    "error_response.json": ApiError,
}


@pytest.mark.parametrize("filename", sorted(EXAMPLE_MODELS))
def test_example_validates(filename):
    model = EXAMPLE_MODELS[filename]
    model.model_validate(load_example(filename))


def test_no_unmapped_example_files():
    on_disk = {p.name for p in EXAMPLES_DIR.glob("*.json")}
    assert on_disk == set(EXAMPLE_MODELS), "every example file must have a contract mapping"


def test_awaiting_state_has_demo_gap():
    case = AuthLensCase.model_validate(load_example("case_state_awaiting_clarification.json"))
    assert case.status == CaseStatus.AWAITING_CLARIFICATION
    lm3 = next(a for a in case.assessments if a.criterion_id == "LM-3")
    assert lm3.status == CriterionStatus.MISSING
    assert case.clarification_questions, "the demo gap must produce a clarification question"
    q = case.clarification_questions[0]
    assert "six weeks" in q.question
    assert case.readiness_history, "initial readiness snapshot required"


def test_ready_state_is_complete_and_improved():
    case = AuthLensCase.model_validate(load_example("case_state_ready_for_review.json"))
    assert case.status == CaseStatus.READY_FOR_REVIEW
    lm3 = next(a for a in case.assessments if a.criterion_id == "LM-3")
    assert lm3.status == CriterionStatus.MET
    assert len(case.readiness_history) >= 2
    assert case.readiness_history[-1].score > case.readiness_history[0].score
    assert case.packet is not None and case.packet.status.value == "verified"
    assert case.verification is not None and case.verification.passed
    assert case.form_draft is not None
    assert case.form_draft.packet_id == case.packet.packet_id
    # unrelated PHI excluded
    excluded = [d for d in case.disclosure_decisions if d.decision.value == "exclude"]
    assert excluded, "unrelated chart content must carry an explicit exclude decision"


def test_evidence_spans_are_verbatim():
    """Every note/transcript evidence span must quote its source exactly."""
    case = AuthLensCase.model_validate(load_example("case_state_ready_for_review.json"))
    sources = {
        case.encounter_note.source_id: case.encounter_note.text,
        case.encounter_transcript.source_id: case.encounter_transcript.text,
    }
    for clar in case.clarifications:
        sources[clar.clarification_id] = clar.response
    checked = 0
    for assessment in case.assessments:
        for item in assessment.evidence:
            if item.source_id in sources and item.span is not None:
                body = sources[item.source_id]
                assert body[item.span.start : item.span.end] == item.excerpt
                checked += 1
    assert checked > 0
