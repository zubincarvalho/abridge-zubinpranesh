"""Evidence retriever port.

Searches the encounter note, transcript, FHIR chart, and recorded
clarifications for text relevant to one criterion. Designed to run in
parallel across criteria (independent chart searches). A bounded agent
loop (max iterations fixed by the implementation, e.g. 3) may be used only
when initial retrieval is uncertain — see docs/AGENT_WORKFLOWS.md.
"""

from typing import Protocol

from app.contracts import AuthLensCase, EvidenceCandidate, PolicyCriterion


class EvidenceRetriever(Protocol):
    def retrieve(self, case: AuthLensCase, criterion: PolicyCriterion) -> list[EvidenceCandidate]:
        """Return candidate evidence for one criterion.

        Excerpts must be verbatim quotes with spans/paths into a known
        source_id. Returning an empty list is a valid, honest result.
        """
        ...
