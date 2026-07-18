"""Disclosure (minimum-necessary) contracts.

Every candidate piece of patient information gets an explicit include/exclude
decision before packet generation. Unrelated PHI must be excluded with a
stated reason. The frontend renders these in the Disclosure Review panel.
"""

from enum import Enum

from pydantic import Field

from app.contracts._base import ContractModel


class DisclosureDecisionType(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


class DisclosureDecision(ContractModel):
    decision_id: str
    source_id: str = Field(description="Evidence source or chart item the decision applies to")
    item_description: str
    decision: DisclosureDecisionType
    reason: str = Field(
        description="Why this item is (ir)relevant to the requested service; required for both decisions"
    )
    phi_category: str | None = Field(
        default=None, description="Optional PHI category label, e.g. 'behavioral_health', 'unrelated_condition'"
    )
