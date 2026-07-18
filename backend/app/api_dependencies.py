"""Dependency-injection and composition surface for the AuthLens API.

Routes depend only on the request-scoped getters below; ``app.main.create_app``
binds concrete instances onto ``app.state``. This module is the composition
root: it assembles Agent F's deterministic orchestrator over Agents A–E's
port implementations and resolves the LLM provider mode explicitly.

LLM provider selection (no hidden fallback from live to mock):

- ``deterministic`` (default): the analysis pipeline runs fully in code with
  no network access and no API key. Reproducible; every safety gate is
  deterministic. A ``MockLLMProvider`` is available for any incidental use.
- ``live``: the LLM-capable stages (retrieval refiner, evidence mapper) use a
  real ``AnthropicLLMProvider``; every deterministic gate still re-checks
  their output. Requires ``ANTHROPIC_API_KEY`` — if live is requested without
  a key, startup fails loudly rather than silently downgrading to the mock.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from typing import Literal

from fastapi import Request

from app.api.case_service import CaseService, FixtureSource
from app.config import Settings
from app.contracts import EvidenceSource
from app.ports import CaseRepository, EvidenceMapper, GapDetector, LLMProvider, WorkflowOrchestrator

logger = logging.getLogger("authlens.integration")

CORS_ORIGINS_ENV_VAR = "AUTHLENS_CORS_ORIGINS"
DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://localhost:5173", "http://localhost:5175", "http://localhost:5176")
LLM_MODE_ENV_VAR = "AUTHLENS_LLM_MODE"

ProviderMode = Literal["live", "deterministic"]


class ProviderConfigurationError(RuntimeError):
    """Live LLM mode was requested without an API key; refusing to fall back."""


# --- Default builders (used by create_app when nothing is injected) ---------


def build_default_case_repository() -> CaseRepository:
    from app.repositories.in_memory import InMemoryCaseRepository

    return InMemoryCaseRepository()


def build_default_fixture_provider() -> FixtureSource:
    from app.adapters.fixture_provider import FixtureProvider

    return FixtureProvider()


# --- LLM provider resolution (explicit; no hidden live->mock fallback) ------


def resolve_provider_mode() -> ProviderMode:
    """Resolve the effective LLM runtime mode from the environment.

    Rules (first match wins):
    - ``DEMO_MODE`` truthy                 -> deterministic
    - ``AUTHLENS_LLM_MODE=deterministic``  -> deterministic
    - ``AUTHLENS_LLM_MODE=live``           -> live (needs a key, else startup error)
    - otherwise                            -> live iff ``ANTHROPIC_API_KEY`` is set,
                                              else deterministic

    Never inspects or exposes key material beyond presence.
    """
    from app.providers.config import LLMProviderConfig

    cfg = LLMProviderConfig.from_env()
    explicit = os.environ.get(LLM_MODE_ENV_VAR, "").strip().lower()
    if cfg.demo_mode or explicit == "deterministic":
        return "deterministic"
    if explicit == "live":
        return "live"
    return "live" if cfg.api_key else "deterministic"


def build_llm_provider(mode: ProviderMode) -> LLMProvider:
    """Construct the provider for ``mode``. Raises in live mode without a key."""
    from app.providers.config import LLMProviderConfig
    from app.providers.mock_provider import MockLLMProvider

    if mode == "deterministic":
        return MockLLMProvider()
    cfg = LLMProviderConfig.from_env()
    if not cfg.api_key:
        raise ProviderConfigurationError(
            "live LLM mode requires ANTHROPIC_API_KEY; refusing to fall back to the "
            "mock provider. Set ANTHROPIC_API_KEY, or select deterministic mode "
            "(DEMO_MODE=1 or AUTHLENS_LLM_MODE=deterministic)."
        )
    from app.providers.anthropic_provider import AnthropicLLMProvider

    return AnthropicLLMProvider(cfg)


# --- Composition root -------------------------------------------------------


def build_default_workflow_orchestrator(
    repository: CaseRepository,
    fixtures: FixtureSource,
    *,
    provider_mode: ProviderMode | None = None,
) -> WorkflowOrchestrator:
    """Assemble the deterministic orchestrator over every stage port.

    The analysis backbone is deterministic. In live mode a real provider is
    injected into the LLM-capable stages (retrieval refiner + evidence
    mapper); the deterministic gates re-check their output either way.
    Evidence mapping and gap detection are wired as *factories* so the
    orchestrator can build them per operation with the case's evidence sources
    (a runtime clarification must become citable evidence).
    """
    from app.agents.disclosure_agent import DisclosureAgent
    from app.agents.evidence_mapper import build_evidence_mapper
    from app.agents.evidence_retriever import build_evidence_retriever
    from app.agents.gap_detector import build_gap_detector
    from app.agents.packet_generator import PacketGeneratorAgent
    from app.agents.policy_parser import build_policy_parser
    from app.agents.verification_agent import VerificationAgent
    from app.orchestration import AuthLensOrchestrator
    from app.services.form_draft import MockPayerFormDrafter

    mode = provider_mode or resolve_provider_mode()
    provider: LLMProvider | None = build_llm_provider(mode) if mode == "live" else None

    def evidence_mapper_factory(sources: Mapping[str, EvidenceSource]) -> EvidenceMapper:
        return build_evidence_mapper(sources, provider)

    def gap_detector_factory(sources: Mapping[str, EvidenceSource]) -> GapDetector:
        return build_gap_detector(sources)

    return AuthLensOrchestrator(
        repository,
        policy_parser=build_policy_parser(),
        evidence_retriever=build_evidence_retriever(provider),
        evidence_mapper_factory=evidence_mapper_factory,
        gap_detector_factory=gap_detector_factory,
        disclosure_filter=DisclosureAgent(),
        packet_generator=PacketGeneratorAgent(),
        packet_verifier=VerificationAgent(),
        form_drafter=MockPayerFormDrafter(),
    )


# --- Environment-driven configuration helpers -------------------------------


def resolve_cors_origins() -> list[str]:
    """Development CORS allowlist from AUTHLENS_CORS_ORIGINS (comma-separated)."""
    raw = os.environ.get(CORS_ORIGINS_ENV_VAR)
    if raw is None or not raw.strip():
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


# --- Request-scoped getters (state is bound by create_app) ------------------


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_case_repository(request: Request) -> CaseRepository:
    return request.app.state.case_repository


def get_workflow_orchestrator(request: Request) -> WorkflowOrchestrator:
    return request.app.state.workflow_orchestrator


def get_case_service(request: Request) -> CaseService:
    return request.app.state.case_service


def get_provider_mode(request: Request) -> ProviderMode:
    """Report the effective LLM runtime mode.

    Resolved from the environment at request time (it never probes the
    Anthropic API or exposes key material). In normal operation this equals
    the mode validated at startup (``app.state.provider_mode``); resolving
    live keeps the indicator truthful if the operator changes configuration.
    """
    return resolve_provider_mode()
