"""API-layer response models that extend (never alter) the frozen contracts."""

from typing import Literal

from app.contracts import HealthResponse


class HealthDetailsResponse(HealthResponse):
    """Liveness payload plus non-secret runtime details.

    ``provider_mode`` reports whether the LLM runtime would run against the
    live Anthropic API or the deterministic mock (``DEMO_MODE``). It carries
    no key material and never indicates whether a key is present.
    """

    provider_mode: Literal["live", "deterministic"]
