"""Evidence retrieval service (Agent C — owned subtree).

Focused, deterministic retrieval workers plus a parallel per-criterion
retriever implementing the frozen ``EvidenceRetriever`` port.
"""

from app.services.retrieval.models import (
    NEGATIVE_FINDING_MARKER,
    NO_RESULT_NOTE,
    RetrievalEventSummary,
    WorkerOutcome,
    WorkerRunSummary,
)
from app.services.retrieval.queries import QueryPlan, plan_for
from app.services.retrieval.refiner import (
    CandidateRefiner,
    LLMCandidateRefiner,
    RefinerSelection,
)
from app.services.retrieval.retriever import MAX_ITERATIONS, ParallelEvidenceRetriever
from app.services.retrieval.workers import (
    ChartItemWorker,
    ClarificationsWorker,
    ConditionsWorker,
    EncounterHistoryWorker,
    EncounterNoteWorker,
    MedicationsWorker,
    ObservationsDiagnosticsWorker,
    ProceduresReferralsWorker,
    RetrievalWorker,
    ServiceRequestsWorker,
    TextSourceWorker,
    TranscriptWorker,
    WorkerRun,
    default_workers,
    select_chart_items,
)

__all__ = [
    "CandidateRefiner",
    "ChartItemWorker",
    "ClarificationsWorker",
    "ConditionsWorker",
    "EncounterHistoryWorker",
    "EncounterNoteWorker",
    "LLMCandidateRefiner",
    "MAX_ITERATIONS",
    "MedicationsWorker",
    "NEGATIVE_FINDING_MARKER",
    "NO_RESULT_NOTE",
    "ObservationsDiagnosticsWorker",
    "ParallelEvidenceRetriever",
    "ProceduresReferralsWorker",
    "QueryPlan",
    "RefinerSelection",
    "RetrievalEventSummary",
    "RetrievalWorker",
    "ServiceRequestsWorker",
    "TextSourceWorker",
    "TranscriptWorker",
    "WorkerOutcome",
    "WorkerRun",
    "WorkerRunSummary",
    "default_workers",
    "plan_for",
    "select_chart_items",
]
