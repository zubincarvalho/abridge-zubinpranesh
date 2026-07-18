"""Prompt registry: version lookup, metadata completeness, safety-rule
presence in every prompt (never weaken these assertions)."""

from __future__ import annotations

import pytest

from app.prompts import (
    CLINICIAN_REVIEW_NOTICE,
    PROMPT_REGISTRY,
    PromptNotFoundError,
    PromptRegistry,
    PromptTemplate,
    REQUIRED_PROMPT_NAMES,
)


def test_all_six_workflow_prompts_are_registered():
    assert set(REQUIRED_PROMPT_NAMES) == {
        "policy_parsing",
        "evidence_mapping",
        "gap_detection",
        "disclosure_minimization",
        "packet_generation",
        "packet_verification",
    }
    for name in REQUIRED_PROMPT_NAMES:
        template = PROMPT_REGISTRY.get(name)
        assert template.name == name


def test_explicit_version_lookup_and_latest_default():
    pinned = PROMPT_REGISTRY.get("policy_parsing", "v1")
    latest = PROMPT_REGISTRY.get("policy_parsing")
    assert pinned.version == "v1"
    assert latest.version in PROMPT_REGISTRY.versions("policy_parsing")


def test_unknown_prompt_and_unknown_version_raise():
    with pytest.raises(PromptNotFoundError):
        PROMPT_REGISTRY.get("nonexistent_prompt")
    with pytest.raises(PromptNotFoundError):
        PROMPT_REGISTRY.get("policy_parsing", "v999")


def test_latest_resolution_orders_versions_naturally():
    registry = PromptRegistry()
    for version in ("v1", "v2", "v10"):
        registry.register(
            PromptTemplate(
                name="demo",
                version=version,
                description="d",
                permitted_input_types=("str",),
                output_contract="str",
                system="s",
                user_template="{x}",
            )
        )
    assert registry.get("demo").version == "v10"


def test_duplicate_registration_is_rejected():
    registry = PromptRegistry()
    template = PromptTemplate(
        name="demo",
        version="v1",
        description="d",
        permitted_input_types=("str",),
        output_contract="str",
        system="s",
        user_template="{x}",
    )
    registry.register(template)
    with pytest.raises(ValueError):
        registry.register(template)


def test_metadata_is_complete_on_every_prompt():
    for name in REQUIRED_PROMPT_NAMES:
        template = PROMPT_REGISTRY.get(name)
        assert template.version
        assert template.description
        assert template.permitted_input_types
        assert template.output_contract
        assert template.system.strip()
        assert template.user_template.strip()
        assert template.placeholders  # every prompt takes typed inputs


def test_render_user_rejects_placeholder_mismatch():
    template = PROMPT_REGISTRY.get("policy_parsing")
    with pytest.raises(ValueError):
        template.render_user(policy_json="{}")  # policy_text missing
    rendered = template.render_user(policy_json="{}", policy_text="TEXT")
    assert "TEXT" in rendered


def test_every_prompt_carries_the_shared_safety_rules():
    for name in REQUIRED_PROMPT_NAMES:
        system = PROMPT_REGISTRY.get(name).system
        assert "Never invent, extend, or assume payer criteria" in system
        assert "Never diagnose the patient and never recommend treatment" in system
        assert "cite its source" in system
        assert "MISSING evidence" in system and "NEGATIVE evidence" in system
        assert "referral is NEVER proof of completed therapy" in system
        assert "prescription is NEVER proof of treatment failure" in system
        assert "mark" in system.lower() and "uncertainty" in system.lower()
        assert "chain-of-thought" in system  # instructed to withhold it


def test_packet_prompts_require_clinician_review_notice():
    assert CLINICIAN_REVIEW_NOTICE == "Requires clinician review before submission."
    assert CLINICIAN_REVIEW_NOTICE in PROMPT_REGISTRY.get("packet_generation").system
    assert CLINICIAN_REVIEW_NOTICE in PROMPT_REGISTRY.get("packet_verification").system


def test_no_prompt_asks_for_reasoning_or_approval_promises():
    for name in REQUIRED_PROMPT_NAMES:
        system = PROMPT_REGISTRY.get(name).system.lower()
        assert "think step by step" not in system
        assert "show your reasoning" not in system
        assert "guarantee approval" not in system
        assert "will be approved" not in system
