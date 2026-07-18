"""Workflow endpoints: transitions, gates, clarifications, verification."""

from datetime import datetime, timezone

from app.contracts import CaseStatus

from tests.api.conftest import (
    FakeWorkflowOrchestrator,
    advance,
    assert_api_error,
    create_case,
    make_intake_case,
)

Q = FakeWorkflowOrchestrator.QUESTION_ID


# --- run ---------------------------------------------------------------------


def test_run_transitions_to_awaiting_clarification(client):
    case_id = create_case(client)
    response = client.post(f"/api/cases/{case_id}/run")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_clarification"
    assert body["criteria"] and body["assessments"] and body["clarification_questions"]
    assert body["readiness_history"][0]["score"] == 79


def test_run_twice_is_409(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    body = assert_api_error(
        client.post(f"/api/cases/{case_id}/run"), 409, "invalid_state_transition"
    )
    assert body["case_id"] == case_id


def test_run_missing_case_is_404(client):
    assert_api_error(client.post("/api/cases/nope/run"), 404, "case_not_found")


def test_failed_gate_does_not_mutate_case(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    before = client.get(f"/api/cases/{case_id}").json()
    assert_api_error(
        client.post(f"/api/cases/{case_id}/run"), 409, "invalid_state_transition"
    )
    assert client.get(f"/api/cases/{case_id}").json() == before


# --- clarifications ------------------------------------------------------------


def test_submit_clarification_reevaluates(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    response = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": Q, "response": "Completed 8 weeks of PT, documented."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_clarification"
    assert body["clarification_questions"][0]["status"] == "answered"
    assert body["clarifications"][0]["response"] == "Completed 8 weeks of PT, documented."
    assert body["readiness_history"][-1]["score"] == 93


def test_clarification_wrong_state_is_409(client):
    case_id = create_case(client)
    response = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": Q, "response": "answer"},
    )
    assert_api_error(response, 409, "invalid_state_transition")


def test_clarification_unknown_question_is_404(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    response = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": "q-unknown", "response": "answer"},
    )
    assert_api_error(response, 404, "question_not_found")


def test_clarification_reanswer_is_409(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    first = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": Q, "response": "answer"},
    )
    assert first.status_code == 200
    second = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": Q, "response": "answer again"},
    )
    assert_api_error(second, 409, "question_already_answered")


def test_clarification_empty_response_is_422(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    response = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": Q, "response": ""},
    )
    assert_api_error(response, 422, "validation_error")


def test_clarification_missing_body_field_is_422(client):
    case_id = create_case(client)
    response = client.post(
        f"/api/cases/{case_id}/clarifications", json={"question_id": Q}
    )
    assert_api_error(response, 422, "validation_error")


# --- generate-packet -----------------------------------------------------------


def test_generate_packet_from_awaiting_clarification(client):
    case_id = create_case(client)
    body = advance(client, case_id, CaseStatus.PACKET_DRAFTED)
    assert body["packet"] is not None
    assert body["disclosure_decisions"]
    decisions = {d["decision"] for d in body["disclosure_decisions"]}
    assert decisions == {"include", "exclude"}


def test_generate_packet_wrong_state_is_409(client):
    case_id = create_case(client)
    response = client.post(f"/api/cases/{case_id}/generate-packet")
    assert_api_error(response, 409, "invalid_state_transition")


# --- verify --------------------------------------------------------------------


def test_verify_passed(client):
    case_id = create_case(client)
    body = advance(client, case_id, CaseStatus.VERIFIED)
    assert body["verification"]["passed"] is True
    assert body["verification"]["checked_claim_count"] == 1


def test_verify_failure_is_http_200_with_verification_failed(client, fake_orchestrator):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.PACKET_DRAFTED)
    fake_orchestrator.next_verification_passed = False
    response = client.post(f"/api/cases/{case_id}/verify")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "verification_failed"
    assert body["verification"]["passed"] is False
    assert body["verification"]["issues"][0]["severity"] == "blocking"


