"""Shared fixtures for Agent D's evidence/readiness tests.

Builds evidence sources and policy criteria from the frozen lumbar MRI demo
fixture and policy (read-only inputs — never modified here).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.contracts import (
    EvidenceCandidate,
    EvidenceConfidence,
    EvidenceSource,
    PolicyCriterion,
    SourceType,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
FIXTURE_PATH = REPO_ROOT / "data" / "fixtures" / "lumbar_mri_prior_auth.json"


@pytest.fixture(scope="session")
def fixture_data() -> dict:
    return json.loads(FIXTURE_PATH.read_text())


@pytest.fixture(scope="session")
def sources(fixture_data: dict) -> dict[str, EvidenceSource]:
    """Evidence sources keyed by source_id, built from the frozen fixture."""
    note = fixture_data["encounter_note"]
    transcript = fixture_data["encounter_transcript"]
    built: dict[str, EvidenceSource] = {
        note["source_id"]: EvidenceSource(
            source_id=note["source_id"],
            source_type=SourceType.ENCOUNTER_NOTE,
            label=note["title"],
            content=note["text"],
        ),
        transcript["source_id"]: EvidenceSource(
            source_id=transcript["source_id"],
            source_type=SourceType.ENCOUNTER_TRANSCRIPT,
            label="Encounter transcript",
            content=transcript["text"],
        ),
    }
    for item in fixture_data["patient"]["chart_items"]:
        built[item["source_id"]] = EvidenceSource(
            source_id=item["source_id"],
            source_type=SourceType.FHIR_RESOURCE,
            label=item["display"],
            content=item["display"],
            fhir_resource_type=item["category"],
        )
    return built


def _criterion(cid: str, label: str, requirement: str, category: str, note: str | None = None) -> PolicyCriterion:
    return PolicyCriterion(
        criterion_id=cid,
        policy_id="MHP-IMG-2201",
        label=label,
        requirement=requirement,
        category=category,
        applicability_note=note,
    )


@pytest.fixture(scope="session")
def criteria() -> list[PolicyCriterion]:
    """LM-1..LM-7 parsed by hand from the frozen demo policy text."""
    return [
        _criterion(
            "LM-1",
            "Appropriate diagnosis or indication",
            "The record documents a clinical indication appropriate for lumbar "
            "spine MRI, such as suspected lumbar radiculopathy, with a "
            "corresponding diagnosis code.",
            "indication",
        ),
        _criterion(
            "LM-2",
            "Symptom duration of at least six weeks",
            "Symptoms have persisted for at least six (6) weeks, with the "
            "duration explicitly documented.",
            "duration",
        ),
        _criterion(
            "LM-3",
            "Completed and failed conservative treatment",
            "The patient has completed at least six (6) weeks of conservative "
            "treatment without sufficient improvement. A referral to therapy or "
            "a prescription alone does not satisfy this criterion.",
            "conservative_therapy",
        ),
        _criterion(
            "LM-4",
            "Relevant neurologic or examination findings",
            "The record documents neurologic or physical-examination findings "
            "consistent with the indication.",
            "exam_findings",
        ),
        _criterion(
            "LM-5",
            "Red-flag screening",
            "The record documents screening for red-flag conditions, with "
            "findings noted as present or absent.",
            "red_flags",
        ),
        _criterion(
            "LM-6",
            "Functional limitation",
            "The record documents a functional limitation attributable to the "
            "symptoms.",
            "functional_limitation",
        ),
        _criterion(
            "LM-7",
            "Clinical rationale for MRI",
            "The record documents why MRI results are expected to change "
            "management.",
            "rationale",
        ),
    ]


@pytest.fixture(scope="session")
def criteria_by_id(criteria: list[PolicyCriterion]) -> dict[str, PolicyCriterion]:
    return {c.criterion_id: c for c in criteria}


def make_candidate(
    criterion_id: str,
    source: EvidenceSource,
    excerpt: str,
    confidence: EvidenceConfidence = EvidenceConfidence.MODERATE,
    candidate_id: str = "cand-001",
) -> EvidenceCandidate:
    return EvidenceCandidate(
        candidate_id=candidate_id,
        criterion_id=criterion_id,
        source_id=source.source_id,
        source_type=source.source_type,
        excerpt=excerpt,
        confidence=confidence,
        relevance_rationale="test candidate",
    )
