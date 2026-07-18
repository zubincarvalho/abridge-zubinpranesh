"""Case workflow errors.

Every error carries an ``error_code`` matching the stable ApiError codes in
docs/API_CONTRACT.md so the API layer (Agent G) can map exceptions to
responses without inspecting messages. Messages are safe, public
descriptions — no prompts, completions, or clinical content.
"""

from app.contracts import CaseStatus


class CaseOperationError(Exception):
    """Base class for case workflow errors."""

    error_code: str = "internal_error"

    def __init__(self, message: str, *, case_id: str | None = None) -> None:
        super().__init__(message)
        self.case_id = case_id


class CaseNotFoundError(CaseOperationError):
    error_code = "case_not_found"

    def __init__(self, case_id: str) -> None:
        super().__init__(f"no case with case_id {case_id!r}", case_id=case_id)


class InvalidStateTransitionError(CaseOperationError):
    """The operation is not allowed from the case's current status (HTTP 409)."""

    error_code = "invalid_state_transition"

    def __init__(
        self,
        *,
        case_id: str,
        current_status: CaseStatus,
        operation: str,
        allowed: frozenset[CaseStatus] | set[CaseStatus] = frozenset(),
    ) -> None:
        allowed_names = ", ".join(sorted(s.value for s in allowed)) or "none"
        super().__init__(
            f"operation {operation!r} is not allowed while the case is "
            f"{current_status.value!r} (allowed from: {allowed_names})",
            case_id=case_id,
        )
        self.current_status = current_status
        self.operation = operation
        self.allowed = frozenset(allowed)


class IntakeValidationError(CaseOperationError):
    """Intake inputs are incomplete; the case cannot enter the workflow."""

    error_code = "internal_error"

    def __init__(self, case_id: str, problems: list[str]) -> None:
        super().__init__(
            "intake validation failed: " + "; ".join(problems), case_id=case_id
        )
        self.problems = list(problems)
