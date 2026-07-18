"""Case service (creation, reset) and event recorder unit behavior."""

from datetime import datetime, timezone

import pytest

from app.contracts import AgentStage, CaseStatus, EventStatus
from app.events import EventRecorder
from app.services.cases import (
    CaseNotFoundError,
    CaseOperationError,
    CaseService,
    IntakeValidationError,
)

from tests.orchestration.conftest import build_case, make_orchestrator
from tests.orchestration.fakes import FakeCaseRepository


def test_create_case_moves_draft_to_intake_ready_with_event():
    service = CaseService(FakeCaseRepository())
    created = service.create_case(build_case(status=CaseStatus.DRAFT))

    assert created.status is CaseStatus.INTAKE_READY
    assert created.events[0].stage is AgentStage.INTAKE
    assert created.events[0].status is EventStatus.COMPLETED


def test_create_case_rejects_empty_intake_inputs():
    service = CaseService(FakeCaseRepository())
    case = build_case(status=CaseStatus.DRAFT)
    case.encounter_note.text = "   "
    with pytest.raises(IntakeValidationError) as excinfo:
        service.create_case(case)
    assert "encounter note" in str(excinfo.value)


def test_create_case_rejects_mid_workflow_status():
    service = CaseService(FakeCaseRepository())
    with pytest.raises(CaseOperationError):
        service.create_case(build_case(status=CaseStatus.ANALYZING))


def test_get_case_translates_not_found():
    service = CaseService(FakeCaseRepository())
    with pytest.raises(CaseNotFoundError) as excinfo:
        service.get_case("missing")
    assert excinfo.value.error_code == "case_not_found"


def test_demo_reset_clears_cases_and_recreation_converges():
    repository = FakeCaseRepository()
    orchestrator = make_orchestrator(repository)
    service = CaseService(repository)
    service.create_case(build_case(status=CaseStatus.DRAFT))
    orchestrator.start_analysis("case-demo-1")

    service.reset_demo()
    assert service.list_case_ids() == []
    with pytest.raises(CaseNotFoundError):
        orchestrator.get_case("case-demo-1")

    reseeded = service.create_case(build_case(status=CaseStatus.DRAFT))
    assert reseeded.status is CaseStatus.INTAKE_READY
    assert reseeded.assessments == [] and reseeded.readiness_history == []


def test_recorder_sequences_are_monotonic_and_ids_stable():
    fixed = datetime(2026, 7, 18, 12, 0, 0, tzinfo=timezone.utc)
    recorder = EventRecorder(clock=lambda: fixed)
    case = build_case()

    first = recorder.started(case, AgentStage.INTAKE, "Intake started")
    second = recorder.completed(case, AgentStage.INTAKE, "Intake completed")

    assert (first.sequence, second.sequence) == (0, 1)
    assert first.event_id == "case-demo-1-ev-0000"
    assert second.occurred_at == fixed


def test_recorder_truncates_oversized_detail():
    recorder = EventRecorder()
    case = build_case()
    event = recorder.completed(case, AgentStage.INTAKE, "t", detail="x" * 1000)
    assert len(event.detail) == 400
