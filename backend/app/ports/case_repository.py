"""Case repository port. In-memory implementation is sufficient for the demo."""

from typing import Protocol

from app.contracts import AuthLensCase


class CaseRepository(Protocol):
    def create(self, case: AuthLensCase) -> AuthLensCase:
        """Persist a new case. Raises if the case_id already exists."""
        ...

    def get(self, case_id: str) -> AuthLensCase:
        """Return the case. Raises a not-found error if absent."""
        ...

    def save(self, case: AuthLensCase) -> AuthLensCase:
        """Persist the updated case state atomically (whole-case replace)."""
        ...

    def list_case_ids(self) -> list[str]:
        ...

    def reset(self) -> None:
        """Remove all cases (demo reset). Never touches fixture files."""
        ...
