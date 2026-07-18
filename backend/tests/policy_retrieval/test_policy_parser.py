"""Policy parser tests (Agent C).

Covers lumbar MRI extraction, required/conditional separation, verbatim
source citations, the no-invented-requirements guarantee, and the loud
rejection of malformed or unsupported policies.
"""

from __future__ import annotations

import pytest

from app.agents.policy_parser import build_policy_parser
from app.contracts import PayerPolicy, PolicyCriterion
from app.services.policy.errors import (
    DuplicateCriterionError,
    MissingCitationError,
    PolicyParseError,
    UnsupportedPolicyError,
)
from app.services.policy.models import RequirementKind
from app.services.policy.parser import DeterministicPolicyParser
from app.services.policy.routes import CategoryRule, PolicyRoute, PolicyRouter

EXPECTED_CATEGORIES = {
    "LM-1": "indication",
    "LM-2": "duration",
    "LM-3": "conservative_therapy",
    "LM-4": "exam_findings",
    "LM-5": "red_flags",
    "LM-6": "functional_limitation",
    "LM-7": "rationale",
}


def test_lumbar_mri_policy_extraction(criteria: list[PolicyCriterion]) -> None:
    ids = [c.criterion_id for c in criteria]
    assert ids == ["LM-1", "LM-2", "LM-3", "LM-4", "LM-5", "LM-6", "LM-7"]
    assert {c.criterion_id: c.category for c in criteria} == EXPECTED_CATEGORIES
    assert all(c.policy_id == "MHP-IMG-2201" for c in criteria)


def test_no_invented_requirements(
    criteria: list[PolicyCriterion], policy_text: str
) -> None:
    # Exactly one criterion per '### LM-' heading — nothing added, nothing dropped.
    assert len(criteria) == policy_text.count("\n### LM-")
    # Every requirement is verbatim policy text; the parser never paraphrases.
    for criterion in criteria:
        assert criterion.requirement in policy_text


def test_policy_source_citations(
    parser: DeterministicPolicyParser, policy: PayerPolicy, policy_text: str
) -> None:
    # The recorded source span reproduces the requirement text exactly.
    for parsed in parser.parse_detailed(policy, policy_text):
        assert (
            policy_text[parsed.location.start : parsed.location.end]
            == parsed.requirement
        )
        assert parsed.location.heading_line >= 1


def test_required_vs_conditional_demo_all_required(
    parser: DeterministicPolicyParser, policy: PayerPolicy, policy_text: str
) -> None:
    parsed = parser.parse_detailed(policy, policy_text)
    assert all(p.kind is RequirementKind.REQUIRED for p in parsed)
    assert all(p.applicability_note is None for p in parsed)


def test_conditional_criterion_detected_verbatim(
    parser: DeterministicPolicyParser, policy: PayerPolicy
) -> None:
    text = (
        "## Medical-necessity criteria\n\n"
        "### LM-1. Appropriate diagnosis or indication\n"
        "The record documents a clinical indication.\n\n"
        "### LM-2. Conservative therapy duration\n"
        "The patient has documentation of therapy. This applies only when "
        "prior imaging is unavailable.\n"
    )
    parsed = {p.criterion_id: p for p in parser.parse_detailed(policy, text)}
    assert parsed["LM-1"].kind is RequirementKind.REQUIRED
    lm2 = parsed["LM-2"]
    assert lm2.kind is RequirementKind.CONDITIONAL
    # The applicability note is exact policy language, never a paraphrase.
    assert lm2.applicability_note == "This applies only when prior imaging is unavailable."
    assert lm2.applicability_note in lm2.requirement


def test_duplicate_criterion_ids_rejected(policy: PayerPolicy) -> None:
    text = (
        "### LM-1. Appropriate diagnosis or indication\nFirst body.\n\n"
        "### LM-1. Appropriate diagnosis or indication\nDuplicate body.\n"
    )
    with pytest.raises(DuplicateCriterionError):
        build_policy_parser().parse(policy, text)


def test_missing_citation_rejected(policy: PayerPolicy) -> None:
    text = (
        "### LM-1. Appropriate diagnosis or indication\n"
        "### LM-2. Symptom duration\nHas a body.\n"
    )
    with pytest.raises(MissingCitationError):
        build_policy_parser().parse(policy, text)


def test_unmatched_category_refuses_to_guess(policy: PayerPolicy) -> None:
    text = "### LM-9. Astrological alignment check\nSome body text.\n"
    with pytest.raises(PolicyParseError):
        build_policy_parser().parse(policy, text)


def test_criterion_id_outside_route_pattern_rejected(policy: PayerPolicy) -> None:
    text = "### XX-1. Appropriate diagnosis or indication\nSome body text.\n"
    with pytest.raises(PolicyParseError):
        build_policy_parser().parse(policy, text)


def test_unsupported_policy_rejected(policy_text: str) -> None:
    unsupported = PayerPolicy(
        policy_id="UNKNOWN-999",
        payer_name="Nowhere Health (fictional)",
        policy_title="Knee MRI",
        service_description="MRI knee without contrast (CPT 73721)",
        source_document="n/a",
    )
    with pytest.raises(UnsupportedPolicyError):
        build_policy_parser().parse(unsupported, policy_text)


def test_router_is_extensible_without_contract_change(policy_text: str) -> None:
    # A new specialty can be registered without touching contracts or ports.
    knee_route = PolicyRoute(
        route_id="knee_mri",
        policy_ids=("MHP-IMG-3301",),
        service_codes=("73721",),
        criterion_id_pattern=r"KN-\d+",
        category_rules=(CategoryRule("indication", ("diagnosis", "indication")),),
    )
    router = PolicyRouter()
    router.register(knee_route)
    parser = build_policy_parser(router)
    knee_policy = PayerPolicy(
        policy_id="MHP-IMG-3301",
        payer_name="Meridian Health Plans (fictional)",
        policy_title="Knee MRI",
        service_description="MRI knee without contrast (CPT 73721)",
        source_document="n/a",
    )
    text = "### KN-1. Appropriate diagnosis or indication\nKnee indication body.\n"
    parsed = parser.parse(knee_policy, text)
    assert [c.criterion_id for c in parsed] == ["KN-1"]
    assert parsed[0].category == "indication"