def test_regenerate_packet_after_verification_failure(client, fake_orchestrator):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.PACKET_DRAFTED)
    fake_orchestrator.next_verification_passed = False
    client.post(f"/api/cases/{case_id}/verify")
    response = client.post(f"/api/cases/{case_id}/generate-packet")
    assert response.status_code == 200
    assert response.json()["status"] == "packet_drafted"
    fake_orchestrator.next_verification_passed = True
    assert client.post(f"/api/cases/{case_id}/verify").json()["status"] == "verified"


def test_verify_wrong_state_is_409(client):
    case_id = create_case(client)
    response = client.post(f"/api/cases/{case_id}/verify")
    assert_api_error(response, 409, "invalid_state_transition")


# --- form-draft (the verification gate) -----------------------------------------


def test_form_draft_happy_path_is_terminal(client):
    case_id = create_case(client)
    body = advance(client, case_id, CaseStatus.READY_FOR_REVIEW)
    assert body["form_draft"] is not None
    assert body["form_draft"]["status"] == "ready_for_review"
    assert "review" in body["form_draft"]["attestation"].lower()


def test_form_draft_before_verification_is_409(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.PACKET_DRAFTED)
    response = client.post(f"/api/cases/{case_id}/form-draft")
    assert_api_error(response, 409, "packet_not_verified")


def test_form_draft_in_awaiting_clarification_is_409(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    response = client.post(f"/api/cases/{case_id}/form-draft")
    assert_api_error(response, 409, "packet_not_verified")


def test_form_draft_after_failed_verification_is_409(client, fake_orchestrator):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.PACKET_DRAFTED)
    fake_orchestrator.next_verification_passed = False
    client.post(f"/api/cases/{case_id}/verify")
    response = client.post(f"/api/cases/{case_id}/form-draft")
    assert_api_error(response, 409, "packet_not_verified")


def test_form_draft_requires_stored_passing_result(client, fake_repository):
    # Even with status 'verified', a missing VerificationResult blocks drafting.
    case = make_intake_case("case-forged-001")
    case.status = CaseStatus.VERIFIED
    case.updated_at = datetime.now(timezone.utc)
    fake_repository.create(case)
    response = client.post("/api/cases/case-forged-001/form-draft")
    assert_api_error(response, 409, "packet_not_verified")


def test_form_draft_twice_is_409(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.READY_FOR_REVIEW)
    response = client.post(f"/api/cases/{case_id}/form-draft")
    assert_api_error(response, 409, "packet_not_verified")


# --- failure posture -------------------------------------------------------------


def test_unexpected_orchestrator_error_is_500_internal_error(
    client, fake_orchestrator, monkeypatch
):
    case_id = create_case(client)

    def boom(_case_id):
        raise RuntimeError("stack trace details that must not leak")

    monkeypatch.setattr(fake_orchestrator, "start_analysis", boom)
    response = client.post(f"/api/cases/{case_id}/run")
    body = assert_api_error(response, 500, "internal_error")
    assert "stack trace" not in response.text
    assert body["detail"] is None


def test_default_composition_wires_the_real_orchestrator(
    fake_repository, fake_fixtures, monkeypatch
):
    """Integration replaced the placeholder with Agent F's real orchestrator.

    The temporary ``PlaceholderWorkflowOrchestrator`` no longer exists; the
    default composition root must build the deterministic
    ``AuthLensOrchestrator`` over the real stage ports.
    """
    monkeypatch.setenv("DEMO_MODE", "true")  # deterministic; no key required

    from app import api_dependencies as deps
    from app.orchestration import AuthLensOrchestrator

    assert not hasattr(deps, "PlaceholderWorkflowOrchestrator")
    orchestrator = deps.build_default_workflow_orchestrator(
        fake_repository, fake_fixtures
    )
    assert isinstance(orchestrator, AuthLensOrchestrator)
