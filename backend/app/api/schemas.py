"""API-layer response models that extend (never alter) the frozen contracts."""

from typing import Literal

from pydantic import BaseModel

from app.contracts import HealthResponse


class HealthDetailsResponse(HealthResponse):
    """Liveness payload plus non-secret runtime details.

    ``provider_mode`` reports whether the LLM runtime would run against the
    live Anthropic API or the deterministic mock (``DEMO_MODE``). It carries
    no key material and never indicates whether a key is present.
    """

    provider_mode: Literal["live", "deterministic"]


class DemoScenario(BaseModel):
    """Metadata for a selectable demo scenario shown in the case picker."""

    scenario_id: str
    fixture_id: str
    title: str
    patient_display: str
    visit_summary: str
    requested_service: str
    payer: str
    policy_id: str
    expected_outcome: Literal["gap", "high_risk", "approved"]
    expected_outcome_label: str
    risk_level: Literal["low", "medium", "high"]
    description: str
    is_real_data: bool
