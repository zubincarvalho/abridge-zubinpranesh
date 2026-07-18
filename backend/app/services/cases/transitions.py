"""Case state-transition validation.

Thin, safety-critical wrappers over the frozen transition table
``app.contracts.case.ALLOWED_TRANSITIONS``. Every status change the
orchestrator makes goes through :func:`apply_transition`; there is no other
write path to ``AuthLensCase.status`` in Agent F code.
"""

from collections.abc import Iterable
from datetime import datetime

from app.contracts import ALLOWED_TRANSITIONS, AuthLensCase, CaseStatus, can_transition

from app.services.cases.errors import InvalidStateTransitionError


def require_status(
    case: AuthLensCase, allowed: Iterable[CaseStatus], operation: str
) -> None:
    """Raise InvalidStateTransitionError unless the case is in an allowed status."""
    allowed_set = frozenset(allowed)
    if case.status not in allowed_set:
        raise InvalidStateTransitionError(
            case_id=case.case_id,
            current_status=case.status,
            operation=operation,
            allowed=allowed_set,
        )


def apply_transition(case: AuthLensCase, target: CaseStatus, *, now: datetime) -> None:
    """Move the case to ``target`` if the frozen table allows it, else raise."""
    if not can_transition(case.status, target):
        raise InvalidStateTransitionError(
            case_id=case.case_id,
            current_status=case.status,
            operation=f"transition to {target.value}",
            allowed=ALLOWED_TRANSITIONS[case.status],
        )
    case.status = target
    case.updated_at = now
