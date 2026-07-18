"""Policy routing registry (Agent C).

Routing selects which parsing configuration applies to a payer policy. The
demo ships exactly one supported route — lumbar spine MRI (MHP-IMG-2201,
CPT 72148). The registry is extensible via ``PolicyRouter.register`` so new
specialties can be added without contract changes, but no unsupported
specialty is ever guessed at: an unmatched policy raises
``UnsupportedPolicyError``.
"""

import re
from dataclasses import dataclass

from app.contracts import PayerPolicy

from app.services.policy.errors import UnsupportedPolicyError


@dataclass(frozen=True)
class CategoryRule:
    """Maps criterion-label keywords to a routing category (first match wins)."""

    category: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class PolicyRoute:
    """Parsing configuration for one supported policy family."""

    route_id: str
    policy_ids: tuple[str, ...]
    service_codes: tuple[str, ...]
    criterion_id_pattern: str
    category_rules: tuple[CategoryRule, ...]

    def category_for(self, label: str) -> str | None:
        lowered = label.lower()
        for rule in self.category_rules:
            if any(keyword in lowered for keyword in rule.keywords):
                return rule.category
        return None

    def matches_criterion_id(self, criterion_id: str) -> bool:
        return re.fullmatch(self.criterion_id_pattern, criterion_id) is not None


LUMBAR_MRI_ROUTE = PolicyRoute(
    route_id="lumbar_mri",
    policy_ids=("MHP-IMG-2201",),
    service_codes=("72148",),
    criterion_id_pattern=r"LM-\d+",
    category_rules=(
        CategoryRule("conservative_therapy", ("conservative",)),
        CategoryRule("duration", ("duration",)),
        CategoryRule("red_flags", ("red-flag", "red flag")),
        CategoryRule("exam_findings", ("examination", "neurologic", "exam finding")),
        CategoryRule("functional_limitation", ("functional",)),
        CategoryRule("rationale", ("rationale",)),
        CategoryRule("indication", ("diagnosis", "indication")),
    ),
)


class PolicyRouter:
    """Resolves a ``PayerPolicy`` to a registered parsing route."""

    def __init__(self, routes: tuple[PolicyRoute, ...] = (LUMBAR_MRI_ROUTE,)) -> None:
        self._routes: list[PolicyRoute] = list(routes)

    def register(self, route: PolicyRoute) -> None:
        """Add a new supported route (extensibility seam; no contract change)."""
        self._routes.append(route)

    def route_for(self, policy: PayerPolicy) -> PolicyRoute:
        for route in self._routes:
            if policy.policy_id in route.policy_ids:
                return route
        for route in self._routes:
            if any(code in policy.service_description for code in route.service_codes):
                return route
        supported = ", ".join(route.route_id for route in self._routes)
        raise UnsupportedPolicyError(
            f"No parsing route registered for policy '{policy.policy_id}' "
            f"({policy.service_description}). Supported routes: {supported}."
        )
