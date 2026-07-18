"""Typed errors raised by LLM provider implementations.

Callers (stage services) catch these instead of SDK exception types so the
Anthropic SDK never leaks across the LLMProvider port boundary.
"""


class LLMProviderError(Exception):
    """Base class for all provider failures."""


class LLMConfigurationError(LLMProviderError):
    """The provider cannot start (e.g. no API key configured)."""


class LLMTransientError(LLMProviderError):
    """A retryable failure (network, rate limit, 5xx) persisted past max retries."""


class LLMStructuredOutputError(LLMProviderError):
    """The model never produced output validating against the contract.

    Raised only after the bounded validation retries are exhausted. The
    message contains a sanitized error summary (error types and field
    paths) — never raw model output or clinical content.
    """
