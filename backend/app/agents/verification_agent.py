"""Verification agent — port-facing entry point for PacketVerifier.

Satisfies the ``PacketVerifier`` protocol (backend/app/ports/
packet_verifier.py). The verifier is implemented independently of the
packet generator (``app.services.verification``): it re-derives every
index from the case and checks each claim mechanically. It also exposes
the single safe revision (wording / formatting / citation placement only;
never a factual fix) via ``revise_once``.
"""

from app.contracts import (
    AuthLensCase,
    PriorAuthorizationPacket,
    VerificationResult,
)
from app.services.verification.revision import SafePacketReviser
from app.services.verification.verifier import IndependentPacketVerifier


class VerificationAgent:
    def __init__(
        self,
        verifier: IndependentPacketVerifier | None = None,
        reviser: SafePacketReviser | None = None,
    ) -> None:
        self._verifier = verifier or IndependentPacketVerifier()
        self._reviser = reviser or SafePacketReviser()

    def verify(
        self, packet: PriorAuthorizationPacket, case: AuthLensCase
    ) -> VerificationResult:
        """Check every claim; ``passed`` is True only with zero BLOCKING issues."""
        return self._verifier.verify(packet, case)

    def revise_once(
        self, packet: PriorAuthorizationPacket, result: VerificationResult
    ) -> PriorAuthorizationPacket:
        """Apply the single permitted presentation-only revision.

        Raises SafeRevisionError on a second attempt for the same packet.
        Factual issues are never revised — they still fail re-verification.
        """
        return self._reviser.revise(packet, result)
