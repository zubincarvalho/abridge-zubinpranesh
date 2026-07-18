"""Provider selection.

DEMO_MODE=true (or a config with demo_mode set) yields the deterministic
mock provider so the demo never depends on network access or a real key.
"""

from __future__ import annotations

from app.ports import LLMProvider
from app.providers.anthropic_provider import AnthropicLLMProvider
from app.providers.config import LLMProviderConfig
from app.providers.mock_provider import MockLLMProvider


def build_llm_provider(config: LLMProviderConfig | None = None) -> LLMProvider:
    cfg = config or LLMProviderConfig.from_env()
    if cfg.demo_mode:
        return MockLLMProvider()
    return AnthropicLLMProvider(cfg)
