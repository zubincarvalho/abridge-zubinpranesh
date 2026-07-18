"""All contract and port modules must import cleanly."""

import importlib

import pytest

MODULES = [
    "app",
    "app.config",
    "app.contracts",
    "app.contracts.api",
    "app.contracts.assessment",
    "app.contracts.case",
    "app.contracts.disclosure",
    "app.contracts.events",
    "app.contracts.evidence",
    "app.contracts.form_draft",
    "app.contracts.packet",
    "app.contracts.policy",
    "app.contracts.verification",
    "app.ports",
    "app.ports.case_repository",
    "app.ports.disclosure_filter",
    "app.ports.evidence_mapper",
    "app.ports.evidence_retriever",
    "app.ports.form_drafter",
    "app.ports.gap_detector",
    "app.ports.llm_provider",
    "app.ports.packet_generator",
    "app.ports.packet_verifier",
    "app.ports.policy_parser",
    "app.ports.workflow_orchestrator",
]


@pytest.mark.parametrize("module", MODULES)
def test_module_imports(module):
    importlib.import_module(module)


def test_contract_exports_cover_required_models():
    import app.contracts as c

    required = [
        "AuthLensCase", "PatientSummary", "RequestedService", "PolicyCriterion",
        "EvidenceCandidate", "EvidenceItem", "CriterionAssessment",
        "ClinicianClarification", "DisclosureDecision", "ReadinessSummary",
        "PriorAuthorizationPacket", "PacketClaim", "VerificationIssue",
        "VerificationResult", "PriorAuthorizationFormDraft", "AgentEvent", "ApiError",
    ]
    for name in required:
        assert hasattr(c, name), f"missing contract export: {name}"
