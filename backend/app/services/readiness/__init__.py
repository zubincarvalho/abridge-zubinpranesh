"""Agent D — gap detection and Documentation Readiness services.

Category rubrics, deterministic readiness scoring, clarification-question
generation, and the code-only GapDetector implementation.
"""

from app.services.readiness.calculator import (
    SCORE_NAME,
    compute_readiness,
    compute_score,
    overall_denial_risk,
    unresolved_required_gaps,
)
from app.services.readiness.detector import DeterministicGapDetector
from app.services.readiness.questions import LM3_QUESTION, generate_clarifications
from app.services.readiness.rubrics import assess_criterion

__all__ = [
    "LM3_QUESTION",
    "SCORE_NAME",
    "DeterministicGapDetector",
    "assess_criterion",
    "compute_readiness",
    "compute_score",
    "generate_clarifications",
    "overall_denial_risk",
    "unresolved_required_gaps",
]
