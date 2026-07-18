"""Development CORS: configurable allowlist, sane defaults."""

from fastapi.testclient import TestClient

from app.api_dependencies import DEFAULT_CORS_ORIGINS, resolve_cors_origins
from app.main import create_app


def test_allowed_origin_gets_cors_headers(client):
    response = client.get("/api/health", headers={"Origin": "http://allowed.example"})
    assert response.headers.get("access-control-allow-origin") == "http://allowed.example"


def test_disallowed_origin_gets_no_cors_headers(client):
    response = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in response.headers


def test_preflight_for_allowed_origin(client):
    response = client.options(
        "/api/cases",
        headers={
            "Origin": "http://allowed.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://allowed.example"


def test_origins_configurable_via_env(
    monkeypatch, fake_repository, fake_fixtures, fake_orchestrator
):
    monkeypatch.setenv("AUTHLENS_CORS_ORIGINS", "http://from-env.example, http://two.example")
    app = create_app(
        case_repository=fake_repository,
        fixture_provider=fake_fixtures,
        workflow_orchestrator=fake_orchestrator,
        seed_demo_on_startup=False,
    )
    with TestClient(app) as client:
        response = client.get("/api/health", headers={"Origin": "http://from-env.example"})
        assert (
            response.headers.get("access-control-allow-origin")
            == "http://from-env.example"
        )


def test_default_origins_are_local_dev(monkeypatch):
    monkeypatch.delenv("AUTHLENS_CORS_ORIGINS", raising=False)
    assert resolve_cors_origins() == list(DEFAULT_CORS_ORIGINS)
    assert "http://localhost:5173" in DEFAULT_CORS_ORIGINS
