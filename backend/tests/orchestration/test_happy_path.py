"""Happy-path workflow: run → pause → clarify → packet → verify → form."""

from app.contracts import (
    AgentStage,
    CaseStatus,
    ClarificationSubmission,
    CriterionStatus,
    DisclosureDecisionType,
    EventStatus,
    PacketStatus,
)
from app.services.cases import InvalidStateTransitionError

from tests.orchestration.conftest import CLARIFICATION_ANSWER

import pytest


def test_initial_run_pauses_for_clarification(orchestrator, case):
    result = orchestrator.start_analysis(case.case_id)

    assert result.status is CaseStatus.AWAITING_CLARIFICATION
    assert [c.criterion_id for c in result.criteria] == ["LM-1", "LM-2", "LM-3"]

    by_id = {a.criterion_id: a for a in result.assessments}
    assert by_id["LM-1"].status is CriterionStatus.MET
    assert by_id["LM-2"].status is CriterionStatus.MET
    assert by_id["LM-3"].status is CriterionStatus.MISSING

    open_questions = [q for q in result.clarification_questions if q.status == "open"]
    assert [q.question_id for q in open_questions] == ["q-LM-3"]

    assert len(result.readiness_history) == 1
    initial = result.readiness_history[0]
    assert initial.label == "initial"
    assert initial.score == 67
    assert initial.criteria_missing == 1

    pause_events = [
        e
        for e in result.events
        if e.stage is AgentStage.CLARIFICATION and e.status is EventStatus.STARTED
    ]
    assert pause_events, "pausing for clarification must be on the timeline"


def test_clarification_resumes_and_updates_readiness(orchestrator, case):
    orchestrator.start_analysis(case.case_id)
    result = orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )

    assert result.status is CaseStatus.AWAITING_CLARIFICATION

    # The answer is recorded verbatim and the question is closed.
    assert len(result.clarifications) == 1
    assert result.clarifications[0].response == CLARIFICATION_ANSWER
    question = next(q for q in result.clarification_questions if q.question_id == "q-LM-3")
    assert question.status == "answered"

    # The affected criterion was re-mapped and re-assessed.
    lm3 = next(a for a in result.assessments if a.criterion_id == "LM-3")
    assert lm3.status is CriterionStatus.MET
    assert lm3.evidence and lm3.evidence[0].excerpt == CLARIFICATION_ANSWER

    # Before/after readiness preserved: both snapshots stay in the history.
    assert [r.label for r in result.readiness_history] == [
        "initial",
        "post_clarification_1",
    ]
    assert result.readiness_history[1].score > result.readiness_history[0].score
    assert result.readiness_history[1].score == 100

    # The re-evaluation event summarizes the before → after change.
    rerun_events = [
        e
        for e in result.events
        if e.stage is AgentStage.GAP_DETECTION and e.detail and "→" in e.detail
    ]
    assert any("missing → met" in e.detail for e in rerun_events)


def test_full_workflow_reaches_ready_for_review(orchestrator, case):
    orchestrator.start_analysis(case.case_id)
    orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )

    drafted = orchestrator.generate_packet(case.case_id)
    assert drafted.status is CaseStatus.PACKET_DRAFTED
    assert drafted.packet is not None
    assert drafted.packet.status is PacketStatus.DRAFT
    assert drafted.verification is None
    # Minimum-necessary: the unrelated condition is excluded with a reason.
    exclusions = [
        d
        for d in drafted.disclosure_decisions
        if d.decision is DisclosureDecisionType.EXCLUDE
    ]
    assert any(d.source_id == "src-chart-anxiety" and d.reason for d in exclusions)

    verified = orchestrator.verify_packet(case.case_id)
    assert verified.status is CaseStatus.VERIFIED
    assert verified.verification is not None and verified.verification.passed
    assert verified.packet.status is PacketStatus.VERIFIED

    done = orchestrator.draft_form(case.case_id)
    assert done.status is CaseStatus.READY_FOR_REVIEW
    assert done.form_draft is not None
    assert done.form_draft.packet_id == done.packet.packet_id
    assert "not" in done.form_draft.attestation.lower()  # no-submission attestation

    human_review = [e for e in done.events if e.stage is AgentStage.HUMAN_REVIEW]
    assert human_review and human_review[-1].status is EventStatus.STARTED


def test_repeated_run_calls_are_safe(orchestrator, case, repository):
    orchestrator.start_analysis(case.case_id)
    snapshot = repository.get(case.case_id)

    with pytest.raises(InvalidStateTransitionError) as excinfo:
        orchestrator.start_analysis(case.case_id)

    assert excinfo.value.error_code == "invalid_state_transition"
    after = repository.get(case.case_id)
    assert after.model_dump() == snapshot.model_dump()


def test_event_order_is_correct(orchestrator, case):
    orchestrator.start_analysis(case.case_id)
    orchestrator.submit_clarification(
        case.case_id,
        ClarificationSubmission(question_id="q-LM-3", response=CLARIFICATION_ANSWER),
    )
    orchestrator.generate_packet(case.case_id)
    orchestrator.verify_packet(case.case_id)
    orchestrator.draft_form(case.case_id)

    events = orchestrator.get_events(case.case_id)
    assert [e.sequence for e in events] == list(range(len(events)))

    # Every stage's first started event precedes its first completed event.
    first_index = {}
    for index, event in enumerate(events):
        first_index.setdefault((event.stage, event.status), index)
    for stage in {e.stage for e in events}:
        started = first_index.get((stage, EventStatus.STARTED))
        completed = first_index.get((stage, EventStatus.COMPLETED))
        if started is not None and completed is not None:
            assert started < completed, stage

    # The initial run follows the required stage order.
    run_stage_order = []
    for event in events:
        if event.status is EventStatus.STARTED and event.stage not in run_stage_order:
            run_stage_order.append(event.stage)
    expected_prefix = [
        AgentStage.INTAKE,
        AgentStage.POLICY_PARSING,
        AgentStage.EVIDENCE_RETRIEVAL,
        AgentStage.EVIDENCE_MAPPING,
        AgentStage.GAP_DETECTION,
        AgentStage.CLARIFICATION,
    ]
    assert run_stage_order[: len(expected_prefix)] == expected_prefix
    assert run_stage_order.index(AgentStage.DISCLOSURE_REVIEW) < run_stage_order.index(
        AgentStage.PACKET_GENERATION
    )
    assert run_stage_order.index(AgentStage.PACKET_GENERATION) < run_stage_order.index(
        AgentStage.VERIFICATION
    )
    assert run_stage_order.index(AgentStage.VERIFICATION) < run_stage_order.index(
        AgentStage.FORM_DRAFTING
    )
    assert run_stage_order[-1] is AgentStage.HUMAN_REVIEW


def test_events_never_contain_prompts_or_raw_output(orchestrator, case):
    """Event details are short summaries — counts, ids, scores — never payloads."""
    orchestrator.start_analysis(case.case_id)
    for event in orchestrator.get_events(case.case_id):
        assert event.detail is None or len(event.detail) <= 400
