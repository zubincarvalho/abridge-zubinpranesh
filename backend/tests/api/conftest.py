"""Local fakes for the API test suite (Agent G).

The API layer is exercised end-to-end through FastAPI's TestClient with a
fake repository, fixture provider, and workflow orchestrator — no LLMs, no
files from other agents' pipelines. The fakes raise the same canonical
error types the real implementations raise (``app.repositories.errors``,
``app.data.errors``) so the API's translation paths are the ones under test.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.contracts import (
    AgentEvent,
    AgentStage,
    AuthLensCase,
    CaseStatus,
    ChartItem,
    ClarificationQuestion,
    ClarificationSubmission,
    ClinicianClarification,
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    DisclosureDecision,
    DisclosureDecisionType,
    EncounterNote,
    EncounterTranscript,
    EventStatus,
    EvidenceSource,
    FormDraftField,
    PacketClaim,
    PacketSection,
    PacketStatus,
    PatientSummary,
    PayerPolicy,
    PolicyCriterion,
    PriorAuthorizationFormDraft,
    PriorAuthorizationPacket,
    ReadinessSummary,
    RequestedService,
    SourceType,
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)
from app.data.errors import FixtureNotFoundError, SourceNotFoundError
from app.main import create_app
from app.repositories.errors import CaseAlreadyExistsError, CaseNotFoundError

DEMO_FIXTURE_ID = "lumbar_mri_prior_auth"
NOTE_TEXT = (
    "Low back pain radiating down the left leg for 8 weeks. "
    "Naproxen 500 mg twice daily is on the medication list. "
    "Referral to physical therapy is in place."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_intake_case(case_id: str = "case-test-001") -> AuthLensCase:
    now = _now()
    return AuthLensCase(
        case_id=case_id,
        status=CaseStatus.INTAKE_READY,
        created_at=now,
        updated_at=now,
        synthetic=True,
        patient=PatientSummary(
            patient_id="patient-001",
            display_name="Jordan Rivera",
            birth_date="1978-03-14",
            sex="female",
            chart_items=[
                ChartItem(
                    source_id="chart-med-001",
                    category="medication",
                    display="Naproxen 500 mg twice daily",
                    detail="Active prescription",
                ),
                ChartItem(
                    source_id="chart-ref-001",
                    category="referral",
                    display="Referral to physical therapy",
                ),
            ],
        ),
        requested_service=RequestedService(
            service_name="MRI lumbar spine without contrast",
            code="72148",
            code_system="CPT",
            modality="MRI",
            body_site="lumbar spine",
        ),
        clinical_indication="Low back pain with left leg radiation",
        indication_codes=["M54.16"],
        encounter_note=EncounterNote(
            source_id="note-001",
            title="Clinic note - low back pain follow-up",
            text=NOTE_TEXT,
        ),
        encounter_transcript=EncounterTranscript(
            source_id="transcript-001",
            text="Clinician: How long has the pain been present? Patient: About eight weeks.",
        ),
        policy=PayerPolicy(
            policy_id="policy-lumbar-mri-001",
            payer_name="Acme Health (synthetic)",
            policy_title="Lumbar Spine MRI Medical Necessity",
            service_description="MRI lumbar spine without contrast",
            source_document="data/policies/lumbar_mri_policy.md",
            synthetic=True,
        ),
    )


class FakeCaseRepository:
    """Dict-backed CaseRepository raising the canonical repository errors."""

    def __init__(self) -> None:
        self._cases: dict[str, AuthLensCase] = {}

    def create(self, case: AuthLensCase) -> AuthLensCase:
        if case.case_id in self._cases:
            raise CaseAlreadyExistsError(case.case_id)
        self._cases[case.case_id] = case.model_copy(deep=True)
        return case.model_copy(deep=True)

    def get(self, case_id: str) -> AuthLensCase:
        if case_id not in self._cases:
            raise CaseNotFoundError(case_id)
        return self._cases[case_id].model_copy(deep=True)

    def save(self, case: AuthLensCase) -> AuthLensCase:
        if case.case_id not in self._cases:
            raise CaseNotFoundError(case.case_id)
        self._cases[case.case_id] = case.model_copy(deep=True)
        return case.model_copy(deep=True)

    def list_case_ids(self) -> list[str]:
        return list(self._cases)

    def reset(self) -> None:
        self._cases.clear()


class FakeFixtureProvider:
    """FixtureSource fake with a deterministic evidence-source index."""

    def __init__(self) -> None:
        self.known = {DEMO_FIXTURE_ID}

    def has(self, fixture_id: str) -> bool:
        return fixture_id in self.known

    def build_case(self, fixture_id: str, case_id: str) -> AuthLensCase:
        if fixture_id not in self.known:
            raise FixtureNotFoundError(f"unknown fixture_id {fixture_id!r}")
        return make_intake_case(case_id)

    def get_evidence_source(self, fixture_id: str, source_id: str) -> EvidenceSource:
        if fixture_id not in self.known:
            raise FixtureNotFoundError(f"unknown fixture_id {fixture_id!r}")
        template = make_intake_case("template")
        sources = [
            EvidenceSource(
                source_id=template.encounter_note.source_id,
                source_type=SourceType.ENCOUNTER_NOTE,
                label=template.encounter_note.title,
                content=template.encounter_note.text,
            ),
            EvidenceSource(
                source_id=template.encounter_transcript.source_id,
                source_type=SourceType.ENCOUNTER_TRANSCRIPT,
                label="Encounter transcript",
                content=template.encounter_transcript.text,
            ),
            EvidenceSource(
                source_id=template.policy.policy_id,
                source_type=SourceType.PAYER_POLICY,
                label=template.policy.policy_title,
                content="LM-3: Completion of at least 6 weeks of conservative therapy.",
            ),
        ]
        for item in template.patient.chart_items:
            sources.append(
                EvidenceSource(
                    source_id=item.source_id,
                    source_type=SourceType.FHIR_RESOURCE,
                    label=item.display,
                    content=item.display if item.detail is None else f"{item.display}\n{item.detail}",
                )
            )
        for source in sources:
            if source.source_id == source_id:
                return source
        raise SourceNotFoundError(
            f"no evidence source {source_id!r} in fixture {fixture_id!r}"
        )


class FakeWorkflowOrchestrator:
    """Deterministic port fake: drives the state machine, no clinical logic."""

    QUESTION_ID = "q-001"

    def __init__(self, repository: FakeCaseRepository) -> None:
        self._repository = repository
        self.next_verification_passed = True

    # --- helpers ---

    def _event(self, case: AuthLensCase, stage: AgentStage, title: str) -> None:
        case.events.append(
            AgentEvent(
                event_id=f"event-{len(case.events):03d}",
                case_id=case.case_id,
                sequence=len(case.events),
                stage=stage,
                status=EventStatus.COMPLETED,
                title=title,
                occurred_at=_now(),
            )
        )

    def _snapshot(self, case: AuthLensCase, label: str, score: int) -> None:
        met = sum(1 for a in case.assessments if a.status == CriterionStatus.MET)
        missing = sum(1 for a in case.assessments if a.status == CriterionStatus.MISSING)
        case.readiness_history.append(
            ReadinessSummary(
                label=label,
                score=score,
                criteria_met=met,
                criteria_weak=0,
                criteria_missing=missing,
                criteria_conflicting=0,
                criteria_not_applicable=0,
                overall_denial_risk=DenialRisk.HIGH if missing else DenialRisk.LOW,
                computed_at=_now(),
            )
        )

    def _save(self, case: AuthLensCase) -> AuthLensCase:
        case.updated_at = _now()
        return self._repository.save(case)

    # --- WorkflowOrchestrator port ---

    def start_analysis(self, case_id: str) -> AuthLensCase:
        case = self._repository.get(case_id)
        assert case.status == CaseStatus.INTAKE_READY
        case.status = CaseStatus.AWAITING_CLARIFICATION
        case.criteria = [
            PolicyCriterion(
                criterion_id="LM-3",
                policy_id=case.policy.policy_id,
                label="Conservative therapy completed",
                requirement="At least 6 weeks of documented conservative therapy.",
                category="conservative_therapy",
            )
        ]
        case.assessments = [
            CriterionAssessment(
                criterion_id="LM-3",
                status=CriterionStatus.MISSING,
                denial_risk=DenialRisk.HIGH,
                rationale="No documentation of completed conservative therapy was found.",
                clarification_question_id=self.QUESTION_ID,
            )
        ]
        case.clarification_questions = [
            ClarificationQuestion(
                question_id=self.QUESTION_ID,
                criterion_ids=["LM-3"],
                question="Was at least 6 weeks of conservative therapy completed?",
                why_needed="Policy criterion LM-3 requires documented completion.",
                status="open",
            )
        ]
        self._snapshot(case, "initial", 79)
        self._event(case, AgentStage.GAP_DETECTION, "Analysis complete")
        return self._save(case)

    def submit_clarification(
        self, case_id: str, submission: ClarificationSubmission
    ) -> AuthLensCase:
        case = self._repository.get(case_id)
        assert case.status == CaseStatus.AWAITING_CLARIFICATION
        question = next(
            q for q in case.clarification_questions
            if q.question_id == submission.question_id
        )
        question.status = "answered"
        case.clarifications.append(
            ClinicianClarification(
                clarification_id=f"clar-{submission.question_id}",
                question_id=submission.question_id,
                response=submission.response,
                recorded_at=_now(),
            )
        )
        case.assessments[0].status = CriterionStatus.MET
        case.assessments[0].denial_risk = DenialRisk.LOW
        self._snapshot(case, "post_clarification", 93)
        self._event(case, AgentStage.CLARIFICATION, "Clarification recorded")
        return self._save(case)

    def generate_packet(self, case_id: str) -> AuthLensCase:
        case = self._repository.get(case_id)
        assert case.status in (
            CaseStatus.AWAITING_CLARIFICATION,
            CaseStatus.VERIFICATION_FAILED,
        )
        case.status = CaseStatus.PACKET_DRAFTED
        case.disclosure_decisions = [
            DisclosureDecision(
                decision_id="disc-001",
                source_id="note-001",
                item_description="Encounter note",
                decision=DisclosureDecisionType.INCLUDE,
                reason="Directly supports the requested service.",
            ),
            DisclosureDecision(
                decision_id="disc-002",
                source_id="chart-unrelated-001",
                item_description="Unrelated condition history",
                decision=DisclosureDecisionType.EXCLUDE,
                reason="Not relevant to the requested lumbar MRI.",
                phi_category="unrelated_condition",
            ),
        ]
        case.packet = PriorAuthorizationPacket(
            packet_id="packet-001",
            case_id=case.case_id,
            status=PacketStatus.DRAFT,
            sections=[
                PacketSection(
                    section_id="sec-001",
                    title="Clinical summary",
                    body="Documented low back pain with radiculopathy.",
                    claim_ids=["claim-001"],
                )
            ],
            claims=[
                PacketClaim(
                    claim_id="claim-001",
                    text="8 weeks of low back pain radiating down the left leg.",
                    claim_type="clinical",
                    criterion_id="LM-3",
                    evidence_ids=["ev-001"],
                )
            ],
            generated_at=_now(),
        )
        case.verification = None
        self._event(case, AgentStage.PACKET_GENERATION, "Packet drafted")
        return self._save(case)

    def verify_packet(self, case_id: str) -> AuthLensCase:
        case = self._repository.get(case_id)
        assert case.status == CaseStatus.PACKET_DRAFTED and case.packet is not None
        passed = self.next_verification_passed
        issues = []
        if not passed:
            issues.append(
                VerificationIssue(
                    issue_id="issue-001",
                    severity=VerificationSeverity.BLOCKING,
                    claim_id="claim-001",
                    description="Claim excerpt is not verbatim in the cited source.",
                    suggested_resolution="Regenerate the packet.",
                )
            )
        case.verification = VerificationResult(
            verification_id="verif-001",
            packet_id=case.packet.packet_id,
            passed=passed,
            checked_claim_count=len(case.packet.claims),
            issues=issues,
            verified_at=_now(),
        )
        case.status = CaseStatus.VERIFIED if passed else CaseStatus.VERIFICATION_FAILED
        case.packet.status = (
            PacketStatus.VERIFIED if passed else PacketStatus.VERIFICATION_FAILED
        )
        self._event(case, AgentStage.VERIFICATION, "Verification finished")
        return self._save(case)

    def draft_form(self, case_id: str) -> AuthLensCase:
        case = self._repository.get(case_id)
        assert (
            case.status == CaseStatus.VERIFIED
            and case.verification is not None
            and case.verification.passed
        )
        case.status = CaseStatus.READY_FOR_REVIEW
        case.form_draft = PriorAuthorizationFormDraft(
            form_id="form-001",
            case_id=case.case_id,
            packet_id=case.packet.packet_id,
            payer_form_name="Acme Health Prior Authorization Request (MOCK)",
            fields=[
                FormDraftField(
                    field_id="field-001",
                    label="Clinical indication",
                    value="Low back pain with left leg radiation",
                    source_claim_ids=["claim-001"],
                )
            ],
            attestation=(
                "Draft for clinician review only. Nothing has been submitted. "
                "Readiness is not a guarantee of payer approval."
            ),
            generated_at=_now(),
        )
        self._event(case, AgentStage.FORM_DRAFTING, "Mock form drafted")
        return self._save(case)

    def get_case(self, case_id: str) -> AuthLensCase:
        return self._repository.get(case_id)

    def get_events(self, case_id: str):
        return sorted(self._repository.get(case_id).events, key=lambda e: e.sequence)


# --- Fixtures ---------------------------------------------------------------


@pytest.fixture
def fake_repository() -> FakeCaseRepository:
    return FakeCaseRepository()


@pytest.fixture
def fake_fixtures() -> FakeFixtureProvider:
    return FakeFixtureProvider()


@pytest.fixture
def fake_orchestrator(fake_repository) -> FakeWorkflowOrchestrator:
    return FakeWorkflowOrchestrator(fake_repository)


@pytest.fixture
def app(fake_repository, fake_fixtures, fake_orchestrator):
    return create_app(
        case_repository=fake_repository,
        fixture_provider=fake_fixtures,
        workflow_orchestrator=fake_orchestrator,
        cors_origins=["http://allowed.example"],
        seed_demo_on_startup=False,
    )


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


# --- Shared helpers ---------------------------------------------------------

ERROR_KEYS = {"error_code", "message", "detail", "case_id"}


def assert_api_error(response, status_code: int, error_code: str) -> dict:
    assert response.status_code == status_code, response.text
    body = response.json()
    assert set(body) == ERROR_KEYS, f"non-standard error shape: {body}"
    assert body["error_code"] == error_code
    assert isinstance(body["message"], str) and body["message"]
    return body


def create_case(client) -> str:
    response = client.post("/api/cases", json={"fixture_id": DEMO_FIXTURE_ID})
    assert response.status_code == 201, response.text
    return response.json()["case_id"]


def advance(client, case_id: str, target: CaseStatus) -> dict:
    """Drive a case along the happy path to the target status."""
    order = [
        CaseStatus.AWAITING_CLARIFICATION,
        CaseStatus.PACKET_DRAFTED,
        CaseStatus.VERIFIED,
        CaseStatus.READY_FOR_REVIEW,
    ]
    steps = {
        CaseStatus.AWAITING_CLARIFICATION: ("run", None),
        CaseStatus.PACKET_DRAFTED: ("generate-packet", None),
        CaseStatus.VERIFIED: ("verify", None),
        CaseStatus.READY_FOR_REVIEW: ("form-draft", None),
    }
    body = None
    for status in order[: order.index(target) + 1]:
        path, payload = steps[status]
        response = client.post(f"/api/cases/{case_id}/{path}", json=payload)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == status.value
    return body
