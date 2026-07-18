"""Form drafter port.

Populates the MOCK payer form from a VERIFIED packet only. This port
deliberately does not accept free-form clinical text: its inputs are the
typed packet, its passing verification result, and the case.
"""

from typing import Protocol

from app.contracts import (
    AuthLensCase,
    PriorAuthorizationFormDraft,
    PriorAuthorizationPacket,
    VerificationResult,
)


class FormDrafter(Protocol):
    def draft(
        self,
        packet: PriorAuthorizationPacket,
        verification: VerificationResult,
        case: AuthLensCase,
    ) -> PriorAuthorizationFormDraft:
        """Return the mock form draft.

        Implementations MUST raise if ``packet.status`` is not VERIFIED, if
        ``verification.packet_id != packet.packet_id``, or if
        ``verification.passed`` is False. Field values are drawn from
        packet claims (``source_claim_ids``); the drafter never composes
        new clinical statements.
        """
        ...
