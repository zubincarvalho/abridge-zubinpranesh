"""Anthropic implementation of the LLMProvider port.

The only module in AuthLens allowed to import ``anthropic``. Implements the
frozen port in app/ports/llm_provider.py plus the port's hard rules:

- Never logs prompts, completions, chain-of-thought, or the API key —
  only call metadata (model, prompt name/version, latency, attempts,
  validation status, token counts).
- ``complete_structured`` validates against the given contract model,
  retries validation failures a bounded number of times with a sanitized
  error summary, then raises LLMStructuredOutputError.
- Transient failures (network, rate limit, 5xx) are retried with
  exponential backoff up to ``config.max_retries``, then surface as
  LLMTransientError.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.providers.config import LLMProviderConfig
from app.providers.errors import (
    LLMConfigurationError,
    LLMProviderError,
    LLMStructuredOutputError,
    LLMTransientError,
)
from app.providers.response import ProviderResponse, ValidationStatus

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger("authlens.llm")

_STRUCTURED_INSTRUCTIONS = (
    "\n\nRespond with a single JSON object that validates against this JSON Schema. "
    "Output ONLY the JSON object — no prose, no markdown fences, no explanation, "
    "and no reasoning or chain-of-thought:\n{schema}"
)

_REPAIR_INSTRUCTIONS = (
    "\n\nYour previous response did not validate against the schema "
    "(problems: {errors}). Respond again with ONLY a valid JSON object "
    "matching the schema above."
)


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return True
    if isinstance(exc, anthropic.APIStatusError):
        return exc.status_code == 429 or exc.status_code >= 500
    return False


def _extract_json(text: str) -> str:
    """Pull the JSON object out of a completion, tolerating markdown fences."""
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[: -3]
        stripped = stripped.strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise json.JSONDecodeError("no JSON object found", stripped, 0)
    return stripped[start : end + 1]


def _sanitize_validation_errors(exc: ValidationError) -> str:
    """Field paths and error types only — never the offending input values."""
    parts = []
    for err in exc.errors(include_input=False, include_url=False):
        loc = ".".join(str(p) for p in err.get("loc", ())) or "<root>"
        parts.append(f"{loc}: {err.get('type', 'invalid')}")
    return "; ".join(parts[:10])


class AnthropicLLMProvider:
    """Synchronous Anthropic-backed LLMProvider."""

    def __init__(
        self,
        config: LLMProviderConfig | None = None,
        *,
        client: Any | None = None,
        sleep: Callable[[float], None] = time.sleep,
        backoff_base_seconds: float = 1.0,
    ) -> None:
        self._config = config or LLMProviderConfig.from_env()
        self._sleep = sleep
        self._backoff_base = backoff_base_seconds
        self.last_response: ProviderResponse | None = None

        if client is not None:
            self._client = client
        else:
            if not self._config.api_key:
                raise LLMConfigurationError(
                    "ANTHROPIC_API_KEY is not configured; set it in the environment "
                    "or enable DEMO_MODE to use the mock provider."
                )
            self._client = anthropic.Anthropic(
                api_key=self._config.api_key,
                timeout=self._config.timeout_seconds,
                max_retries=0,  # retries are handled here so they are observable
            )

    # ------------------------------------------------------------------ port

    def complete(
        self,
        *,
        system: str,
        prompt: str,
        max_tokens: int | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
    ) -> str:
        started = time.monotonic()
        message, attempts = self._call_with_transient_retries(
            system=system, prompt=prompt, max_tokens=max_tokens
        )
        text = self._message_text(message)
        self._record(
            message,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            latency_ms=(time.monotonic() - started) * 1000,
            attempts=attempts,
            validation_status=ValidationStatus.NOT_APPLICABLE,
        )
        return text

    def complete_structured(
        self,
        *,
        system: str,
        prompt: str,
        output_model: type[T],
        max_tokens: int | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
    ) -> T:
        started = time.monotonic()
        schema = json.dumps(output_model.model_json_schema())
        base_prompt = prompt + _STRUCTURED_INSTRUCTIONS.format(schema=schema)

        current_prompt = base_prompt
        total_attempts = 0
        last_error_summary = "unknown"
        max_validation_attempts = self._config.max_retries + 1

        for _ in range(max_validation_attempts):
            message, attempts = self._call_with_transient_retries(
                system=system, prompt=current_prompt, max_tokens=max_tokens
            )
            total_attempts += attempts
            text = self._message_text(message)
            try:
                payload = json.loads(_extract_json(text))
                result = output_model.model_validate(payload)
            except json.JSONDecodeError:
                last_error_summary = "invalid JSON"
            except ValidationError as exc:
                last_error_summary = _sanitize_validation_errors(exc)
            else:
                self._record(
                    message,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    latency_ms=(time.monotonic() - started) * 1000,
                    attempts=total_attempts,
                    validation_status=ValidationStatus.VALID,
                )
                return result
            current_prompt = base_prompt + _REPAIR_INSTRUCTIONS.format(
                errors=last_error_summary
            )

        self._record(
            message,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            latency_ms=(time.monotonic() - started) * 1000,
            attempts=total_attempts,
            validation_status=ValidationStatus.INVALID,
        )
        raise LLMStructuredOutputError(
            f"structured output for {output_model.__name__} failed validation "
            f"after {max_validation_attempts} attempts ({last_error_summary})"
        )

    # ------------------------------------------------------------- internals

    def _call_with_transient_retries(
        self, *, system: str, prompt: str, max_tokens: int | None
    ) -> tuple[Any, int]:
        """Return (message, attempts). Raises LLMTransientError / LLMProviderError."""
        attempts = 0
        last_exc: Exception | None = None
        for attempt in range(self._config.max_retries + 1):
            attempts += 1
            try:
                message = self._client.messages.create(
                    model=self._config.model,
                    max_tokens=max_tokens or self._config.max_tokens,
                    system=system,
                    messages=[{"role": "user", "content": prompt}],
                )
                return message, attempts
            except anthropic.APIError as exc:
                if not _is_transient(exc):
                    raise LLMProviderError(
                        f"non-retryable Anthropic API error: {type(exc).__name__}"
                    ) from exc
                last_exc = exc
                if attempt < self._config.max_retries:
                    delay = self._backoff_base * (2**attempt)
                    logger.info(
                        "llm_retry model=%s attempt=%d delay_s=%.1f error=%s",
                        self._config.model,
                        attempts,
                        delay,
                        type(exc).__name__,
                    )
                    self._sleep(delay)
        raise LLMTransientError(
            f"transient Anthropic API failure persisted after {attempts} attempts "
            f"({type(last_exc).__name__ if last_exc else 'unknown'})"
        ) from last_exc

    @staticmethod
    def _message_text(message: Any) -> str:
        parts = [
            block.text
            for block in getattr(message, "content", [])
            if getattr(block, "type", None) == "text"
        ]
        return "".join(parts)

    def _record(
        self,
        message: Any,
        *,
        prompt_name: str | None,
        prompt_version: str | None,
        latency_ms: float,
        attempts: int,
        validation_status: ValidationStatus,
    ) -> None:
        usage = getattr(message, "usage", None)
        response = ProviderResponse(
            model=getattr(message, "model", None) or self._config.model,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            latency_ms=latency_ms,
            attempts=attempts,
            validation_status=validation_status,
            stop_reason=getattr(message, "stop_reason", None),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )
        self.last_response = response
        # Metadata only — never prompt/completion text or the API key.
        logger.info(
            "llm_call model=%s prompt=%s version=%s latency_ms=%.0f attempts=%d "
            "validation=%s stop_reason=%s input_tokens=%s output_tokens=%s",
            response.model,
            response.prompt_name,
            response.prompt_version,
            response.latency_ms,
            response.attempts,
            response.validation_status.value,
            response.stop_reason,
            response.input_tokens,
            response.output_tokens,
        )
