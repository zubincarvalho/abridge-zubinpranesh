"""The generated OpenAPI surface must match contracts/openapi.yaml."""

from pathlib import Path

import yaml

from app.contracts import CaseStatus

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_SPEC_PATH = REPO_ROOT / "contracts" / "openapi.yaml"
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _contract_spec() -> dict:
    return yaml.safe_load(CONTRACT_SPEC_PATH.read_text())


def _operations(spec: dict) -> set[tuple[str, str]]:
    return {
        (path, method)
        for path, item in spec["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }


def test_generated_paths_match_contract_exactly(app):
    contract_ops = _operations(_contract_spec())
    generated_ops = _operations(app.openapi())
    assert generated_ops == contract_ops


def test_no_submission_endpoint_generated(app):
    for path in app.openapi()["paths"]:
        assert "submit" not in path.lower()


def test_generated_case_status_enum_matches_contract(app):
    contract_enum = _contract_spec()["components"]["schemas"]["CaseStatus"]["enum"]
    generated_enum = app.openapi()["components"]["schemas"]["CaseStatus"]["enum"]
    assert generated_enum == contract_enum
    assert generated_enum == [status.value for status in CaseStatus]
    assert "submitted" not in generated_enum


def test_generated_schemas_include_core_contracts(app):
    schemas = app.openapi()["components"]["schemas"]
    for name in ("AuthLensCase", "ApiError", "AgentEvent", "EvidenceSourceResponse"):
        assert name in schemas, f"missing schema {name}"


def test_create_case_documents_201(app):
    spec = app.openapi()
    responses = spec["paths"]["/api/cases"]["post"]["responses"]
    assert "201" in responses
