"""Provider call metadata.

A ProviderResponse records what is safe to observe about an LLM call —
model, prompt identity, latency, attempt counts, validation status, token
usage. It deliberately has no field for prompt text, completion text, or
chain-of-thought (see docs/SAFETY_AND_HUMAN_REVIEW.md rule 9).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ValidationStatus(str, Enum):
    NOT_APPLICABLE = "not_applicable"  # plain-text completion, nothing to validate
    VALID = "valid"
    INVALID = "invalid"  # structured call never validated (error was raised)


@dataclass(frozen=True)
class ProviderResponse:
    model: str
    prompt_name: str | None
    prompt_version: str | None
    latency_ms: float
    attempts: int
    validation_status: ValidationStatus
    stop_reason: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
