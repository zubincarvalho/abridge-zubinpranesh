"""LLM provider port.

The only place model calls happen. Implementations (Agent B) wrap the
Anthropic Python SDK; no other package may import ``anthropic`` directly.

Rules for implementations:
- Never log prompts, completions, or chain-of-thought.
- Structured calls validate against the given contract model and retry on
  validation failure (bounded retries, then raise).
- Prompts must instruct source-grounded output; the provider is not
  responsible for grounding, but must pass caller instructions through
  unmodified.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(Protocol):
    def complete(self, *, system: str, prompt: str, max_tokens: int | None = None) -> str:
        """Return a plain-text completion."""
        ...

    def complete_structured(
        self, *, system: str, prompt: str, output_model: type[T], max_tokens: int | None = None
    ) -> T:
        """Return a completion validated against ``output_model``.

        Raises a provider-defined error after bounded validation retries.
        """
        ...
