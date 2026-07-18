"""In-memory CaseRepository (satisfies app.ports.case_repository.CaseRepository).

Demo-scope persistence: cases live in a dict for the process lifetime.
Stored state is isolated by deep-copying on every write and read, so a
caller mutating a returned AuthLensCase can never corrupt the stored copy —
`save` (whole-case replace) is the only way to change persisted state.
"""

import threading

from app.contracts import AuthLensCase
from app.repositories.errors import CaseAlreadyExistsError, CaseNotFoundError


class InMemoryCaseRepository:
    def __init__(self) -> None:
        self._cases: dict[str, AuthLensCase] = {}
        self._lock = threading.Lock()

    def create(self, case: AuthLensCase) -> AuthLensCase:
        """Persist a new case. Raises CaseAlreadyExistsError on duplicate id."""
        with self._lock:
            if case.case_id in self._cases:
                raise CaseAlreadyExistsError(case.case_id)
            self._cases[case.case_id] = case.model_copy(deep=True)
        return case.model_copy(deep=True)

    def get(self, case_id: str) -> AuthLensCase:
        """Return the case. Raises CaseNotFoundError if absent."""
        with self._lock:
            try:
                stored = self._cases[case_id]
            except KeyError:
                raise CaseNotFoundError(case_id) from None
            return stored.model_copy(deep=True)

    def save(self, case: AuthLensCase) -> AuthLensCase:
        """Whole-case replace of an existing case. Raises CaseNotFoundError."""
        with self._lock:
            if case.case_id not in self._cases:
                raise CaseNotFoundError(case.case_id)
            self._cases[case.case_id] = case.model_copy(deep=True)
        return case.model_copy(deep=True)

    def list_case_ids(self) -> list[str]:
        with self._lock:
            return list(self._cases)

    def reset(self) -> None:
        """Remove all cases (demo reset). Never touches fixture files."""
        with self._lock:
            self._cases.clear()
