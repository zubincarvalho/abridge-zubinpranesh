"""Mock payer form draft contracts.

The form drafter populates a MOCK payer form from a VERIFIED packet only.
It never accepts unverified free-form clinical text, and the draft is the
terminal artifact: the case stops at 'Ready for Clinician Review'.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.contracts._base import ContractModel


class FormDraftField(ContractModel):
    field_id: str
    label: str
    value: str
    source_claim_ids: list[str] = Field(
        default_factory=list,
        description="PacketClaim ids the value was drawn from (empty only for administrative fields)",
    )


class PriorAuthorizationFormDraft(ContractModel):
    form_id: str
    case_id: str
    packet_id: str = Field(description="Must reference a packet with status 'verified'")
    payer_form_name: str
    fields: list[FormDraftField] = Field(default_factory=list)
    attestation: str = Field(
        description="Fixed reviewer-facing notice: draft for clinician review; not submitted; no approval guarantee"
    )
    status: Literal["ready_for_review"] = "ready_for_review"
    generated_at: datetime
