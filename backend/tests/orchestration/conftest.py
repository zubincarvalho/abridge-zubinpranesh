from datetime import datetime, timezone

import pytest

from app.contracts import (
    AuthLensCase,
    CaseStatus,
    ChartItem,
    EncounterNote,
    EncounterTranscript,
    PatientSummary,
    PayerPolicy,
    RequestedService,
)
from app.orchestration import AuthLensOrchestrator

from tests.orchestration.fakes import (
    NOTE_TEXT,
    POLICY_TEXT,
    TRANSCRIPT_TEXT,
    FakeCaseRepository,
    FakeDisclosureFilter,
    FakeEvidenceMapper,
    FakeEvidenceRetriever,
    FakeFormDrafter,
    FakeGapDetector,
    FakePacketGenerator,
    FakePacketVerifier,
    FakePolicyParser,
)

CLARIFICATION_ANSWER = (
    "Patient completed 8 weeks of supervised physical therapy with no "
    "symptom improvement."
)


def build_case(
    case_id: str = "case-demo-1", status: CaseStatus = CaseStatus.INTAKE_READY
) -> AuthLensCase:
    now = datetime.now(timezone.utc)
    return AuthLensCase(
        case_id=case_id,
        status=status,
        created_at=now,
        updated_at=now,
        patient=PatientSummary(
            patient_id="pat-1",
            display_name="Sam Rivera (synthetic)",
            birth_date="1978-03-14",
            sex="female",
            chart_items=[
                ChartItem(
                    source_id="src-chart-referral",
                    category="referral",
                    display="Referral to physical therapy",
                    detail="Ordered eight weeks before this encounter",
                ),
                ChartItem(
                    source_id="src-chart-anxiety",
                    category="condition",
                    display="Generalized anxiety disorder",
                ),
            ],
        ),
        requested_service=RequestedService(
            service_name="MRI lumbar spine without contrast", code="72148"
        ),
        clinical_indication="Chronic low back pain with radiculopathy",
        indication_codes=["M54.16"],
        encounter_note=EncounterNote(
            source_id="src-note", title="Encounter note", text=NOTE_TEXT
        ),
        encounter_transcript=EncounterTranscript(
            source_id="src-transcript", text=TRANSCRIPT_TEXT
        ),
        policy=PayerPolicy(
            policy_id="MHP-IMG-2201",
            payer_name="Meridian Health Plan",
            policy_title="Lumbar Spine MRI Medical Necessity",
            service_description="MRI lumbar spine (CPT 72148)",
            source_document="data/policies/lumbar_mri_policy.md",
        ),
    )


def make_orchestrator(
    repository: FakeCaseRepository | None = None, **overrides
) -> AuthLensOrchestrator:
    deps = {
        "policy_parser": FakePolicyParser(),
        "evidence_retriever": FakeEvidenceRetriever(),
        "evidence_mapper": FakeEvidenceMapper(),
        "gap_detector": FakeGapDetector(),
        "disclosure_filter": FakeDisclosureFilter(),
        "packet_generator": FakePacketGenerator(),
        "packet_verifier": FakePacketVerifier(),
        "form_drafter": FakeFormDrafter(),
        "policy_text_loader": lambda policy: POLICY_TEXT,
    }
    deps.update(overrides)
    return AuthLensOrchestrator(repository or FakeCaseRepository(), **deps)


@pytest.fixture
def repository() -> FakeCaseRepository:
    return FakeCaseRepository()


@pytest.fixture
def case(repository: FakeCaseRepository) -> AuthLensCase:
    return repository.create(build_case())


@pytest.fixture
def orchestrator(repository: FakeCaseRepository) -> AuthLensOrchestrator:
    return make_orchestrator(repository)
