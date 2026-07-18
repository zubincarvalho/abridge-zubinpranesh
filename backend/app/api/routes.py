"""AuthLens API routes — thin: validate, gate, delegate, return contracts.

The route set mirrors ``contracts/openapi.yaml`` exactly. There is no
submission endpoint and none may be added; ``ready_for_review`` is terminal
(docs/SAFETY_AND_HUMAN_REVIEW.md rule 4).
"""

from fastapi import APIRouter, Depends

from app.api.case_service import CaseService
from app.api.schemas import DemoScenario, HealthDetailsResponse
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


_DEMO_SCENARIOS: list[DemoScenario] = [
    DemoScenario(
        scenario_id="lumbar-mri-gap",
        fixture_id="lumbar_mri_prior_auth",
        title="Lumbar MRI — Conservative Therapy Gap",
        patient_display="Jordan Rivera, 47F",
        visit_summary="Lumbar radiculopathy · 8 weeks of symptoms",
        requested_service="MRI lumbar spine w/o contrast (CPT 72148)",
        payer="Meridian Health Plans (fictional)",
        policy_id="MHP-IMG-2201",
        expected_outcome="gap",
        expected_outcome_label="1 Gap — Needs Clarification",
        risk_level="medium",
        description=(
            "6 of 7 criteria met from chart evidence. LM-3 (conservative therapy "
            "completion) requires clinician clarification — PT referral is present but "
            "completion and outcome are not documented."
        ),
        is_real_data=False,
    ),
    DemoScenario(
        scenario_id="abridge-lbp-depression",
        fixture_id="abridge:1ba8eeb9-bc93-7129-4390-0d2ddd560616",
        title="Chronic LBP + Depression Screen",
        patient_display="Male patient, 27",
        visit_summary="Chronic low back pain · General exam · Positive depression screen",
        requested_service="MRI lumbar spine w/o contrast (CPT 72148)",
        payer="Meridian Health Plans (fictional)",
        policy_id="MHP-IMG-2201",
        expected_outcome="high_risk",
        expected_outcome_label="High Denial Risk",
        risk_level="high",
        description=(
            "Real Abridge AI encounter. Younger patient with chronic LBP — "
            "conservative therapy completion, neurological exam findings, and "
            "functional limitation may be insufficiently documented for approval."
        ),
        is_real_data=True,
    ),
    DemoScenario(
        scenario_id="abridge-htn-lbp",
        fixture_id="abridge:6d4fd363-1ddb-74f8-516f-2fdc861cb736",
        title="Hypertension Initiation + Chronic LBP",
        patient_display="Male patient, 36",
        visit_summary="Hypertension treatment start · Chronic low back pain co-presentation",
        requested_service="MRI lumbar spine w/o contrast (CPT 72148)",
        payer="Meridian Health Plans (fictional)",
        policy_id="MHP-IMG-2201",
        expected_outcome="high_risk",
        expected_outcome_label="High Denial Risk",
        risk_level="high",
        description=(
            "Real Abridge AI encounter. Primary focus is hypertension management; "
            "LBP is a secondary complaint. Neurological workup and functional "
            "limitation documentation may be insufficient for imaging approval."
        ),
        is_real_data=True,
    ),
]


@router.get("/scenarios", response_model=list[DemoScenario], tags=["demo"])
def list_scenarios() -> list[DemoScenario]:
    return _DEMO_SCENARIOS


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
