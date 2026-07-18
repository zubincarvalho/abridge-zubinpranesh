"""AnthropicLLMProvider: structured validation, malformed-output failure,
transient retries, missing-key behavior, response metadata, log hygiene."""

from __future__ import annotations

import json
import logging

import anthropic
import httpx
import pytest

from app.providers import (
    AnthropicLLMProvider,
    LLMConfigurationError,
    LLMProviderConfig,
    LLMProviderError,
    LLMStructuredOutputError,
    LLMTransientError,
    ValidationStatus,
)
from tests.providers.conftest import SampleOutput, StubClient


def _connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=httpx.Request("POST", "https://api.test"))


def _status_error(status_code: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://api.test")
    response = httpx.Response(status_code, request=request)
    return anthropic.APIStatusError("boom", response=response, body=None)


def _provider(config, script):
    return AnthropicLLMProvider(config, client=StubClient(script), sleep=lambda s: None)


def test_complete_returns_text_and_passes_through_prompts(provider_config):
    provider = _provider(provider_config, ["plain answer"])
    result = provider.complete(system="sys instructions", prompt="user prompt")
    assert result == "plain answer"

    request = provider._client.messages.requests[0]
    assert request["system"] == "sys instructions"
    assert request["messages"] == [{"role": "user", "content": "user prompt"}]
    assert request["model"] == provider_config.model
    assert request["max_tokens"] == provider_config.max_tokens


def test_structured_output_valid_json_is_validated(provider_config):
    payload = json.dumps({"label": "ok", "score": 7})
    provider = _provider(provider_config, [payload])
    result = provider.complete_structured(
        system="s", prompt="p", output_model=SampleOutput
    )
    assert result == SampleOutput(label="ok", score=7)
    assert provider.last_response.validation_status is ValidationStatus.VALID


def test_structured_output_tolerates_markdown_fences(provider_config):
    fenced = "```json\n" + json.dumps({"label": "ok", "score": 1}) + "\n```"
    provider = _provider(provider_config, [fenced])
    result = provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)
    assert result.label == "ok"


def test_structured_output_retries_validation_then_succeeds(provider_config):
    good = json.dumps({"label": "fixed", "score": 3})
    provider = _provider(provider_config, ["not json at all", good])
    result = provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)
    assert result.label == "fixed"
    # Second request carries a repair instruction, not clinical content.
    second_prompt = provider._client.messages.requests[1]["messages"][0]["content"]
    assert "did not validate" in second_prompt


def test_structured_output_fails_clearly_after_bounded_retries(provider_config):
    provider = _provider(provider_config, ["garbage", "{bad", "still bad"])
    with pytest.raises(LLMStructuredOutputError) as excinfo:
        provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)
    assert "SampleOutput" in str(excinfo.value)
    assert provider.last_response.validation_status is ValidationStatus.INVALID
    # max_retries=2 -> exactly 3 validation attempts, no more.
    assert len(provider._client.messages.requests) == 3


def test_schema_mismatch_error_is_sanitized(provider_config):
    wrong = json.dumps({"label": "ok", "score": "SENSITIVE-VALUE"})
    provider = _provider(provider_config, [wrong] * 3)
    with pytest.raises(LLMStructuredOutputError) as excinfo:
        provider.complete_structured(system="s", prompt="p", output_model=SampleOutput)
    message = str(excinfo.value)
    assert "score" in message  # field path is fine
    assert "SENSITIVE-VALUE" not in message  # offending value is not


def test_transient_errors_are_retried_then_succeed(provider_config):
    provider = _provider(
        provider_config, [_connection_error(), _status_error(529), "recovered"]
    )
    assert provider.complete(system="s", prompt="p") == "recovered"
    assert provider.last_response.attempts == 3


def test_transient_errors_exhaust_into_llm_transient_error(provider_config):
    provider = _provider(
        provider_config, [_status_error(500), _status_error(500), _status_error(500)]
    )
    with pytest.raises(LLMTransientError):
        provider.complete(system="s", prompt="p")


def test_non_retryable_api_error_is_not_retried(provider_config):
    provider = _provider(provider_config, [_status_error(400)])
    with pytest.raises(LLMProviderError):
        provider.complete(system="s", prompt="p")
    assert len(provider._client.messages.requests) == 1


def test_missing_api_key_raises_configuration_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(LLMConfigurationError):
        AnthropicLLMProvider(LLMProviderConfig(api_key=None))


def test_response_metadata_records_model_prompt_latency_and_status(provider_config):
    provider = _provider(provider_config, ["hello"])
    provider.complete(
        system="s", prompt="p", prompt_name="gap_detection", prompt_version="v1"
    )
    meta = provider.last_response
    assert meta.model == "claude-opus-4-8"
    assert meta.prompt_name == "gap_detection"
    assert meta.prompt_version == "v1"
    assert meta.latency_ms >= 0
    assert meta.attempts == 1
    assert meta.validation_status is ValidationStatus.NOT_APPLICABLE
    assert meta.input_tokens == 10 and meta.output_tokens == 5


def test_logs_carry_metadata_but_never_key_prompt_or_completion(
    provider_config, caplog
):
    secret_prompt = "PATIENT-NOTE-CONTENT lumbar MRI"
    secret_system = "SYSTEM-RULES-TEXT"
    completion = "COMPLETION-CLINICAL-TEXT"
    provider = _provider(provider_config, [_status_error(500), completion])
    with caplog.at_level(logging.DEBUG, logger="authlens.llm"):
        provider.complete(
            system=secret_system,
            prompt=secret_prompt,
            prompt_name="packet_generation",
            prompt_version="v1",
        )
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert logged  # metadata was logged (retry line + call line)
    assert "packet_generation" in logged
    for forbidden in (provider_config.api_key, secret_prompt, secret_system, completion):
        assert forbidden not in logged
