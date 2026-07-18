"""Agent timeline event contracts.

Every workflow stage emits AgentEvent records. The frontend renders them as
the Agent Timeline. Events carry titles and human-readable detail only —
never model chain-of-thought, prompts, or raw LLM output.
"""

from datetime import datetime
from enum import Enum

from pydantic import Field

from app.contracts._base import ContractModel


class AgentStage(str, Enum):
    INTAKE = "intake"
    POLICY_PARSING = "policy_parsing"
    EVIDENCE_RETRIEVAL = "evidence_retrieval"
    EVIDENCE_MAPPING = "evidence_mapping"
    GAP_DETECTION = "gap_detection"
    CLARIFICATION = "clarification"
    DISCLOSURE_REVIEW = "disclosure_review"
    PACKET_GENERATION = "packet_generation"
    VERIFICATION = "verification"
    FORM_DRAFTING = "form_drafting"
    HUMAN_REVIEW = "human_review"


class EventStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentEvent(ContractModel):
    event_id: str
    case_id: str
    sequence: int = Field(ge=0, description="Monotonically increasing per case")
    stage: AgentStage
    status: EventStatus
    title: str
    detail: str | None = Field(
        default=None, description="Human-readable summary; never chain-of-thought or raw prompts"
    )
    related_ids: list[str] = Field(
        default_factory=list,
        description="Ids of artifacts this event touched (criteria, evidence, packet, ...)",
    )
    occurred_at: datetime
