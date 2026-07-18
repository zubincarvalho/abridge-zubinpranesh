"""Workflow orchestrator port.

Deterministic, code-driven orchestration of the whole workflow. The
orchestrator owns case state transitions (via the ALLOWED_TRANSITIONS
table), emits AgentEvent records for every stage, and calls the other
ports. It contains no LLM prompts itself.

Each method raises an invalid-state error when the case is not in a status
from which the operation is allowed (see docs/API_CONTRACT.md).
"""

from typing import Protocol

from app.contracts import AgentEvent, AuthLensCase, ClarificationSubmission


class WorkflowOrchestrator(Protocol):
    def start_analysis(self, case_id: str) -> AuthLensCase:
        """intake_ready -> analyzing -> awaiting_clarification.

        Runs policy parsing, parallel evidence retrieval, evidence mapping,
        gap detection, clarification generation, and the initial readiness
        snapshot.
        """
        ...

    def submit_clarification(
        self, case_id: str, submission: ClarificationSubmission
    ) -> AuthLensCase:
        """awaiting_clarification -> reanalyzing -> awaiting_clarification.

        Records the clarification verbatim, re-assesses affected criteria,
        and appends a new readiness snapshot.
        """
        ...

    def generate_packet(self, case_id: str) -> AuthLensCase:
        """awaiting_clarification -> packet_drafted.

        Runs disclosure review then packet generation.
        """
        ...

    def verify_packet(self, case_id: str) -> AuthLensCase:
        """packet_drafted -> verified | verification_failed."""
        ...

    def draft_form(self, case_id: str) -> AuthLensCase:
        """verified -> ready_for_review. Requires a passing verification."""
        ...

    def get_case(self, case_id: str) -> AuthLensCase:
        """Read current case state (no side effects)."""
        ...

    def get_events(self, case_id: str) -> list[AgentEvent]:
        """Read the timeline, ordered by sequence (no side effects)."""
        ...
