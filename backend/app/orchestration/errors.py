"""Orchestration-level errors (see app.services.cases.errors for the base).

``error_code`` values match the stable ApiError codes in
docs/API_CONTRACT.md. Messages are public descriptions only.
"""

from app.services.cases.errors import CaseOperationError


class QuestionNotFoundError(CaseOperationError):
    error_code = "question_not_found"

    def __init__(self, case_id: str, question_id: str) -> None:
        super().__init__(
            f"no clarification question with id {question_id!r}", case_id=case_id
        )
        self.question_id = question_id


class QuestionAlreadyAnsweredError(CaseOperationError):
    error_code = "question_already_answered"

    def __init__(self, case_id: str, question_id: str) -> None:
        super().__init__(
            f"clarification question {question_id!r} is already answered",
            case_id=case_id,
        )
        self.question_id = question_id


class PacketNotVerifiedError(CaseOperationError):
    """Form drafting requires a verified packet and a passing verification."""

    error_code = "packet_not_verified"

    def __init__(self, case_id: str, reason: str) -> None:
        super().__init__(f"packet is not verified: {reason}", case_id=case_id)


class StageExecutionError(CaseOperationError):
    """A workflow stage failed; the case was rolled back to its prior state."""

    error_code = "internal_error"

    def __init__(
        self, message: str, *, case_id: str | None = None, stage: str | None = None
    ) -> None:
        super().__init__(message, case_id=case_id)
        self.stage = stage


class StageTimeoutError(StageExecutionError):
    """A workflow stage exceeded its time budget and was abandoned."""
