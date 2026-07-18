"""Internal policy-parsing models (Agent C).

``ParsedCriterion`` is the service-internal shape: it carries everything the
frozen ``PolicyCriterion`` contract carries plus the exact source location of
the requirement text inside the policy document and the required/conditional
separation. The port boundary returns contract models via ``to_contract``.
"""

from dataclasses import dataclass
from enum import Enum

from app.contracts import PolicyCriterion


class RequirementKind(str, Enum):
    """Whether a criterion always applies or applies only conditionally."""

    REQUIRED = "required"
    CONDITIONAL = "conditional"


@dataclass(frozen=True)
class PolicySourceLocation:
    """Exact location of a criterion inside the source policy text.

    ``start``/``end`` are character offsets into the policy text such that
    ``policy_text[start:end]`` equals the criterion's requirement verbatim.
    """

    heading_line: int
    heading_start: int
    start: int
    end: int


@dataclass(frozen=True)
class ParsedCriterion:
    """One criterion with verbatim requirement text and its source location.

    The parser never decides whether a patient satisfies a criterion — no
    patient data ever enters this service.
    """

    criterion_id: str
    policy_id: str
    label: str
    requirement: str
    category: str
    kind: RequirementKind
    applicability_note: str | None
    location: PolicySourceLocation

    def to_contract(self) -> PolicyCriterion:
        return PolicyCriterion(
            criterion_id=self.criterion_id,
            policy_id=self.policy_id,
            label=self.label,
            requirement=self.requirement,
            category=self.category,
            applicability_note=self.applicability_note,
        )
