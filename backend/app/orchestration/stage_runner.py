"""Bounded execution of one workflow stage call.

Stages run in a worker thread so the orchestrator can enforce a wall-clock
budget. On timeout the worker thread is abandoned (Python cannot kill it);
the orchestrator records a failed event and rolls the case back, so a
timed-out stage can never leave a partial transition or bypass a later
safety gate.
"""

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import TypeVar

from app.orchestration.errors import StageTimeoutError

T = TypeVar("T")


def call_with_timeout(
    fn: Callable[[], T], *, timeout_seconds: float, stage: str, case_id: str
) -> T:
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"stage-{stage}")
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        raise StageTimeoutError(
            f"stage {stage!r} timed out after {timeout_seconds:g}s",
            case_id=case_id,
            stage=stage,
        ) from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
