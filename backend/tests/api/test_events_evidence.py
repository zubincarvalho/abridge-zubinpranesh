"""GET /events and GET /evidence/{source_id}: timeline and citation drawer."""

from app.contracts import CaseStatus

from tests.api.conftest import (
    FakeWorkflowOrchestrator,
    NOTE_TEXT,
    advance,
    assert_api_error,
    create_case,
)

Q = FakeWorkflowOrchestrator.QUESTION_ID


# --- events -----------------------------------------------------------------


def test_events_empty_at_intake(client):
    case_id = create_case(client)
    response = client.get(f"/api/cases/{case_id}/events")
    assert response.status_code == 200
    assert response.json() == []


def test_events_ordered_by_sequence(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.PACKET_DRAFTED)
    response = client.get(f"/api/cases/{case_id}/events")
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 2
    assert [e["sequence"] for e in events] == sorted(e["sequence"] for e in events)
    for event in events:
        assert event["case_id"] == case_id
        assert set(event) >= {
            "event_id",
            "sequence",
            "stage",
            "status",
            "title",
            "related_ids",
            "occurred_at",
        }


def test_events_missing_case_is_404(client):
    assert_api_error(client.get("/api/cases/nope/events"), 404, "case_not_found")


# --- evidence ------------------------------------------------------------------


def test_resolve_note_source(client):
    case_id = create_case(client)
    response = client.get(f"/api/cases/{case_id}/evidence/note-001")
    assert response.status_code == 200
    body = response.json()
    assert body["source_id"] == "note-001"
    assert body["source_type"] == "encounter_note"
    assert body["content"] == NOTE_TEXT
    assert body["label"]


def test_resolve_chart_item_source(client):
    case_id = create_case(client)
    response = client.get(f"/api/cases/{case_id}/evidence/chart-med-001")
    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "fhir_resource"
    assert "Naproxen" in body["content"]


def test_resolve_clarification_source_verbatim(client):
    case_id = create_case(client)
    advance(client, case_id, CaseStatus.AWAITING_CLARIFICATION)
    answer = "Patient completed 8 weeks of physical therapy ending last month."
    client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": Q, "response": answer},
    )
    case = client.get(f"/api/cases/{case_id}").json()
    clarification_id = case["clarifications"][0]["clarification_id"]
    response = client.get(f"/api/cases/{case_id}/evidence/{clarification_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["source_type"] == "clinician_clarification"
    assert body["content"] == answer  # verbatim, never paraphrased


def test_unknown_source_is_404(client):
    case_id = create_case(client)
    response = client.get(f"/api/cases/{case_id}/evidence/src-unknown")
    body = assert_api_error(response, 404, "source_not_found")
    assert body["case_id"] == case_id


def test_evidence_missing_case_is_404(client):
    response = client.get("/api/cases/nope/evidence/note-001")
    assert_api_error(response, 404, "case_not_found")
