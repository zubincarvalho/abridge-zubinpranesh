"""Shared base model for all AuthLens contracts.

Contracts are FROZEN after the foundation phase. Parallel agents must not
edit files in this package; contract-change requests go in the agent's
report under docs/agent_reports/ (see docs/PARALLEL_EXECUTION.md).
"""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Strict base: undeclared fields are rejected so drift is caught early."""

    model_config = ConfigDict(extra="forbid")
