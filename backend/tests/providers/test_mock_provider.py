"""MockLLMProvider: determinism, structured validation, factory selection."""

from __future__ import annotations

import pytest

from app.providers import (
    AnthropicLLMProvider,
    LLMProviderConfig,
    LLMStructuredOutputError,
    MockLLMProvider,
    ValidationStatus,
    build_llm_provider,
)
from tests.providers.conftest import SampleOutput


def test_complete_is_deterministic_across_instances():
    a = MockLLMProvider().complete(system="sys", prompt="prompt")
    b = MockLLMProvider().complete(system="sys", prompt="prompt")
    assert a == b
    assert a.startswith("mock-completion:")


def test_complete_varies_with_inputs():
    provider = MockLLMProvider()
    assert provider.complete(system="sys", prompt="one") != provider.complete(
        system="sys", prompt="two"
    )


def test_canned_text_response_takes_priority():
    provider = MockLLMProvider(text_responses={"the prompt": "canned"})
    assert provider.complete(system="s", prompt="the prompt") == "canned"


def test_structured_response_is_validated_through_the_contract():
    provider = MockLLMProvider(
        structured_responses={SampleOutput: {"label": "demo", "score": 42}}
    )
    result = provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)
    assert result == SampleOutput(label="demo", score=42)
    assert provider.last_response.validation_status is ValidationStatus.VALID
    # A single registered payload is reusable — deterministic on every call.
    again = provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)
    assert again == result


def test_structured_response_missing_registration_fails_clearly():
    provider = MockLLMProvider()
    with pytest.raises(LLMStructuredOutputError):
        provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)


def test_invalid_canned_payload_fails_contract_validation():
    provider = MockLLMProvider(structured_responses={SampleOutput: {"label": "x"}})
    with pytest.raises(LLMStructuredOutputError):
        provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)


def test_calls_are_recorded_with_prompt_identity():
    provider = MockLLMProvider()
    provider.complete(system="s", prompt="p", prompt_name="gap_detection", prompt_version="v1")
    assert provider.calls[0]["prompt_name"] == "gap_detection"
    assert provider.calls[0]["prompt_version"] == "v1"


def test_factory_selects_mock_in_demo_mode_and_anthropic_otherwise():
    demo = build_llm_provider(LLMProviderConfig(demo_mode=True))
    assert isinstance(demo, MockLLMProvider)

    real = build_llm_provider(LLMProviderConfig(api_key="sk-test", demo_mode=False))
    assert isinstance(real, AnthropicLLMProvider)
