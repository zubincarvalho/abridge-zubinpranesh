"""contracts/openapi.yaml must be valid and complete."""

import yaml
from openapi_spec_validator import validate

from tests.contracts.conftest import OPENAPI_PATH

REQUIRED_PATHS = {
    "/api/health": {"get"},
    "/api/demo-case": {"get"},
    "/api/cases": {"post"},
    "/api/cases/{case_id}": {"get"},
    "/api/cases/{case_id}/run": {"post"},
    "/api/cases/{case_id}/clarifications": {"post"},
    "/api/cases/{case_id}/generate-packet": {"post"},
    "/api/cases/{case_id}/verify": {"post"},
    "/api/cases/{case_id}/form-draft": {"post"},
    "/api/cases/{case_id}/events": {"get"},
    "/api/cases/{case_id}/evidence/{source_id}": {"get"},
    "/api/demo/reset": {"post"},
}


def load_spec() -> dict:
    return yaml.safe_load(OPENAPI_PATH.read_text())


def test_spec_is_valid_openapi():
    validate(load_spec())


def test_all_required_endpoints_present():
    spec = load_spec()
    for path, methods in REQUIRED_PATHS.items():
        assert path in spec["paths"], f"missing path {path}"
        assert methods <= set(spec["paths"][path]), f"missing method on {path}"
    assert set(spec["paths"]) == set(REQUIRED_PATHS), "no undocumented endpoints"


def test_case_status_enum_matches_contract():
    from app.contracts import CaseStatus

    spec_enum = load_spec()["components"]["schemas"]["CaseStatus"]["enum"]
    assert spec_enum == [s.value for s in CaseStatus]
    assert "submitted" not in spec_enum


def test_no_submission_endpoint():
    spec = load_spec()
    for path in spec["paths"]:
        assert "submit" not in path.lower()
