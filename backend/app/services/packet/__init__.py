"""Prior authorization packet generation (Agent E).

Builds the focused, source-grounded packet draft from INCLUDE'd content
only. Every clinical statement is a PacketClaim citing EvidenceItem ids;
the packet always ends with the fixed human-review sentence.
"""

from app.services.packet.builder import (
    HUMAN_REVIEW_SENTENCE,
    EvidenceGroundedPacketGenerator,
    PacketGenerationError,
)

__all__ = [
    "HUMAN_REVIEW_SENTENCE",
    "EvidenceGroundedPacketGenerator",
    "PacketGenerationError",
]
