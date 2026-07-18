"""Packet generator port.

Generates the focused prior authorization packet draft. May only use
content covered by an INCLUDE disclosure decision, and every clinical or
policy statement must be emitted as a PacketClaim with evidence_ids.
"""

from typing import Protocol

from app.contracts import AuthLensCase, PriorAuthorizationPacket


class PacketGenerator(Protocol):
    def generate(self, case: AuthLensCase) -> PriorAuthorizationPacket:
        """Return a packet with status DRAFT. Never marks its own work verified."""
        ...
