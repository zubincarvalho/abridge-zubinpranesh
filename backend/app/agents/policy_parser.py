"""Policy Parser agent (Agent C) — PolicyParser port implementation.

Policy parsing is fully deterministic (docs/AGENT_WORKFLOWS.md): the payer
policy is structured into discrete criteria by mechanical markdown extraction
and a routing registry, never by a model call. Requirement text is always a
verbatim substring of the source document, so the parser cannot invent,
soften, or reinterpret a requirement, and it never sees patient data or
decides whether a patient satisfies a criterion.

This module is the wiring surface the orchestrator binds to the PolicyParser
port; the implementation lives in ``app.services.policy``.
"""

from __future__ import annotations

from app.services.policy.parser import DeterministicPolicyParser
from app.services.policy.routes import PolicyRouter


def build_policy_parser(router: PolicyRouter | None = None) -> DeterministicPolicyParser:
    """Factory for the PolicyParser port binding.

    A custom ``router`` may be supplied to register additional supported
    policy families without any contract change; the default supports the
    lumbar spine MRI route only and refuses to guess at unsupported ones.
    """
    return DeterministicPolicyParser(router)


PolicyParserAgent = DeterministicPolicyParser
