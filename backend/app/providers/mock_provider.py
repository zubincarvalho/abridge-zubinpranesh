"""Deterministic mock LLMProvider for tests and DEMO_MODE.

Makes no network calls. Text completions are a stable digest of the inputs
(same inputs → same output, always). Structured completions come from
canned payloads registered per output model; the payload is validated
through the same Pydantic contract the real provider would use.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.providers.errors import LLMStructuredOutputError
from app.providers.response import ProviderResponse, ValidationStatus

T = TypeVar("T", bound=BaseModel)

MOCK_MODEL_NAME = "mock-deterministic"


def _digest(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


class MockLLMProvider:
    """Deterministic LLMProvider implementation.

    ``text_responses`` maps an exact prompt string to a canned completion.
    ``structured_responses`` maps an output model class (or its ``__name__``)
    to either one payload dict or a list of payload dicts consumed in order.
    """

    def __init__(
        self,
        *,
        text_responses: dict[str, str] | None = None,
        structured_responses: dict[Any, Any] | None = None,
    ) -> None:
        self._text_responses = dict(text_responses or {})
        self._structured_responses: dict[str, list[dict]] = {}
        for key, value in (structured_responses or {}).items():
            name = key if isinstance(key, str) else key.__name__
            payloads = value if isinstance(value, list) else [value]
            self._structured_responses[name] = list(payloads)
        self.calls: list[dict[str, Any]] = []
        self.last_response: ProviderResponse | None = None

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
        text = self._text_responses.get(prompt) or f"mock-completion:{_digest(system, prompt)}"
        self._record_call("complete", system, prompt, prompt_name, prompt_version)
        self._record_response(
            prompt_name, prompt_version, started, ValidationStatus.NOT_APPLICABLE
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
        self._record_call("complete_structured", system, prompt, prompt_name, prompt_version)
        queue = self._structured_responses.get(output_model.__name__)
        if not queue:
            self._record_response(prompt_name, prompt_version, started, ValidationStatus.INVALID)
            raise LLMStructuredOutputError(
                f"MockLLMProvider has no canned payload registered for "
                f"{output_model.__name__}"
            )
        payload = queue[0] if len(queue) == 1 else queue.pop(0)
        try:
            result = output_model.model_validate(payload)
        except ValidationError as exc:
            self._record_response(prompt_name, prompt_version, started, ValidationStatus.INVALID)
            raise LLMStructuredOutputError(
                f"canned payload for {output_model.__name__} failed contract validation"
            ) from exc
        self._record_response(prompt_name, prompt_version, started, ValidationStatus.VALID)
        return result

    def _record_call(
        self,
        method: str,
        system: str,
        prompt: str,
        prompt_name: str | None,
        prompt_version: str | None,
    ) -> None:
        self.calls.append(
            {
                "method": method,
                "system": system,
                "prompt": prompt,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
            }
        )

    def _record_response(
        self,
        prompt_name: str | None,
        prompt_version: str | None,
        started: float,
        status: ValidationStatus,
    ) -> None:
        self.last_response = ProviderResponse(
            model=MOCK_MODEL_NAME,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            latency_ms=(time.monotonic() - started) * 1000,
            attempts=1,
            validation_status=status,
        )
