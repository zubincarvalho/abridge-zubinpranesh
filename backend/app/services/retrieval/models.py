"""Internal retrieval models (Agent C).

The retrieval event summary is the transparent record of what each worker
did: which sources existed, how many survived deterministic filtering, and
whether the worker found candidates, found nothing, or had no source to
search. It contains counts and human-readable notes only — never prompts,
completions, or chain-of-thought — and never a readiness decision.

``NO_RESULT_FOUND`` deliberately means "no documentation was located"; it is
distinct from a documented negative clinical finding (e.g. "denies fever"),
which is returned as a real candidate flagged as a negative finding.
"""

from dataclasses import dataclass, field
from enum import Enum


class WorkerOutcome(str, Enum):
    CANDIDATES_FOUND = "candidates_found"
    NO_RESULT_FOUND = "no_result_found"
    SOURCE_UNAVAILABLE = "source_unavailable"


NO_RESULT_NOTE = (
    "No matching documentation located. This means nothing was found to cite — "
    "it is not evidence that a finding is absent."
)

NEGATIVE_FINDING_MARKER = "Documents a negative clinical finding"


@dataclass(frozen=True)
class WorkerRunSummary:
    """What one worker did during one retrieval iteration."""

    worker: str
    kind: str
    iteration: int
    sources_total: int
    sources_considered: int
    candidates_found: int
    outcome: WorkerOutcome
    note: str | None = None


@dataclass(frozen=True)
class RetrievalEventSummary:
    """Transparent summary of one criterion's retrieval run."""

    criterion_id: str
    category: str
    iterations: int
    confident: bool
    total_candidates: int
    negative_findings: int
    sources_total: int
    sources_considered: int
    worker_runs: tuple[WorkerRunSummary, ...] = field(default_factory=tuple)

    def as_event_detail(self) -> str:
        """Human-readable one-liner suitable for ``AgentEvent.detail``."""
        workers = {run.worker for run in self.worker_runs}
        return (
            f"Evidence retrieval for {self.criterion_id} ({self.category}): "
            f"{self.total_candidates} candidate(s) from {len(workers)} worker(s) over "
            f"{self.iterations} iteration(s); sources narrowed by deterministic filters "
            f"{self.sources_total}→{self.sources_considered}; "
            f"{self.negative_findings} documented negative finding(s)."
        )
