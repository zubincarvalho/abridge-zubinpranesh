"""POST /api/cases and GET /api/cases/{case_id}: creation, reads, validation."""

from tests.api.conftest import DEMO_FIXTURE_ID, assert_api_error, create_case


def test_create_case_returns_201_and_full_case(client):
    response = client.post("/api/cases", json={"fixture_id": DEMO_FIXTURE_ID})
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "intake_ready"
    assert body["synthetic"] is True
    assert body["case_id"].startswith("case-")
    # Frontend-safe full-case shape: every panel field is present.
    for field in (
        "patient",
        "requested_service",
        "encounter_note",
        "policy",
        "criteria",
        "assessments",
        "clarification_questions",
        "clarifications",
        "readiness_history",
        "disclosure_decisions",
        "events",
    ):
        assert field in body, f"missing {field}"
    assert body["policy"]["synthetic"] is True
    assert body["packet"] is None
    assert body["verification"] is None
    assert body["form_draft"] is None


def test_create_case_uses_default_fixture(client):
    response = client.post("/api/cases", json={})
    assert response.status_code == 201
    assert response.json()["status"] == "intake_ready"


def test_create_case_is_not_idempotent(client):
    first = create_case(client)
    second = create_case(client)
    assert first != second


def test_create_case_unknown_fixture_is_404(client):
    response = client.post("/api/cases", json={"fixture_id": "nope"})
    assert_api_error(response, 404, "fixture_not_found")


def test_create_case_rejects_non_string_fixture_id(client):
    response = client.post("/api/cases", json={"fixture_id": 123})
    body = assert_api_error(response, 422, "validation_error")
    assert "fixture_id" in (body["detail"] or "")


def test_create_case_rejects_undeclared_fields(client):
    response = client.post(
        "/api/cases", json={"fixture_id": DEMO_FIXTURE_ID, "bogus": True}
    )
    assert_api_error(response, 422, "validation_error")


def test_get_case_roundtrip(client):
    case_id = create_case(client)
    response = client.get(f"/api/cases/{case_id}")
    assert response.status_code == 200
    assert response.json()["case_id"] == case_id


def test_get_missing_case_is_404(client):
    response = client.get("/api/cases/case-does-not-exist")
    body = assert_api_error(response, 404, "case_not_found")
    assert body["case_id"] == "case-does-not-exist"
