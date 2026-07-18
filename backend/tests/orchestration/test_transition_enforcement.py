"""State-machine enforcement: wrong-status operations fail without mutation."""

import pytest

from app.contracts import CaseStatus, ClarificationSubmission
from app.orchestration import (
    PacketNotVerifiedError,
    QuestionAlreadyAnsweredError,
    QuestionNotFoundError,
)
from app.services.cases import CaseNotFoundError, InvalidStateTransitionError

from tests.orchestration.conftest import CLARIFICATION_ANSWER


def _assert_unchanged(repository, case_id, snapshot):
    assert repository.get(case_id).model_dump() == snapshot.model_dump()


def test_unknown_case_id_raises_case_not_found(orchestrator):
    with pytest.raises(CaseNotFoundError) as excinfo:
        orchestrator.start_analysis("case-does-not-exist")
    assert excinfo.value.error_code == "case_not_found"


def test_operations_invalid_before_run(orchestrator, case, repository):
    snapshot = repository.get(case.case_id)
    for operation in (
        orchestrator.generate_packet,
        orchestrator.verify_packet,
        lambda case_id: orchestrator.submit_clarification(
            case_id, ClarificationSubmission(question_id="q-LM-3", response="x")
        ),
    ):
        with pytest.raises(InvalidStateTransitionError):
            operation(case.case_id)
        _assert_unchanged(repository, case.case_id, snapshot)


def test_form_draft_before_run_is_invalid_state(orchestrator, case):
    with pytest.raises(InvalidStateTransitionError):
        orchestrator.draft_form(case.case_id)


def test_verify_requires_packet_drafted(orchestrator, case, repository):
    orchestrator.start_analysis(case.case_id)
    snapshot = repository.get(case.case_id)
    with pytest.raises(InvalidStateTransitionError):
        orchestrator.verify_packet(case.case_id)
    _assert_unchanged(repository, case.case_id, snapshot)


def test_form_draft_requires_verification(orchestrator, case, repository):
    orchestrator.start_analysis(case.case_id)
    orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )
    orchestrator.generate_packet(case.case_id)
    snapshot = repository.get(case.case_id)

    with pytest.raises(PacketNotVerifiedError) as excinfo:
        orchestrator.draft_form(case.case_id)

    assert excinfo.value.error_code == "packet_not_verified"
    _assert_unchanged(repository, case.case_id, snapshot)


def test_unknown_question_raises_question_not_found(orchestrator, case):
    orchestrator.start_analysis(case.case_id)
    with pytest.raises(QuestionNotFoundError) as excinfo:
        orchestrator.submit_clarification(
            case.case_id,
            ClarificationSubmission(question_id="q-nope", response="answer"),
        )
    assert excinfo.value.error_code == "question_not_found"


def test_reanswering_a_question_is_rejected(orchestrator, case, repository):
    orchestrator.start_analysis(case.case_id)
    orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )
    snapshot = repository.get(case.case_id)

    with pytest.raises(QuestionAlreadyAnsweredError) as excinfo:
        orchestrator.submit_clarification(
            case.case_id,
            ClarificationSubmission(question_id="q-LM-3", response="different answer"),
        )

    assert excinfo.value.error_code == "question_already_answered"
    _assert_unchanged(repository, case.case_id, snapshot)


def test_ready_for_review_is_terminal(orchestrator, case, repository):
    orchestrator.start_analysis(case.case_id)
    orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )
    orchestrator.generate_packet(case.case_id)
    orchestrator.verify_packet(case.case_id)
    done = orchestrator.draft_form(case.case_id)
    assert done.status is CaseStatus.READY_FOR_REVIEW

    snapshot = repository.get(case.case_id)
    operations = [
        orchestrator.start_analysis,
        orchestrator.generate_packet,
        orchestrator.verify_packet,
        orchestrator.draft_form,
        lambda case_id: orchestrator.submit_clarification(
            case_id, ClarificationSubmission(question_id="q-LM-3", response="x")
        ),
    ]
    for operation in operations:
        with pytest.raises(InvalidStateTransitionError):
            operation(case.case_id)
        _assert_unchanged(repository, case.case_id, snapshot)


def test_repeated_form_draft_is_rejected(orchestrator, case):
    orchestrator.start_analysis(case.case_id)
    orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )
    orchestrator.generate_packet(case.case_id)
    orchestrator.verify_packet(case.case_id)
    orchestrator.draft_form(case.case_id)
    with pytest.raises(InvalidStateTransitionError):
        orchestrator.draft_form(case.case_id)


def test_no_submitted_state_and_no_submission_api(orchestrator):
    assert "submitted" not in {status.value for status in CaseStatus}
    submission_like = [
        name
        for name in dir(orchestrator)
        if "submit" in name.lower() and "clarification" not in name.lower()
    ]
    assert submission_like == [], "orchestrator must expose no submission API"
