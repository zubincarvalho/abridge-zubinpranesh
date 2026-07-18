"""Evidence mapper port.

Turns retrieval candidates into accepted, cited EvidenceItem records for a
criterion. The mapper is the gatekeeper for citation quality: it must
reject candidates whose excerpt does not appear verbatim in the source.
"""

from typing import Protocol

from app.contracts import EvidenceCandidate, EvidenceItem, PolicyCriterion


class EvidenceMapper(Protocol):
    def map_evidence(
        self, criterion: PolicyCriterion, candidates: list[EvidenceCandidate]
    ) -> list[EvidenceItem]:
        """Return accepted evidence with confidence grades for one criterion."""
        ...
