"""Packet verifier port (evaluator in the evaluator-optimizer loop).

Independently checks every PacketClaim against its cited evidence and the
parsed policy criteria. Must be implemented independently of the packet
generator (separate prompts/logic) so it can catch generator errors.
"""

from typing import Protocol

from app.contracts import AuthLensCase, PriorAuthorizationPacket, VerificationResult


class PacketVerifier(Protocol):
    def verify(self, packet: PriorAuthorizationPacket, case: AuthLensCase) -> VerificationResult:
        """Check every claim; ``passed`` is True only with zero BLOCKING issues.

        Checks include: evidence exists and quotes its source verbatim,
        claims do not overstate evidence (referral != completed therapy),
        policy statements match the parsed criteria, and no excluded
        content leaked into the packet.
        """
        ...
