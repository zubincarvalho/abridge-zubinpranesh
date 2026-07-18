"""AuthLens stable contracts (FROZEN after the foundation phase).

Import from this package, e.g. ``from app.contracts import AuthLensCase``.
Changes require an integration-agent review; parallel agents document
requested changes in their agent report instead of editing these files.
"""

from app.contracts.api import (
    ApiError,
    ClarificationSubmission,
    CreateCaseRequest,
    DemoResetResponse,
    EvidenceSourceResponse,
    HealthResponse,
)
from app.contracts.assessment import (
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    ReadinessSummary,
)
from app.contracts.case import (
    ALLOWED_TRANSITIONS,
    AuthLensCase,
    CaseStatus,
    ChartItem,
    EncounterNote,
    EncounterTranscript,
    PatientSummary,
    RequestedService,
    can_transition,
)
from app.contracts.disclosure import DisclosureDecision, DisclosureDecisionType
from app.contracts.events import AgentEvent, AgentStage, EventStatus
from app.contracts.evidence import (
    EvidenceCandidate,
    EvidenceConfidence,
    EvidenceItem,
    EvidenceSource,
    SourceType,
    TextSpan,
)
from app.contracts.form_draft import FormDraftField, PriorAuthorizationFormDraft
from app.contracts.packet import (
    ClaimType,
    PacketClaim,
    PacketSection,
    PacketStatus,
    PriorAuthorizationPacket,
)
from app.contracts.policy import PayerPolicy, PolicyCriterion
from app.contracts.verification import (
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "AgentEvent",
    "AgentStage",
    "ApiError",
    "AuthLensCase",
    "CaseStatus",
    "ChartItem",
    "ClaimType",
    "ClarificationQuestion",
    "ClarificationSubmission",
    "ClinicianClarification",
    "CreateCaseRequest",
    "CriterionAssessment",
    "CriterionStatus",
    "DemoResetResponse",
    "DenialRisk",
    "DisclosureDecision",
    "DisclosureDecisionType",
    "EncounterNote",
    "EncounterTranscript",
    "EventStatus",
    "EvidenceCandidate",
    "EvidenceConfidence",
    "EvidenceItem",
    "EvidenceSource",
    "EvidenceSourceResponse",
    "FormDraftField",
    "HealthResponse",
    "PacketClaim",
    "PacketSection",
    "PacketStatus",
    "PatientSummary",
    "PayerPolicy",
    "PolicyCriterion",
    "PriorAuthorizationFormDraft",
    "PriorAuthorizationPacket",
    "ReadinessSummary",
    "RequestedService",
    "SourceType",
    "TextSpan",
    "VerificationIssue",
    "VerificationResult",
    "VerificationSeverity",
    "can_transition",
]
