"""Prior authorization packet contracts.

The packet is a focused, source-grounded draft. Every clinical or policy
statement in it is a PacketClaim linked to cited evidence, so the verifier
and the frontend can check and display provenance claim-by-claim.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.contracts._base import ContractModel


class PacketStatus(str, Enum):
    DRAFT = "draft"
    VERIFIED = "verified"
    VERIFICATION_FAILED = "verification_failed"


class ClaimType(str, Enum):
    CLINICAL = "clinical"
    POLICY = "policy"


class PacketClaim(ContractModel):
    """One checkable statement in the packet, linked to its evidence."""

    claim_id: str
    text: str
    claim_type: ClaimType
    criterion_id: str | None = None
    evidence_ids: list[str] = Field(
        default_factory=list,
        description="EvidenceItem ids supporting this claim; clinical claims require at least one",
    )


class PacketSection(ContractModel):
    section_id: str
    title: str
    body: str
    claim_ids: list[str] = Field(default_factory=list)


class PriorAuthorizationPacket(ContractModel):
    """A draft prior authorization packet. Never submitted anywhere.

    Only content with an INCLUDE disclosure decision may appear here.
    """

    packet_id: str
    case_id: str
    status: PacketStatus = PacketStatus.DRAFT
    sections: list[PacketSection] = Field(default_factory=list)
    claims: list[PacketClaim] = Field(default_factory=list)
    generated_at: datetime
