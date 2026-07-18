"""AuthLens FastAPI application factory (Agent G).

``create_app`` wires the API layer against the frozen ports. Keyword
arguments exist so tests and the integration agent can inject port
implementations without touching module state; defaults come from
``app.api_dependencies``.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import api_dependencies as deps
from app.api.case_service import CaseService, FixtureSource
from app.api.errors import ApiException, install_error_handlers
from app.api.routes import router
from app.config import Settings, get_settings
from app.ports import CaseRepository, WorkflowOrchestrator

logger = logging.getLogger(__name__)


def create_app(
    *,
    settings: Settings | None = None,
    case_repository: CaseRepository | None = None,
    fixture_provider: FixtureSource | None = None,
    workflow_orchestrator: WorkflowOrchestrator | None = None,
    cors_origins: list[str] | None = None,
    seed_demo_on_startup: bool = True,
) -> FastAPI:
    settings = settings or get_settings()
    repository = case_repository or deps.build_default_case_repository()
    fixtures = fixture_provider or deps.build_default_fixture_provider()
    # Startup validation: resolving the mode fails loudly if live is requested
    # without a key, and the orchestrator builder constructs the live provider
    # eagerly so misconfiguration surfaces here rather than mid-request.
    provider_mode = deps.resolve_provider_mode()
    orchestrator = workflow_orchestrator or deps.build_default_workflow_orchestrator(
        repository, fixtures, provider_mode=provider_mode
    )
    case_service = CaseService(repository, fixtures)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if seed_demo_on_startup:
            try:
                case_service.get_or_seed_demo_case()
            except ApiException as exc:
                # GET /api/demo-case retries the seed lazily.
                logger.warning("demo case seeding failed: %s", exc.error.message)
        yield

    app = FastAPI(
        title="AuthLens API",
        version=settings.app_version,
        description=(
            "Point-of-capture prior authorization readiness API. "
            "Synthetic data only; no submission endpoint exists and "
            "'ready_for_review' is the terminal case state."
        ),
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.case_repository = repository
    app.state.workflow_orchestrator = orchestrator
    app.state.case_service = case_service
    app.state.provider_mode = provider_mode
    logger.info("AuthLens API configured (provider_mode=%s)", provider_mode)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins is not None else deps.resolve_cors_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(router)
    return app


app = create_app()
