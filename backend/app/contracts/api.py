"""API request/response envelope contracts.

Endpoints that mutate a case return the full AuthLensCase so the frontend
never reconstructs clinical logic client-side. Errors always use ApiError.
"""

from typing import Literal

from pydantic import Field

from app.contracts._base import ContractModel
from app.contracts.evidence import SourceType


class HealthResponse(ContractModel):
    status: Literal["ok"] = "ok"
    service: str = "authlens"
    version: str


class CreateCaseRequest(ContractModel):
    """Create a case from a named synthetic fixture (demo scope)."""

    fixture_id: str = "lumbar_mri_prior_auth"


class ClarificationSubmission(ContractModel):
    """POST /api/cases/{case_id}/clarifications request body."""

    question_id: str
    response: str = Field(min_length=1)


class EvidenceSourceResponse(ContractModel):
    """GET /api/cases/{case_id}/evidence/{source_id} — citation drawer content."""

    source_id: str
    source_type: SourceType
    label: str
    content: str
    fhir_resource_type: str | None = None


class DemoResetResponse(ContractModel):
    status: Literal["reset"] = "reset"
    demo_case_id: str


class ApiError(ContractModel):
    """Uniform error shape for every non-2xx response."""

    error_code: str = Field(
        description="Stable machine-readable code, e.g. 'case_not_found', "
        "'invalid_state_transition', 'packet_not_verified', 'question_not_found'"
    )
    message: str
    detail: str | None = None
    case_id: str | None = None
