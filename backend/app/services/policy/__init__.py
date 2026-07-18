"""Policy parsing service (Agent C — owned subtree).

Deterministic conversion of payer policy documents into typed criteria with
verbatim requirement text, exact source locations, and required/conditional
separation. Implements the frozen ``PolicyParser`` port.
"""

from app.services.policy.errors import (
    DuplicateCriterionError,
    MissingCitationError,
    PolicyParseError,
    UnsupportedPolicyError,
)
from app.services.policy.models import (
    ParsedCriterion,
    PolicySourceLocation,
    RequirementKind,
)
from app.services.policy.parser import DeterministicPolicyParser
from app.services.policy.routes import (
    LUMBAR_MRI_ROUTE,
    CategoryRule,
    PolicyRoute,
    PolicyRouter,
)

__all__ = [
    "CategoryRule",
    "DeterministicPolicyParser",
    "DuplicateCriterionError",
    "LUMBAR_MRI_ROUTE",
    "MissingCitationError",
    "ParsedCriterion",
    "PolicyParseError",
    "PolicyRoute",
    "PolicyRouter",
    "PolicySourceLocation",
    "RequirementKind",
    "UnsupportedPolicyError",
]
