"""AuthLens case aggregate and case state machine.

AuthLensCase is the single response shape the frontend renders from — every
console panel maps to a field on it (see docs/FRONTEND_HANDOFF.md). The
state machine below is authoritative: there is deliberately NO 'submitted'
state and no transition out of READY_FOR_REVIEW.
"""

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import Field

from app.contracts._base import ContractModel
from app.contracts.assessment import (
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    ReadinessSummary,
)
from app.contracts.disclosure import DisclosureDecision
from app.contracts.events import AgentEvent
from app.contracts.form_draft import PriorAuthorizationFormDraft
from app.contracts.packet import PriorAuthorizationPacket
from app.contracts.policy import PayerPolicy, PolicyCriterion
from app.contracts.verification import VerificationResult


class CaseStatus(str, Enum):
    DRAFT = "draft"
    INTAKE_READY = "intake_ready"
    ANALYZING = "analyzing"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    REANALYZING = "reanalyzing"
    PACKET_DRAFTED = "packet_drafted"
    VERIFICATION_FAILED = "verification_failed"
    VERIFIED = "verified"
    READY_FOR_REVIEW = "ready_for_review"


# Authoritative transition table. READY_FOR_REVIEW is terminal; the only way
# past it is a human acting outside AuthLens. There is no 'submitted' state.
ALLOWED_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.DRAFT: frozenset({CaseStatus.INTAKE_READY}),
    CaseStatus.INTAKE_READY: frozenset({CaseStatus.ANALYZING}),
    CaseStatus.ANALYZING: frozenset({CaseStatus.AWAITING_CLARIFICATION}),
    CaseStatus.AWAITING_CLARIFICATION: frozenset(
        {CaseStatus.REANALYZING, CaseStatus.PACKET_DRAFTED}
    ),
    CaseStatus.REANALYZING: frozenset({CaseStatus.AWAITING_CLARIFICATION}),
    CaseStatus.PACKET_DRAFTED: frozenset(
        {CaseStatus.VERIFIED, CaseStatus.VERIFICATION_FAILED}
    ),
    CaseStatus.VERIFICATION_FAILED: frozenset({CaseStatus.PACKET_DRAFTED}),
    CaseStatus.VERIFIED: frozenset({CaseStatus.READY_FOR_REVIEW}),
    CaseStatus.READY_FOR_REVIEW: frozenset(),
}


def can_transition(current: CaseStatus, target: CaseStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


class ChartItem(ContractModel):
    """One structured chart entry, addressable as an evidence source."""

    source_id: str
    category: Literal[
        "condition", "medication", "procedure", "referral", "observation", "service_request", "other"
    ]
    display: str
    detail: str | None = None


class PatientSummary(ContractModel):
    """Minimum-necessary patient context for the Patient Chart panel."""

    patient_id: str
    display_name: str
    birth_date: str = Field(description="ISO date, e.g. 1978-03-14 (synthetic)")
    sex: Literal["female", "male", "other", "unknown"]
    chart_items: list[ChartItem] = Field(default_factory=list)


class RequestedService(ContractModel):
    service_name: str
    code: str = Field(description="Procedure code, e.g. CPT 72148")
    code_system: str = "CPT"
    modality: str | None = None
    body_site: str | None = None


class EncounterNote(ContractModel):
    """The Abridge-style encounter note (an addressable evidence source)."""

    source_id: str
    title: str
    text: str


class EncounterTranscript(ContractModel):
    source_id: str
    text: str


class AuthLensCase(ContractModel):
    """The full case state. GET /api/cases/{case_id} returns exactly this."""

    case_id: str
    status: CaseStatus
    created_at: datetime
    updated_at: datetime
    synthetic: bool = Field(
        default=True, description="True for demo cases built from hackathon-authored synthetic data"
    )

    # --- Intake inputs ---
    patient: PatientSummary
    requested_service: RequestedService
    clinical_indication: str
    indication_codes: list[str] = Field(
        default_factory=list, description="ICD-10 codes for the stated indication (not a diagnosis by AuthLens)"
    )
    encounter_note: EncounterNote
    encounter_transcript: EncounterTranscript | None = None
    policy: PayerPolicy

    # --- Analysis artifacts ---
    criteria: list[PolicyCriterion] = Field(default_factory=list)
    assessments: list[CriterionAssessment] = Field(default_factory=list)
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    clarifications: list[ClinicianClarification] = Field(default_factory=list)
    readiness_history: list[ReadinessSummary] = Field(
        default_factory=list,
        description="Ordered snapshots; first is the 'before' score, last is the current score",
    )

    # --- Output pipeline artifacts ---
    disclosure_decisions: list[DisclosureDecision] = Field(default_factory=list)
    packet: PriorAuthorizationPacket | None = None
    verification: VerificationResult | None = None
    form_draft: PriorAuthorizationFormDraft | None = None

    # --- Timeline ---
    events: list[AgentEvent] = Field(default_factory=list)
