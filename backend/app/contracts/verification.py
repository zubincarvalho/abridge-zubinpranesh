"""Packet verification contracts (evaluator side of the evaluator-optimizer loop).

The verifier independently checks every PacketClaim against its cited
evidence and the parsed policy. A packet with any BLOCKING issue fails
verification and cannot reach the form drafter.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.contracts._base import ContractModel


class VerificationSeverity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


class VerificationIssue(ContractModel):
    issue_id: str
    severity: VerificationSeverity
    claim_id: str | None = None
    description: str
    suggested_resolution: str | None = None


class VerificationResult(ContractModel):
    verification_id: str
    packet_id: str
    passed: bool = Field(description="True only when zero BLOCKING issues were found")
    checked_claim_count: int = Field(ge=0)
    issues: list[VerificationIssue] = Field(default_factory=list)
    verified_at: datetime
