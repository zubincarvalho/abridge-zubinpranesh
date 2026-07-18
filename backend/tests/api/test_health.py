"""GET /api/health: liveness, provider mode, no credential exposure."""

SECRET = "sk-ant-test-super-secret-key-000"


def test_health_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "authlens"
    assert isinstance(body["version"], str) and body["version"]
    assert body["provider_mode"] in {"live", "deterministic"}


def test_health_reports_deterministic_mode(client, monkeypatch):
    monkeypatch.setenv("DEMO_MODE", "true")
    assert client.get("/api/health").json()["provider_mode"] == "deterministic"


def test_health_reports_live_mode(client, monkeypatch):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    assert client.get("/api/health").json()["provider_mode"] == "live"


def test_health_never_exposes_credentials(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert SECRET not in response.text
    assert "api_key" not in response.text.lower()


def test_openapi_schema_never_exposes_credentials(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert SECRET not in response.text
