"""Single safe revision for wording, formatting, or citation placement.

After a failed verification, at most ONE safe revision may be applied to a
packet, and it may only touch presentation: append the missing fixed
human-review sentence, or drop a dangling section->claim reference.

It never touches claim text, claim evidence, criterion statuses, or any
factual content — a missing fact can never be revised into a satisfied
fact. Any issue outside the safe categories is left standing for the
regular regenerate-and-re-verify path (an explicit human-triggered API
call, per docs/AGENT_WORKFLOWS.md §4).
"""

from app.contracts import (
    PriorAuthorizationPacket,
    VerificationIssue,
    VerificationResult,
)
from app.services.packet.builder import HUMAN_REVIEW_SENTENCE

_SAFE_PREFIXES = ("Formatting:", "Citation placement:")


def is_safe_issue(issue: VerificationIssue) -> bool:
    return issue.description.startswith(_SAFE_PREFIXES)


class SafeRevisionError(RuntimeError):
    """Raised when a second revision is attempted on the same packet."""


class SafePacketReviser:
    """Applies at most one presentation-only revision per packet."""

    def __init__(self) -> None:
        self._revised_packet_ids: set[str] = set()

    def revise(
        self, packet: PriorAuthorizationPacket, result: VerificationResult
    ) -> PriorAuthorizationPacket:
        """Return a copy of ``packet`` with safe issues fixed.

        Only issues flagged as Formatting / Citation placement are acted on;
        everything else (unsupported claims, invalid citations, invented
        requirements, leaks, overstatements) is untouched and will still
        fail re-verification.
        """
        if packet.packet_id in self._revised_packet_ids:
            raise SafeRevisionError(
                f"Packet {packet.packet_id} was already revised once; only one "
                "safe revision is permitted. Regenerate the packet instead."
            )
        self._revised_packet_ids.add(packet.packet_id)

        safe_issues = [i for i in result.issues if is_safe_issue(i)]
        sections = [s.model_copy(deep=True) for s in packet.sections]
        known_claims = {c.claim_id for c in packet.claims}

        for issue in safe_issues:
            if issue.description.startswith("Citation placement:"):
                for section in sections:
                    section.claim_ids = [
                        cid for cid in section.claim_ids if cid in known_claims
                    ]
            elif issue.description.startswith("Formatting:") and sections:
                last = sections[-1]
                if not last.body.rstrip().endswith(HUMAN_REVIEW_SENTENCE):
                    last.body = f"{last.body.rstrip()} {HUMAN_REVIEW_SENTENCE}"

        return packet.model_copy(update={"sections": sections})
