"""Optional live integration test against the real Anthropic API.

Skipped unless BOTH are set:
- ANTHROPIC_API_KEY   (a real key)
- AUTHLENS_RUN_LIVE_LLM_TESTS=1   (explicit opt-in; never runs in CI by default)
"""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel, ConfigDict

from app.providers import AnthropicLLMProvider, LLMProviderConfig, ValidationStatus

_live_enabled = bool(os.environ.get("ANTHROPIC_API_KEY")) and os.environ.get(
    "AUTHLENS_RUN_LIVE_LLM_TESTS"
) == "1"

pytestmark = pytest.mark.skipif(
    not _live_enabled,
    reason="live LLM test needs ANTHROPIC_API_KEY and AUTHLENS_RUN_LIVE_LLM_TESTS=1",
)


class _Echo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    word: str


def test_live_structured_roundtrip():
    provider = AnthropicLLMProvider(LLMProviderConfig.from_env())
    result = provider.complete_structured(
        system="You are a test harness. Follow the output instructions exactly.",
        prompt='Return the word "authlens" in the `word` field.',
        output_model=_Echo,
        max_tokens=256,
    )
    assert result.word.lower() == "authlens"
    assert provider.last_response.validation_status is ValidationStatus.VALID
    assert provider.last_response.latency_ms > 0
