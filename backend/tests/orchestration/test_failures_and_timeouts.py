"""Failure, retry, gate, and timeout behavior — safety checks never skipped."""

import pytest

from app.contracts import (
    AgentStage,
    CaseStatus,
    ClarificationSubmission,
    EventStatus,
    PacketStatus,
)
from app.orchestration import (
    PacketNotVerifiedError,
    StageExecutionError,
    StageTimeoutError,
)

from tests.orchestration.conftest import CLARIFICATION_ANSWER, make_orchestrator
from tests.orchestration.fakes import (
    FakeCaseRepository,
    FakeEvidenceRetriever,
    FakePacketVerifier,
    GhostEvidencePacketGenerator,
    NonVerbatimMapper,
    SelfVerifyingPacketGenerator,
)
from tests.orchestration.conftest import build_case


def _run_to_awaiting(orchestrator, case_id, answer=True):
    orchestrator.start_analysis(case_id)
    if answer:
        orchestrator.submit_clarification(
            case_id,
            ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
        )


def test_verification_failure_blocks_form_then_regeneration_recovers():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    verifier = FakePacketVerifier(fail_times=1)
    orchestrator = make_orchestrator(repository, packet_verifier=verifier)

    _run_to_awaiting(orchestrator, case.case_id)
    orchestrator.generate_packet(case.case_id)

    failed = orchestrator.verify_packet(case.case_id)
    assert failed.status is CaseStatus.VERIFICATION_FAILED
    assert failed.verification is not None and not failed.verification.passed
    assert failed.verification.issues[0].severity.value == "blocking"
    assert failed.packet.status is PacketStatus.VERIFICATION_FAILED

    with pytest.raises(PacketNotVerifiedError):
        orchestrator.draft_form(case.case_id)

    # Regeneration is the only exit: new draft packet, verification cleared.
    redrafted = orchestrator.generate_packet(case.case_id)
    assert redrafted.status is CaseStatus.PACKET_DRAFTED
    assert redrafted.packet.packet_id != failed.packet.packet_id
    assert redrafted.verification is None

    verified = orchestrator.verify_packet(case.case_id)
    assert verified.status is CaseStatus.VERIFIED
    done = orchestrator.draft_form(case.case_id)
    assert done.status is CaseStatus.READY_FOR_REVIEW
    assert verifier.calls == 2  # verification ran again; never skipped


def test_verifier_timeout_does_not_bypass_verification():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    orchestrator = make_orchestrator(
        repository,
        packet_verifier=FakePacketVerifier(hang_seconds=2.0),
        stage_timeout_seconds=0.2,
    )
    _run_to_awaiting(orchestrator, case.case_id)
    orchestrator.generate_packet(case.case_id)

    with pytest.raises(StageTimeoutError):
        orchestrator.verify_packet(case.case_id)

    stored = repository.get(case.case_id)
    assert stored.status is CaseStatus.PACKET_DRAFTED  # rolled back, not verified
    assert stored.verification is None
    assert stored.packet.status is PacketStatus.DRAFT
    failed_events = [
        e
        for e in stored.events
        if e.stage is AgentStage.VERIFICATION and e.status is EventStatus.FAILED
    ]
    assert failed_events, "the timeout must be visible on the timeline"

    with pytest.raises(PacketNotVerifiedError):
        orchestrator.draft_form(case.case_id)


def test_stage_failure_rolls_back_and_retry_reruns_all_stages():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    # LM-1 retrieval fails more times than the per-run attempt bound (3).
    retriever = FakeEvidenceRetriever(fail_first_n_for={"LM-1": 3})
    orchestrator = make_orchestrator(repository, evidence_retriever=retriever)

    with pytest.raises(StageExecutionError):
        orchestrator.start_analysis(case.case_id)

    stored = repository.get(case.case_id)
    assert stored.status is CaseStatus.INTAKE_READY  # no partial transition
    assert stored.criteria == [] and stored.assessments == []
    assert any(e.status is EventStatus.FAILED for e in stored.events)

    # Retry runs the whole pipeline again (the flaky window has passed).
    result = orchestrator.start_analysis(case.case_id)
    assert result.status is CaseStatus.AWAITING_CLARIFICATION
    assert len(result.assessments) == 3


def test_retrieval_retries_are_bounded_and_recover_within_bound():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    retriever = FakeEvidenceRetriever(fail_first_n_for={"LM-2": 2})
    orchestrator = make_orchestrator(repository, evidence_retriever=retriever)

    result = orchestrator.start_analysis(case.case_id)

    assert result.status is CaseStatus.AWAITING_CLARIFICATION
    assert retriever.calls["LM-2"] == 3  # 2 failures + 1 success, within the bound
    assert retriever.calls["LM-1"] == 1


def test_non_verbatim_excerpt_fails_the_mapping_gate():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    orchestrator = make_orchestrator(repository, evidence_mapper=NonVerbatimMapper())

    with pytest.raises(StageExecutionError) as excinfo:
        orchestrator.start_analysis(case.case_id)

    assert "verbatim" in str(excinfo.value)
    assert repository.get(case.case_id).status is CaseStatus.INTAKE_READY


def test_generator_cannot_mark_its_own_packet_verified():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    orchestrator = make_orchestrator(
        repository, packet_generator=SelfVerifyingPacketGenerator()
    )
    _run_to_awaiting(orchestrator, case.case_id)

    with pytest.raises(StageExecutionError):
        orchestrator.generate_packet(case.case_id)

    stored = repository.get(case.case_id)
    assert stored.status is CaseStatus.AWAITING_CLARIFICATION
    assert stored.packet is None


def test_packet_citing_unknown_evidence_is_rejected():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    orchestrator = make_orchestrator(
        repository, packet_generator=GhostEvidencePacketGenerator()
    )
    _run_to_awaiting(orchestrator, case.case_id)

    with pytest.raises(StageExecutionError) as excinfo:
        orchestrator.generate_packet(case.case_id)

    assert "unknown evidence" in str(excinfo.value)
    assert repository.get(case.case_id).packet is None


def test_failed_clarification_rolls_back_answer_and_question_status():
    repository = FakeCaseRepository()
    case = repository.create(build_case())
    # Re-retrieval for LM-3 fails hard during the clarification re-run only:
    # LM-3 succeeds once (initial run), then fails 3 times (the re-run).
    retriever = FakeEvidenceRetriever()
    orchestrator = make_orchestrator(repository, evidence_retriever=retriever)
    orchestrator.start_analysis(case.case_id)
    retriever.fail_first_n_for["LM-3"] = retriever.calls.get("LM-3", 0) + 3

    with pytest.raises(StageExecutionError):
        orchestrator.submit_clarification(
            case.case_id,
            ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
        )

    stored = repository.get(case.case_id)
    assert stored.status is CaseStatus.AWAITING_CLARIFICATION
    assert stored.clarifications == []  # verbatim answer rolled back with the state
    question = next(q for q in stored.clarification_questions if q.question_id == "q-LM-3")
    assert question.status == "open"  # can be answered again after the failure

    # Retry succeeds and re-runs mapping and assessment (safety not skipped).
    result = orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )
    assert result.readiness_history[-1].score == 100
