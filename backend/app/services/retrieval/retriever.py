"""Parallel per-criterion evidence retriever (Agent C).

Implements the frozen ``EvidenceRetriever`` port. For one criterion it fans
the focused workers out concurrently (ThreadPoolExecutor — workers are pure
functions over the case), merges and deduplicates their typed candidates,
and records a transparent ``RetrievalEventSummary``.

Bounded loop (docs/AGENT_WORKFLOWS.md §5): if the first pass over a
*required* criterion is uncertain (no candidate at MODERATE or better), the
query tier broadens and the workers run again — at most 3 iterations — then
the honest result is returned, possibly empty. Conditional criteria never
loop. The retriever never classifies a criterion as met; it only returns
candidates and counts.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Sequence

from app.contracts import (
    AuthLensCase,
    EvidenceCandidate,
    EvidenceConfidence,
    PolicyCriterion,
)

from app.services.retrieval.models import (
    NEGATIVE_FINDING_MARKER,
    RetrievalEventSummary,
    WorkerRunSummary,
)
from app.services.retrieval.queries import plan_for
from app.services.retrieval.refiner import CandidateRefiner
from app.services.retrieval.workers import RetrievalWorker, default_workers

MAX_ITERATIONS = 3

_CONFIDENCE_RANK = {
    EvidenceConfidence.HIGH: 0,
    EvidenceConfidence.MODERATE: 1,
    EvidenceConfidence.LOW: 2,
}


def _dedup_key(candidate: EvidenceCandidate) -> tuple:
    span = (candidate.span.start, candidate.span.end) if candidate.span else None
    return (candidate.source_id, candidate.excerpt, span, candidate.fhir_path)


class ParallelEvidenceRetriever:
    """``EvidenceRetriever`` port implementation with concurrent workers."""

    def __init__(
        self,
        workers: Sequence[RetrievalWorker] | None = None,
        refiner: CandidateRefiner | None = None,
        max_parallel_workers: int = 8,
    ) -> None:
        self._workers: tuple[RetrievalWorker, ...] = (
            tuple(workers) if workers is not None else default_workers()
        )
        self._refiner = refiner
        self._max_parallel = max(1, max_parallel_workers)
        self._last_summary: RetrievalEventSummary | None = None

    @property
    def last_event_summary(self) -> RetrievalEventSummary | None:
        """The transparent summary of the most recent retrieve() call."""
        return self._last_summary

    def retrieve(
        self, case: AuthLensCase, criterion: PolicyCriterion
    ) -> list[EvidenceCandidate]:
        candidates, _ = self.retrieve_with_summary(case, criterion)
        return candidates

    def retrieve_with_summary(
        self, case: AuthLensCase, criterion: PolicyCriterion
    ) -> tuple[list[EvidenceCandidate], RetrievalEventSummary]:
        plan = plan_for(criterion)
        required = criterion.applicability_note is None
        tier_budget = min(len(plan.tiers), MAX_ITERATIONS)

        all_runs: list[WorkerRunSummary] = []
        merged: dict[tuple, EvidenceCandidate] = {}
        iterations = 0
        confident = False
        last_iteration_runs: list[WorkerRunSummary] = []

        for tier_index in range(tier_budget):
            iterations = tier_index + 1
            terms = plan.tiers[tier_index]
            with ThreadPoolExecutor(
                max_workers=min(self._max_parallel, len(self._workers))
            ) as executor:
                futures = [
                    executor.submit(worker.run, case, criterion, terms, plan, iterations)
                    for worker in self._workers
                ]
                runs = [future.result() for future in futures]
            last_iteration_runs = [run.summary for run in runs]
            all_runs.extend(last_iteration_runs)
            for run in runs:
                for candidate in run.candidates:
                    merged.setdefault(_dedup_key(candidate), candidate)
            confident = any(
                candidate.confidence
                in (EvidenceConfidence.HIGH, EvidenceConfidence.MODERATE)
                for candidate in merged.values()
            )
            if confident or not required:
                break

        ordered = sorted(
            merged.values(),
            key=lambda c: (
                _CONFIDENCE_RANK[c.confidence],
                c.source_id,
                c.span.start if c.span else -1,
                c.excerpt,
            ),
        )
        candidates = [
            candidate.model_copy(
                update={"candidate_id": f"cand-{criterion.criterion_id}-{index:03d}"}
            )
            for index, candidate in enumerate(ordered, start=1)
        ]

        if self._refiner is not None and candidates:
            candidates = self._refiner.refine(criterion, candidates)

        summary = RetrievalEventSummary(
            criterion_id=criterion.criterion_id,
            category=criterion.category,
            iterations=iterations,
            confident=confident,
            total_candidates=len(candidates),
            negative_findings=sum(
                1
                for candidate in candidates
                if NEGATIVE_FINDING_MARKER in candidate.relevance_rationale
            ),
            sources_total=sum(run.sources_total for run in last_iteration_runs),
            sources_considered=sum(run.sources_considered for run in last_iteration_runs),
            worker_runs=tuple(all_runs),
        )
        self._last_summary = summary
        return candidates, summary
