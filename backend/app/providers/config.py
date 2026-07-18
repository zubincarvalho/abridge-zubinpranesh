"""Environment-driven configuration for the LLM provider layer.

Reads the un-prefixed environment variables named in the runtime contract
(ANTHROPIC_API_KEY, ANTHROPIC_MODEL, DEMO_MODE, ...) without touching the
frozen application settings in ``app/config.py``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_MODEL = "claude-opus-4-8"
DEFAULT_MAX_TOKENS = 16000
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_RETRIES = 2

_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


@dataclass(frozen=True)
class LLMProviderConfig:
    """Immutable provider configuration.

    ``max_retries`` bounds both transient-failure retries and structured
    output validation retries (each loop makes at most ``max_retries + 1``
    attempts).
    """

    api_key: str | None = None
    model: str = DEFAULT_MODEL
    demo_mode: bool = False
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    max_tokens: int = DEFAULT_MAX_TOKENS

    @classmethod
    def from_env(cls) -> "LLMProviderConfig":
        return cls(
            api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_MODEL),
            demo_mode=_env_bool("DEMO_MODE"),
            timeout_seconds=float(
                os.environ.get("ANTHROPIC_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            ),
            max_retries=int(os.environ.get("ANTHROPIC_MAX_RETRIES", DEFAULT_MAX_RETRIES)),
            max_tokens=int(os.environ.get("ANTHROPIC_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        )
