"""Gap Detector agent (Agent D) — GapDetector port implementation.

Classification, clarification generation, and readiness scoring are fully
deterministic (docs/AGENT_WORKFLOWS.md §6: readiness is never LLM-computed;
the category rubrics hard-code the referral ≠ completion and
prescription ≠ failure rules). This module is the wiring surface the
orchestrator binds to the GapDetector port.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.contracts import EvidenceSource
from app.services.readiness.detector import DeterministicGapDetector


def build_gap_detector(
    sources: Mapping[str, EvidenceSource] | None = None,
) -> DeterministicGapDetector:
    """Factory for the GapDetector port binding."""
    return DeterministicGapDetector(sources)


GapDetectorAgent = DeterministicGapDetector
