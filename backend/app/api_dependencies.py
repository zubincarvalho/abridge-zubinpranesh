"""Dependency-injection surface for the AuthLens API (Agent G).

Routes depend only on the request-scoped getters below; ``app.main.create_app``
binds concrete instances onto ``app.state``. Defaults use the committed
in-memory repository and fixture provider (Agent A). The workflow
orchestrator default is a placeholder that fails loudly:

    INTEGRATION POINT — the integration agent binds Agent F's orchestration
    engine in ``build_default_workflow_orchestrator`` (or passes an instance
    to ``create_app(workflow_orchestrator=...)``). Nothing else changes.
"""

from __future__ import annotations

import os
from typing import Literal

from fastapi import Request

from app.api.case_service import CaseService, FixtureSource
from app.api.errors import ApiException
from app.config import Settings
from app.contracts import AgentEvent, AuthLensCase, ClarificationSubmission
from app.ports import CaseRepository, WorkflowOrchestrator

CORS_ORIGINS_ENV_VAR = "AUTHLENS_CORS_ORIGINS"
DEFAULT_CORS_ORIGINS = ("http://localhost:3000", "http://localhost:5173")


class PlaceholderWorkflowOrchestrator:
    """Satisfies the WorkflowOrchestrator port until Agent F's engine is bound.

    Every method raises a 500 ``internal_error`` so the API surface stays
    contract-shaped even before integration.
    """

    def _unconfigured(self) -> None:
        raise ApiException(
            500,
            "internal_error",
            "The workflow orchestrator is not configured on this deployment.",
            detail=(
                "Integration pending: bind the orchestration engine in "
                "app/api_dependencies.py (build_default_workflow_orchestrator)."
            ),
        )

    def start_analysis(self, case_id: str) -> AuthLensCase:
        self._unconfigured()
        raise AssertionError("unreachable")

    def submit_clarification(
        self, case_id: str, submission: ClarificationSubmission
    ) -> AuthLensCase:
        self._unconfigured()
        raise AssertionError("unreachable")

    def generate_packet(self, case_id: str) -> AuthLensCase:
        self._unconfigured()
        raise AssertionError("unreachable")

    def verify_packet(self, case_id: str) -> AuthLensCase:
        self._unconfigured()
        raise AssertionError("unreachable")

    def draft_form(self, case_id: str) -> AuthLensCase:
        self._unconfigured()
        raise AssertionError("unreachable")

    def get_case(self, case_id: str) -> AuthLensCase:
        self._unconfigured()
        raise AssertionError("unreachable")

    def get_events(self, case_id: str) -> list[AgentEvent]:
        self._unconfigured()
        raise AssertionError("unreachable")


# --- Default builders (used by create_app when nothing is injected) ---------


def build_default_case_repository() -> CaseRepository:
    from app.repositories.in_memory import InMemoryCaseRepository

    return InMemoryCaseRepository()


def build_default_fixture_provider() -> FixtureSource:
    from app.adapters.fixture_provider import FixtureProvider

    return FixtureProvider()


def build_default_workflow_orchestrator(
    repository: CaseRepository, fixtures: FixtureSource
) -> WorkflowOrchestrator:
    # INTEGRATION POINT: replace with Agent F's engine, e.g.
    #   from app.orchestration.engine import WorkflowEngine
    #   return WorkflowEngine(repository=repository, ...)
    return PlaceholderWorkflowOrchestrator()


# --- Environment-driven configuration helpers -------------------------------


def resolve_cors_origins() -> list[str]:
    """Development CORS allowlist from AUTHLENS_CORS_ORIGINS (comma-separated)."""
    raw = os.environ.get(CORS_ORIGINS_ENV_VAR)
    if raw is None or not raw.strip():
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def resolve_provider_mode() -> Literal["live", "deterministic"]:
    """LLM runtime mode for health details. Never touches key material."""
    from app.providers.config import LLMProviderConfig

    return "deterministic" if LLMProviderConfig.from_env().demo_mode else "live"


# --- Request-scoped getters (state is bound by create_app) ------------------


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_case_repository(request: Request) -> CaseRepository:
    return request.app.state.case_repository


def get_workflow_orchestrator(request: Request) -> WorkflowOrchestrator:
    return request.app.state.workflow_orchestrator


def get_case_service(request: Request) -> CaseService:
    return request.app.state.case_service


def get_provider_mode() -> Literal["live", "deterministic"]:
    return resolve_provider_mode()
