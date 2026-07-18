"""Shared fixtures for provider tests: a stub Anthropic client and a small
output contract. No test in this directory makes a network call."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import BaseModel, ConfigDict

from app.providers.config import LLMProviderConfig


class SampleOutput(BaseModel):
    """Stand-in structured-output contract for provider tests."""

    model_config = ConfigDict(extra="forbid")

    label: str
    score: int


def make_message(text: str, *, model: str = "claude-opus-4-8") -> SimpleNamespace:
    """Build an object shaped like an Anthropic Message response."""
    return SimpleNamespace(
        content=[SimpleNamespace(type="text", text=text)],
        model=model,
        stop_reason="end_turn",
        usage=SimpleNamespace(input_tokens=10, output_tokens=5),
    )


class StubMessages:
    """Scripted messages.create: each queued item is a response text or an
    exception instance to raise. Records every request payload."""

    def __init__(self, script: list) -> None:
        self.script = list(script)
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.script:
            raise AssertionError("StubMessages script exhausted")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return make_message(item)


class StubClient:
    def __init__(self, script: list) -> None:
        self.messages = StubMessages(script)


@pytest.fixture
def provider_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        api_key="sk-test-not-a-real-key",
        model="claude-opus-4-8",
        timeout_seconds=5.0,
        max_retries=2,
        max_tokens=1024,
    )
