"""GET /api/demo-case and POST /api/demo/reset."""

from app.api.case_service import DEMO_CASE_ID
from app.contracts import CaseStatus

from tests.api.conftest import advance, assert_api_error, create_case


def test_demo_case_seeds_lazily(client):
    response = client.get("/api/demo-case")
    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == DEMO_CASE_ID
    assert body["status"] == "intake_ready"
    assert body["synthetic"] is True


def test_demo_case_returns_current_state(client):
    demo_id = client.get("/api/demo-case").json()["case_id"]
    advance(client, demo_id, CaseStatus.AWAITING_CLARIFICATION)
    body = client.get("/api/demo-case").json()
    assert body["case_id"] == demo_id
    assert body["status"] == "awaiting_clarification"


def test_reset_returns_contract_shape(client):
    response = client.post("/api/demo/reset")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "reset", "demo_case_id": DEMO_CASE_ID}


def test_reset_restores_seeded_state(client):
    demo_id = client.get("/api/demo-case").json()["case_id"]
    advance(client, demo_id, CaseStatus.PACKET_DRAFTED)
    client.post("/api/demo/reset")
    body = client.get("/api/demo-case").json()
    assert body["status"] == "intake_ready"
    assert body["packet"] is None
    assert body["events"] == []


def test_reset_removes_all_other_cases(client):
    case_id = create_case(client)
    client.post("/api/demo/reset")
    assert_api_error(client.get(f"/api/cases/{case_id}"), 404, "case_not_found")


def test_reset_is_idempotent(client):
    first = client.post("/api/demo/reset").json()
    second = client.post("/api/demo/reset").json()
    assert first == second
    assert client.get("/api/demo-case").json()["status"] == "intake_ready"


def test_startup_seeding(fake_repository, fake_fixtures, fake_orchestrator):
    from fastapi.testclient import TestClient

    from app.main import create_app

    app = create_app(
        case_repository=fake_repository,
        fixture_provider=fake_fixtures,
        workflow_orchestrator=fake_orchestrator,
        seed_demo_on_startup=True,
        cors_origins=[],
    )
    with TestClient(app) as client:
        assert DEMO_CASE_ID in fake_repository.list_case_ids()
        assert client.get("/api/demo-case").json()["case_id"] == DEMO_CASE_ID
