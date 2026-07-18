"""Disclosure review agent — port-facing entry point for DisclosureFilter.

Satisfies the ``DisclosureFilter`` protocol (backend/app/ports/
disclosure_filter.py). The decision logic is deterministic and lives in
``app.services.disclosure``; every candidate item gets an explicit
include/exclude decision with a stated reason, defaulting to exclusion.
"""

from app.contracts import AuthLensCase, DisclosureDecision
from app.services.disclosure.filter import MinimumNecessaryDisclosureFilter


class DisclosureAgent:
    def __init__(
        self, filter_impl: MinimumNecessaryDisclosureFilter | None = None
    ) -> None:
        self._filter = filter_impl or MinimumNecessaryDisclosureFilter()

    def review(self, case: AuthLensCase) -> list[DisclosureDecision]:
        """Return one decision per candidate item; unrelated PHI is excluded."""
        return self._filter.review(case)
