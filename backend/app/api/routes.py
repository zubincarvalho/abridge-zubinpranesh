"""AuthLens API routes — thin: validate, gate, delegate, return contracts.

The route set mirrors ``contracts/openapi.yaml`` exactly. There is no
submission endpoint and none may be added; ``ready_for_review`` is terminal
(docs/SAFETY_AND_HUMAN_REVIEW.md rule 4).
"""

from fastapi import APIRouter, Depends

from app.api.case_service import CaseService
from app.api.schemas import HealthDetailsResponse
from app.api_dependencies import (
    get_case_service,
    get_provider_mode,
    get_settings,
    get_workflow_orchestrator,
)
from app.config import Settings
from app.contracts import (
    AgentEvent,
    ApiError,
    AuthLensCase,
    CaseStatus,
    ClarificationSubmission,
    CreateCaseRequest,
    DemoResetResponse,
    EvidenceSourceResponse,
)
from app.ports import WorkflowOrchestrator

router = APIRouter(prefix="/api")


def _errors(*codes: int) -> dict[int | str, dict]:
    return {code: {"model": ApiError} for code in codes}


@router.get("/health", response_model=HealthDetailsResponse, tags=["system"])
def get_health(
    settings: Settings = Depends(get_settings),
    provider_mode: str = Depends(get_provider_mode),
) -> HealthDetailsResponse:
    return HealthDetailsResponse(
        service=settings.app_name,
        version=settings.app_version,
        provider_mode=provider_mode,
    )


@router.get(
    "/demo-case",
    response_model=AuthLensCase,
    responses=_errors(404),
    tags=["demo"],
)
def get_demo_case(service: CaseService = Depends(get_case_service)) -> AuthLensCase:
    return service.get_or_seed_demo_case()


@router.post(
    "/cases",
    response_model=AuthLensCase,
    status_code=201,
    responses=_errors(404, 422),
    tags=["cases"],
)
def create_case(
    request: CreateCaseRequest,
    service: CaseService = Depends(get_case_service),
) -> AuthLensCase:
    return service.create_case(request.fixture_id)


@router.get(
    "/cases/{case_id}",
    response_model=AuthLensCase,
    responses=_errors(404),
    tags=["cases"],
)
def get_case(
    case_id: str, service: CaseService = Depends(get_case_service)
) -> AuthLensCase:
    return service.get_case(case_id)


@router.post(
    "/cases/{case_id}/run",
    response_model=AuthLensCase,
    responses=_errors(404, 409),
    tags=["workflow"],
)
def run_analysis(
    case_id: str,
    service: CaseService = Depends(get_case_service),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
) -> AuthLensCase:
    service.ensure_status(
        case_id, (CaseStatus.INTAKE_READY,), "run the analysis pipeline"
    )
    return orchestrator.start_analysis(case_id)


@router.post(
    "/cases/{case_id}/clarifications",
    response_model=AuthLensCase,
    responses=_errors(404, 409, 422),
    tags=["workflow"],
)
def submit_clarification(
    case_id: str,
    submission: ClarificationSubmission,
    service: CaseService = Depends(get_case_service),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
) -> AuthLensCase:
    service.ensure_clarification_open(case_id, submission.question_id)
    return orchestrator.submit_clarification(case_id, submission)


@router.post(
    "/cases/{case_id}/generate-packet",
    response_model=AuthLensCase,
    responses=_errors(404, 409),
    tags=["workflow"],
)
def generate_packet(
    case_id: str,
    service: CaseService = Depends(get_case_service),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
) -> AuthLensCase:
    service.ensure_status(
        case_id,
        (CaseStatus.AWAITING_CLARIFICATION, CaseStatus.VERIFICATION_FAILED),
        "generate the packet",
    )
    return orchestrator.generate_packet(case_id)


@router.post(
    "/cases/{case_id}/verify",
    response_model=AuthLensCase,
    responses=_errors(404, 409),
    tags=["workflow"],
)
def verify_packet(
    case_id: str,
    service: CaseService = Depends(get_case_service),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
) -> AuthLensCase:
    service.ensure_status(case_id, (CaseStatus.PACKET_DRAFTED,), "verify the packet")
    return orchestrator.verify_packet(case_id)


@router.post(
    "/cases/{case_id}/form-draft",
    response_model=AuthLensCase,
    responses=_errors(404, 409),
    tags=["workflow"],
)
def draft_form(
    case_id: str,
    service: CaseService = Depends(get_case_service),
    orchestrator: WorkflowOrchestrator = Depends(get_workflow_orchestrator),
) -> AuthLensCase:
    service.ensure_form_draft_allowed(case_id)
    return orchestrator.draft_form(case_id)


@router.get(
    "/cases/{case_id}/events",
    response_model=list[AgentEvent],
    responses=_errors(404),
    tags=["cases"],
)
def list_events(
    case_id: str, service: CaseService = Depends(get_case_service)
) -> list[AgentEvent]:
    return service.get_events(case_id)


@router.get(
    "/cases/{case_id}/evidence/{source_id}",
    response_model=EvidenceSourceResponse,
    responses=_errors(404),
    tags=["cases"],
)
def get_evidence_source(
    case_id: str,
    source_id: str,
    service: CaseService = Depends(get_case_service),
) -> EvidenceSourceResponse:
    return service.resolve_evidence_source(case_id, source_id)


@router.post("/demo/reset", response_model=DemoResetResponse, tags=["demo"])
def reset_demo(service: CaseService = Depends(get_case_service)) -> DemoResetResponse:
    case = service.reset_demo()
    return DemoResetResponse(demo_case_id=case.case_id)
