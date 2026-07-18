"""Evidence Retriever agent (Agent C) — EvidenceRetriever port implementation.

For one criterion the focused workers fan out concurrently over the encounter
note, transcript, structured chart, and recorded clarifications, applying
deterministic resource/date/code/keyword filters *before* anything is emitted
so a dense chart is never forwarded wholesale. Workers return typed candidate
evidence only — they never classify a criterion as met, and a documented
negative finding is kept and flagged, distinct from "no result found".

An optional LLM relevance refiner runs strictly *after* deterministic
filtering and can only drop clearly irrelevant candidates (never add text,
rewrite an excerpt, raise a confidence, or judge fulfilment); on any provider
error the deterministic result stands unchanged. When no provider is supplied
the retriever is fully deterministic.

This module is the wiring surface the orchestrator binds to the
EvidenceRetriever port; the implementation lives in ``app.services.retrieval``.
"""

from __future__ import annotations

from typing import Sequence

from app.contracts import EvidenceSource
from app.ports.llm_provider import LLMProvider
from app.services.retrieval.refiner import LLMCandidateRefiner
from app.services.retrieval.retriever import ParallelEvidenceRetriever
from app.services.retrieval.workers import RetrievalWorker, default_workers


def build_evidence_retriever(
    provider: LLMProvider | None = None,
    *,
    encounter_history_sources: Sequence[EvidenceSource] = (),
    workers: Sequence[RetrievalWorker] | None = None,
    max_parallel_workers: int = 8,
) -> ParallelEvidenceRetriever:
    """Factory for the EvidenceRetriever port binding.

    Deterministic by default. Pass ``provider`` to enable the safe LLM
    relevance refiner. ``encounter_history_sources`` injects prior-encounter
    text sources for the multi-encounter dataset (the demo case has one
    encounter, so the history worker reports ``source_unavailable`` otherwise).
    """
    active_workers = (
        tuple(workers)
        if workers is not None
        else default_workers(encounter_history_sources)
    )
    refiner = LLMCandidateRefiner(provider) if provider is not None else None
    return ParallelEvidenceRetriever(
        workers=active_workers,
        refiner=refiner,
        max_parallel_workers=max_parallel_workers,
    )


EvidenceRetrieverAgent = ParallelEvidenceRetriever
