"""Disclosure filter port (minimum-necessary review).

Reviews every candidate chart item / evidence source and decides
include/exclude with a stated reason. Anything not clearly relevant to the
requested service must be EXCLUDED — the default is exclusion.
"""

from typing import Protocol

from app.contracts import AuthLensCase, DisclosureDecision


class DisclosureFilter(Protocol):
    def review(self, case: AuthLensCase) -> list[DisclosureDecision]:
        """Return one decision per candidate item; unrelated PHI is excluded."""
        ...
