"""Case intake, demo seeding, state gates, and evidence-source resolution.

Plumbing only — clinical analysis lives behind the frozen
``WorkflowOrchestrator`` port. This service:

- creates intake-stage cases from fixtures (Agent A's ``FixtureProvider``,
  seen through the structural ``FixtureSource`` protocol),
- remembers which fixture built each case so citation sources resolve for
  the evidence drawer,
- enforces the documented state gates (409s) before routes delegate to the
  orchestrator, so wrong-state calls never mutate anything.
"""

from __future__ import annotations

import uuid
from typing import Iterator, Protocol

from app.api import errors as api_errors
from app.contracts import (
    AgentEvent,
    AuthLensCase,
    CaseStatus,
    EvidenceSource,
    EvidenceSourceResponse,
    SourceType,
)
from app.data.errors import FixtureNotFoundError, SourceNotFoundError
from app.ports import CaseRepository
from app.repositories.errors import CaseNotFoundError

DEMO_CASE_ID = "case-demo-001"
DEMO_FIXTURE_ID = "lumbar_mri_prior_auth"


class FixtureSource(Protocol):
    """The slice of Agent A's FixtureProvider the API layer depends on."""

    def has(self, fixture_id: str) -> bool: ...

    def build_case(self, fixture_id: str, case_id: str) -> AuthLensCase: ...

    def get_evidence_source(self, fixture_id: str, source_id: str) -> EvidenceSource: ...


class CaseService:
    def __init__(self, repository: CaseRepository, fixtures: FixtureSource):
        self._repository = repository
        self._fixtures = fixtures
        self._fixture_by_case: dict[str, str] = {}

    # --- Reads -------------------------------------------------------------

    def get_case(self, case_id: str) -> AuthLensCase:
        try:
            return self._repository.get(case_id)
        except CaseNotFoundError as exc:
            raise api_errors.case_not_found(case_id) from exc

    def get_events(self, case_id: str) -> list[AgentEvent]:
        case = self.get_case(case_id)
        return sorted(case.events, key=lambda event: event.sequence)

    # --- Intake and demo lifecycle ------------------------------------------

    def create_case(self, fixture_id: str) -> AuthLensCase:
        if not self._fixtures.has(fixture_id):
            raise api_errors.fixture_not_found(fixture_id)
        case_id = f"case-{uuid.uuid4().hex[:12]}"
        try:
            case = self._fixtures.build_case(fixture_id, case_id)
        except FixtureNotFoundError as exc:
            raise api_errors.fixture_not_found(fixture_id) from exc
        created = self._repository.create(case)
        self._fixture_by_case[case_id] = fixture_id
        return created

    def get_or_seed_demo_case(self) -> AuthLensCase:
        """Return the demo case in its current state, seeding it if absent."""
        try:
            case = self._repository.get(DEMO_CASE_ID)
        except CaseNotFoundError:
            return self._seed_demo()
        self._fixture_by_case.setdefault(DEMO_CASE_ID, DEMO_FIXTURE_ID)
        return case

    def _seed_demo(self) -> AuthLensCase:
        if not self._fixtures.has(DEMO_FIXTURE_ID):
            raise api_errors.fixture_not_found(DEMO_FIXTURE_ID)
        case = self._fixtures.build_case(DEMO_FIXTURE_ID, DEMO_CASE_ID)
        created = self._repository.create(case)
        self._fixture_by_case[DEMO_CASE_ID] = DEMO_FIXTURE_ID
        return created

    def reset_demo(self) -> AuthLensCase:
        """Delete every in-memory case and reseed the demo (converges)."""
        self._repository.reset()
        self._fixture_by_case.clear()
        return self._seed_demo()

    # --- State gates (read-only; raise before the orchestrator is called) ---

    def ensure_status(
        self, case_id: str, allowed: tuple[CaseStatus, ...], operation: str
    ) -> AuthLensCase:
        case = self.get_case(case_id)
        if case.status not in allowed:
            required = " or ".join(f"'{status.value}'" for status in allowed)
            raise api_errors.invalid_state_transition(
                case_id=case_id,
                current=case.status,
                operation=operation,
                required=required,
            )
        return case

    def ensure_clarification_open(self, case_id: str, question_id: str) -> AuthLensCase:
        case = self.ensure_status(
            case_id, (CaseStatus.AWAITING_CLARIFICATION,), "submit a clarification"
        )
        question = next(
            (q for q in case.clarification_questions if q.question_id == question_id),
            None,
        )
        if question is None:
            raise api_errors.question_not_found(case_id, question_id)
        if question.status == "answered":
            raise api_errors.question_already_answered(case_id, question_id)
        return case

    def ensure_form_draft_allowed(self, case_id: str) -> AuthLensCase:
        """The verification gate: status 'verified' AND a stored passing result."""
        case = self.get_case(case_id)
        if (
            case.status != CaseStatus.VERIFIED
            or case.verification is None
            or not case.verification.passed
        ):
            raise api_errors.packet_not_verified(case_id, case.status)
        return case

    # --- Evidence drawer ----------------------------------------------------

    def resolve_evidence_source(
        self, case_id: str, source_id: str
    ) -> EvidenceSourceResponse:
        case = self.get_case(case_id)

        # Clarifications live on the case itself (recorded verbatim).
        for clarification in case.clarifications:
            if clarification.clarification_id == source_id:
                return EvidenceSourceResponse(
                    source_id=source_id,
                    source_type=SourceType.CLINICIAN_CLARIFICATION,
                    label="Clinician clarification (recorded verbatim)",
                    content=clarification.response,
                )

        fixture_id = self._fixture_by_case.get(case_id)
        if fixture_id is not None:
            try:
                source = self._fixtures.get_evidence_source(fixture_id, source_id)
            except SourceNotFoundError:
                pass
            else:
                return EvidenceSourceResponse(
                    source_id=source.source_id,
                    source_type=source.source_type,
                    label=source.label,
                    content=source.content,
                    fhir_resource_type=source.fhir_resource_type,
                )

        # Fallback for cases whose fixture mapping is unknown (e.g. seeded
        # directly into the repository): resolve from the case fields.
        for source in _case_derived_sources(case):
            if source.source_id == source_id:
                return source

        raise api_errors.source_not_found(case_id, source_id)


def _case_derived_sources(case: AuthLensCase) -> Iterator[EvidenceSourceResponse]:
    yield EvidenceSourceResponse(
        source_id=case.encounter_note.source_id,
        source_type=SourceType.ENCOUNTER_NOTE,
        label=case.encounter_note.title,
        content=case.encounter_note.text,
    )
    if case.encounter_transcript is not None:
        yield EvidenceSourceResponse(
            source_id=case.encounter_transcript.source_id,
            source_type=SourceType.ENCOUNTER_TRANSCRIPT,
            label="Encounter transcript",
            content=case.encounter_transcript.text,
        )
    for item in case.patient.chart_items:
        content = item.display if item.detail is None else f"{item.display}\n{item.detail}"
        yield EvidenceSourceResponse(
            source_id=item.source_id,
            source_type=SourceType.FHIR_RESOURCE,
            label=item.display,
            content=content,
        )
