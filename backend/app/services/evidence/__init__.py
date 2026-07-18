"""Agent D — evidence mapping services (deterministic core).

Verbatim citation gates, clinical-documentation rules, relevance signals,
and the code-only EvidenceMapper implementation.
"""

from app.services.evidence.envelopes import EvidenceMappingEnvelope
from app.services.evidence.mapper import DeterministicEvidenceMapper, apply_safety_caps
from app.services.evidence.verbatim import locate, resolve_verbatim_span, span_matches

__all__ = [
    "DeterministicEvidenceMapper",
    "EvidenceMappingEnvelope",
    "apply_safety_caps",
    "locate",
    "resolve_verbatim_span",
    "span_matches",
]
