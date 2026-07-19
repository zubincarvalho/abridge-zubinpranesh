"""Agent timeline event recorder.

Every workflow stage gets paired started/completed (or failed/skipped)
AgentEvent records appended to the case, with a per-case monotonically
increasing sequence. Titles and details are short orchestrator-authored
summaries — counts, artifact ids, public error descriptions. Never model
chain-of-thought, prompts, or raw completions (see
docs/SAFETY_AND_HUMAN_REVIEW.md rule 9).
"""

import threading
from collections.abc import Callable, Iterable
from datetime import datetime, timezone

from app.contracts import AgentEvent, AgentStage, AuthLensCase, EventStatus

# Events are UI summaries; anything longer than this is suspicious payload.
_MAX_DETAIL_CHARS = 400


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EventRecorder:
    """Appends AgentEvent records to a case with sequence/id bookkeeping."""

    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or utc_now
        # Optional per-thread progress sink: when set, every recorded event is
        # also handed to the callback so the API can stream live per-agent
        # progress. Thread-local so concurrent runs never cross streams.
        self._sink = threading.local()

    def set_sink(self, callback: "Callable[[AgentEvent], None] | None") -> None:
        """Set (or clear) the live event sink for the CURRENT thread only."""
        self._sink.callback = callback

    def _emit(self, event: AgentEvent) -> None:
        callback = getattr(self._sink, "callback", None)
        if callback is not None:
            try:
                callback(event)
            except Exception:  # a broken stream must never break the workflow
                pass

    def record(
        self,
        case: AuthLensCase,
        stage: AgentStage,
        status: EventStatus,
        title: str,
        detail: str | None = None,
        related_ids: Iterable[str] | None = None,
    ) -> AgentEvent:
        sequence = case.events[-1].sequence + 1 if case.events else 0
        if detail is not None and len(detail) > _MAX_DETAIL_CHARS:
            detail = detail[: _MAX_DETAIL_CHARS - 1] + "…"
        event = AgentEvent(
            event_id=f"{case.case_id}-ev-{sequence:04d}",
            case_id=case.case_id,
            sequence=sequence,
            stage=stage,
            status=status,
            title=title,
            detail=detail,
            related_ids=list(related_ids or []),
            occurred_at=self._clock(),
        )
        case.events.append(event)
        self._emit(event)
        return event

    def started(
        self,
        case: AuthLensCase,
        stage: AgentStage,
        title: str,
        detail: str | None = None,
        related_ids: Iterable[str] | None = None,
    ) -> AgentEvent:
        return self.record(case, stage, EventStatus.STARTED, title, detail, related_ids)

    def completed(
        self,
        case: AuthLensCase,
        stage: AgentStage,
        title: str,
        detail: str | None = None,
        related_ids: Iterable[str] | None = None,
    ) -> AgentEvent:
        return self.record(case, stage, EventStatus.COMPLETED, title, detail, related_ids)

    def failed(
        self,
        case: AuthLensCase,
        stage: AgentStage,
        title: str,
        detail: str | None = None,
        related_ids: Iterable[str] | None = None,
    ) -> AgentEvent:
        return self.record(case, stage, EventStatus.FAILED, title, detail, related_ids)

    def skipped(
        self,
        case: AuthLensCase,
        stage: AgentStage,
        title: str,
        detail: str | None = None,
        related_ids: Iterable[str] | None = None,
    ) -> AgentEvent:
        return self.record(case, stage, EventStatus.SKIPPED, title, detail, related_ids)
