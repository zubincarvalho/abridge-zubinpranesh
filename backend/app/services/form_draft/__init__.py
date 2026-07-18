"""Mock payer form drafting (Agent E).

Populates the synthetic payer form from a VERIFIED packet only. There is
no submit action anywhere in this package; the draft is terminal at
"Ready for Clinician Review".
"""

from app.services.form_draft.drafter import (
    FormDraftError,
    MockPayerFormDrafter,
    UnverifiedPacketError,
)

__all__ = [
    "FormDraftError",
    "MockPayerFormDrafter",
    "UnverifiedPacketError",
]
