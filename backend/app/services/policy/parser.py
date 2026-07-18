"""Deterministic ``PolicyParser`` implementation (Agent C).

Converts a payer policy document into typed, discrete criteria while
preserving exact source policy language and source locations.

Hard rules (see docs/SAFETY_AND_HUMAN_REVIEW.md):
- Requirement text is always a verbatim substring of the policy document —
  the parser cannot invent, soften, or reinterpret a requirement.
- The parser never sees patient data and never decides whether a patient
  satisfies a criterion; it only structures the policy.
- Duplicate criterion ids and criteria without citable source text are
  rejected with typed errors.
"""

from app.contracts import PayerPolicy, PolicyCriterion

from app.services.policy.errors import (
    DuplicateCriterionError,
    MissingCitationError,
    PolicyParseError,
)
from app.services.policy.markdown_parser import (
    conditional_sentence,
    extract_criterion_sections,
)
from app.services.policy.models import (
    ParsedCriterion,
    PolicySourceLocation,
    RequirementKind,
)
from app.services.policy.routes import PolicyRouter


class DeterministicPolicyParser:
    """Implements the frozen ``PolicyParser`` port without any model call."""

    def __init__(self, router: PolicyRouter | None = None) -> None:
        self._router = router or PolicyRouter()

    @property
    def router(self) -> PolicyRouter:
        return self._router

    def parse(self, policy: PayerPolicy, policy_text: str) -> list[PolicyCriterion]:
        return [parsed.to_contract() for parsed in self.parse_detailed(policy, policy_text)]

    def parse_detailed(self, policy: PayerPolicy, policy_text: str) -> list[ParsedCriterion]:
        """Parse with source locations and required/conditional separation."""
        route = self._router.route_for(policy)
        sections = extract_criterion_sections(policy_text)
        if not sections:
            raise PolicyParseError(
                f"No criterion sections found in policy '{policy.policy_id}' "
                f"({policy.source_document})."
            )

        parsed: list[ParsedCriterion] = []
        seen_ids: set[str] = set()
        for section in sections:
            if section.criterion_id in seen_ids:
                raise DuplicateCriterionError(
                    f"Criterion id '{section.criterion_id}' is declared more than once "
                    f"in policy '{policy.policy_id}'."
                )
            seen_ids.add(section.criterion_id)

            if not route.matches_criterion_id(section.criterion_id):
                raise PolicyParseError(
                    f"Criterion id '{section.criterion_id}' does not match the "
                    f"'{route.route_id}' route pattern '{route.criterion_id_pattern}'."
                )
            if not section.body:
                raise MissingCitationError(
                    f"Criterion '{section.criterion_id}' has no requirement text to cite "
                    f"(line {section.heading_line})."
                )
            category = route.category_for(section.label)
            if category is None:
                raise PolicyParseError(
                    f"Criterion '{section.criterion_id}' ('{section.label}') matches no "
                    f"category rule on route '{route.route_id}'. Refusing to guess."
                )

            condition = conditional_sentence(section.body)
            parsed.append(
                ParsedCriterion(
                    criterion_id=section.criterion_id,
                    policy_id=policy.policy_id,
                    label=section.label,
                    requirement=section.body,
                    category=category,
                    kind=(
                        RequirementKind.CONDITIONAL
                        if condition is not None
                        else RequirementKind.REQUIRED
                    ),
                    applicability_note=condition,
                    location=PolicySourceLocation(
                        heading_line=section.heading_line,
                        heading_start=section.heading_start,
                        start=section.body_start,
                        end=section.body_end,
                    ),
                )
            )

        for criterion in parsed:
            if policy_text[criterion.location.start : criterion.location.end] != criterion.requirement:
                raise PolicyParseError(
                    f"Internal citation check failed for '{criterion.criterion_id}': "
                    "requirement text does not match its recorded source span."
                )
        return parsed
