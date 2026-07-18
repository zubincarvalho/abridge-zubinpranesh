"""Payer policy contracts.

A payer medical-necessity policy is parsed into discrete PolicyCriterion
records. Criteria are the unit of assessment for the readiness matrix.
"""

from pydantic import Field

from app.contracts._base import ContractModel


class PayerPolicy(ContractModel):
    """A payer medical-necessity policy document (synthetic in the demo)."""

    policy_id: str
    payer_name: str
    policy_title: str
    service_description: str
    source_document: str = Field(
        description="Repo-relative path or label of the policy text, e.g. data/policies/lumbar_mri_policy.md"
    )
    synthetic: bool = Field(
        default=True,
        description="True for hackathon-authored synthetic policies. The demo policy is always synthetic.",
    )


class PolicyCriterion(ContractModel):
    """One discrete medical-necessity criterion parsed from a policy."""

    criterion_id: str
    policy_id: str
    label: str = Field(description="Short display label, e.g. 'Conservative therapy completed and failed'")
    requirement: str = Field(description="Full requirement text as parsed from the policy")
    category: str = Field(
        description="Routing category, e.g. 'indication', 'duration', 'conservative_therapy', "
        "'exam_findings', 'red_flags', 'functional_limitation', 'rationale'"
    )
    applicability_note: str | None = None
