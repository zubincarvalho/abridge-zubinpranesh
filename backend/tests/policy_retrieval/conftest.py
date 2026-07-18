"""Shared fixtures for Agent C's policy-parsing and retrieval tests.

All inputs come from the frozen, read-only demo policy and fixture. The
``AuthLensCase`` is assembled from the fixture explicitly (contract models
forbid undeclared fields, and the fixture carries demo-only annotation keys).
Criteria used by the retrieval tests are produced by the real parser so the
two halves of Agent C are exercised end to end.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.contracts import (
    AuthLensCase,
    CaseStatus,
    EncounterNote,
    EncounterTranscript,
    PatientSummary,
    PayerPolicy,
    PolicyCriterion,
    RequestedService,
)
from app.services.policy.parser import DeterministicPolicyParser

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "lumbar_mri_prior_auth.json"
POLICY_PATH = REPO_ROOT / "data" / "policies" / "lumbar_mri_policy.md"

# Every source_id the demo case can legitimately cite. Retrieval must never
# invent a source outside this set.
KNOWN_SOURCE_IDS = frozenset(
    {
        "note-001",
        "transcript-001",
        "fhir-cond-001",
        "fhir-obs-slr-001",
        "fhir-med-001",
        "fhir-ref-pt-001",
        "fhir-sr-mri-001",
        "fhir-cond-002",
    }
)


@pytest.fixture(scope="session")
def policy_text() -> str:
    return POLICY_PATH.read_text()


@pytest.fixture(scope="session")
def fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture(scope="session")
def policy(fixture_data: dict) -> PayerPolicy:
    return PayerPolicy(**fixture_data["policy"])


@pytest.fixture(scope="session")
def case(fixture_data: dict, policy: PayerPolicy) -> AuthLensCase:
    note = fixture_data["encounter_note"]
    transcript = fixture_data["encounter_transcript"]
    now = datetime(2026, 7, 18, tzinfo=timezone.utc)
    return AuthLensCase(
        case_id="case-demo-001",
        status=CaseStatus.ANALYZING,
        created_at=now,
        updated_at=now,
        patient=PatientSummary(**fixture_data["patient"]),
        requested_service=RequestedService(**fixture_data["requested_service"]),
        clinical_indication=fixture_data["clinical_indication"],
        indication_codes=fixture_data["indication_codes"],
        encounter_note=EncounterNote(
            source_id=note["source_id"], title=note["title"], text=note["text"]
        ),
        encounter_transcript=EncounterTranscript(
            source_id=transcript["source_id"], text=transcript["text"]
        ),
        policy=policy,
    )


@pytest.fixture(scope="session")
def parser() -> DeterministicPolicyParser:
    return DeterministicPolicyParser()


@pytest.fixture(scope="session")
def criteria(
    parser: DeterministicPolicyParser, policy: PayerPolicy, policy_text: str
) -> list[PolicyCriterion]:
    """LM-1..LM-7 as produced by the real parser from the frozen policy."""
    return parser.parse(policy, policy_text)


@pytest.fixture(scope="session")
def criteria_by_id(criteria: list[PolicyCriterion]) -> dict[str, PolicyCriterion]:
    return {c.criterion_id: c for c in criteria}
