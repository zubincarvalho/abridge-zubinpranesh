"""Evidence contracts: sources, retrieved candidates, and cited evidence.

Every clinical claim AuthLens makes must trace to an EvidenceItem, and every
EvidenceItem must quote exact text from a known source. The frontend renders
citations by resolving ``source_id`` via GET /api/cases/{case_id}/evidence/{source_id}
and highlighting ``span`` inside the returned content.
"""

from enum import Enum

from pydantic import Field

from app.contracts._base import ContractModel


class SourceType(str, Enum):
    """Where a piece of evidence came from."""

    ENCOUNTER_NOTE = "encounter_note"
    ENCOUNTER_TRANSCRIPT = "encounter_transcript"
    FHIR_RESOURCE = "fhir_resource"
    CLINICIAN_CLARIFICATION = "clinician_clarification"
    PAYER_POLICY = "payer_policy"


class EvidenceConfidence(str, Enum):
    """How directly the cited text supports the mapped criterion."""

    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class TextSpan(ContractModel):
    """Character offsets into the source content (half-open: [start, end))."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)


class EvidenceSource(ContractModel):
    """A resolvable evidence source the frontend can open in the citation drawer."""

    source_id: str
    source_type: SourceType
    label: str
    content: str
    fhir_resource_type: str | None = None


class EvidenceItem(ContractModel):
    """An exact, cited piece of evidence mapped to a policy criterion.

    ``excerpt`` must be a verbatim quote from the source content. Referrals and
    prescriptions may be cited, but ports must never treat them as proof of
    completed or failed therapy (see docs/SAFETY_AND_HUMAN_REVIEW.md).
    """

    evidence_id: str
    source_id: str
    source_type: SourceType
    excerpt: str
    span: TextSpan | None = None
    fhir_path: str | None = None
    confidence: EvidenceConfidence
    note: str | None = None


class EvidenceCandidate(ContractModel):
    """A retrieval hit that has not yet been accepted as cited evidence."""

    candidate_id: str
    criterion_id: str
    source_id: str
    source_type: SourceType
    excerpt: str
    span: TextSpan | None = None
    fhir_path: str | None = None
    confidence: EvidenceConfidence
    relevance_rationale: str
    accepted: bool | None = None
