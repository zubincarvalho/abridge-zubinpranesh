"""Minimum-necessary disclosure review (Agent E).

Every candidate patient item receives an explicit include/exclude decision
before packet generation. The default is exclusion; only items linked to a
policy criterion (or the requested service order itself) are included, each
with a stated reason. Sensitive content is labeled with a ``phi_category``
and flagged for clinician review.
"""

from app.services.disclosure.filter import MinimumNecessaryDisclosureFilter
from app.services.disclosure.sources import ResolvedSource, resolve_sources

__all__ = [
    "MinimumNecessaryDisclosureFilter",
    "ResolvedSource",
    "resolve_sources",
]
