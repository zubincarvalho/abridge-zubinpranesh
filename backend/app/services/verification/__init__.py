"""Independent packet verification (Agent E).

The evaluator side of the evaluator-optimizer loop: re-checks every packet
claim against the case's own evidence, policy, and disclosure decisions
using logic that shares nothing with the packet generator's composition
rules. Any BLOCKING issue fails verification and prevents form drafting.
"""

from app.services.verification.revision import SafePacketReviser, SafeRevisionError
from app.services.verification.verifier import IndependentPacketVerifier

__all__ = [
    "IndependentPacketVerifier",
    "SafePacketReviser",
    "SafeRevisionError",
]
