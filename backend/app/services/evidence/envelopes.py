"""Structured-output envelopes for Agent D's LLM stages.

``LLMProvider.complete_structured`` validates against a single Pydantic
model, so the evidence-mapping stage (whose logical output is a list) wraps
it in an envelope. These are Agent D implementation models, not frozen
contracts; the payloads they carry are the frozen contract types.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.contracts import EvidenceItem


class EvidenceMappingEnvelope(BaseModel):
    """LLM output for the evidence_mapping prompt: accepted items only."""

    model_config = ConfigDict(extra="forbid")

    items: list[EvidenceItem] = Field(default_factory=list)
