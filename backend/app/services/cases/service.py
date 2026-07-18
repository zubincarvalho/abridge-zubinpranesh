"""Case service: creation with intake validation, reads, saves, demo reset.

Works against the frozen ``CaseRepository`` port only, so any repository
implementation (Agent A's in-memory one, or a test fake) plugs in.
"""

from collections.abc import Callable
from datetime import datetime

from app.contracts import AgentStage, AuthLensCase, CaseStatus
from app.events import EventRecorder, utc_now
from app.ports import CaseRepository

from app.services.cases.errors import (
    CaseNotFoundError,
    CaseOperationError,
    IntakeValidationError,
)
from app.services.cases.transitions import apply_transition


def validate_intake(case: AuthLensCase) -> None:
    """Workflow step 1: the intake inputs a run needs must be present.

    The Pydantic contracts already enforce shape; this checks the semantic
    minimums (non-empty note, policy reference, service code, indication).
    """
    problems: list[str] = []
    if not case.encounter_note.text.strip():
        problems.append("encounter note text is empty")
    if not case.policy.source_document.strip():
        problems.append("policy source_document is empty")
    if not case.requested_service.code.strip():
        problems.append("requested service code is empty")
    if not case.clinical_indication.strip():
        problems.append("clinical indication is empty")
    if not case.patient.patient_id.strip():
        problems.append("patient id is empty")
    if problems:
        raise IntakeValidationError(case.case_id, problems)


class CaseService:
    def __init__(
        self,
        repository: CaseRepository,
        *,
        clock: Callable[[], datetime] | None = None,
        recorder: EventRecorder | None = None,
    ) -> None:
        self._repository = repository
        self._clock = clock or utc_now
        self._recorder = recorder or EventRecorder(clock)

    def create_case(self, case: AuthLensCase) -> AuthLensCase:
        """Persist a new case; DRAFT cases are validated and moved to INTAKE_READY."""
        case = case.model_copy(deep=True)
        if case.status not in (CaseStatus.DRAFT, CaseStatus.INTAKE_READY):
            raise CaseOperationError(
                f"a case must be created in 'draft' or 'intake_ready', got "
                f"{case.status.value!r}",
                case_id=case.case_id,
            )
        validate_intake(case)
        if case.status is CaseStatus.DRAFT:
            apply_transition(case, CaseStatus.INTAKE_READY, now=self._clock())
            self._recorder.completed(
                case,
                AgentStage.INTAKE,
                "Intake inputs loaded",
                detail=(
                    f"Encounter note, policy {case.policy.policy_id}, and "
                    f"{len(case.patient.chart_items)} chart item(s) validated"
                ),
                related_ids=[case.encounter_note.source_id],
            )
        return self._repository.create(case)

    def get_case(self, case_id: str) -> AuthLensCase:
        try:
            return self._repository.get(case_id)
        except CaseOperationError:
            raise
        except Exception as exc:  # the port only specifies a not-found error
            raise CaseNotFoundError(case_id) from exc

    def save_case(self, case: AuthLensCase) -> AuthLensCase:
        return self._repository.save(case)

    def list_case_ids(self) -> list[str]:
        return self._repository.list_case_ids()

    def reset_demo(self) -> None:
        """Demo reset: drop all cases. Reseeding is the caller's concern."""
        self._repository.reset()
