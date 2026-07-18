"""Packet generation agent — port-facing entry point for PacketGenerator.

Satisfies the ``PacketGenerator`` protocol (backend/app/ports/
packet_generator.py). Generation is deterministic and evidence-grounded
(``app.services.packet``): only INCLUDE'd content is used, every clinical
statement is a PacketClaim with evidence ids, and the packet always ends
with the fixed human-review sentence. The result is always status DRAFT —
only the independent verifier can pass it.
"""

from app.contracts import AuthLensCase, PriorAuthorizationPacket
from app.services.packet.builder import EvidenceGroundedPacketGenerator


class PacketGeneratorAgent:
    def __init__(
        self, generator: EvidenceGroundedPacketGenerator | None = None
    ) -> None:
        self._generator = generator or EvidenceGroundedPacketGenerator()

    def generate(self, case: AuthLensCase) -> PriorAuthorizationPacket:
        """Return a packet with status DRAFT. Never marks its own work verified."""
        return self._generator.generate(case)
