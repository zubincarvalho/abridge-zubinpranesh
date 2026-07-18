"""Packet generator tests."""

import pytest

from app.agents.packet_generator import PacketGeneratorAgent
from app.contracts import ClaimType, PacketStatus
from app.services.packet.builder import HUMAN_REVIEW_SENTENCE, PacketGenerationError
from tests.output_pipeline.conftest import (
    UNRELATED_ALLERGY,
    UNRELATED_SENSITIVE,
    generate_packet,
)

REQUIRED_SECTION_TITLES = [
    "Patient and request summary",
    "Requested service",
    "Clinical indication",
    "Medical-necessity narrative",
    "Criterion-by-criterion evidence",
    "Citations",
    "Remaining gaps",
    "Disclosure summary",
    "Clinician attestation",
    "Human review",
]


def packet_text(packet) -> str:
    return "\n".join(s.title + "\n" + s.body for s in packet.sections)


def test_packet_requires_disclosure_review(case):
    with pytest.raises(PacketGenerationError):
        PacketGeneratorAgent().generate(case)


def test_packet_has_all_required_sections(case):
    _, packet = generate_packet(case)
    assert [s.title for s in packet.sections] == REQUIRED_SECTION_TITLES


def test_packet_is_draft_never_self_verified(case):
    _, packet = generate_packet(case)
    assert packet.status is PacketStatus.DRAFT


def test_every_clinical_claim_cites_evidence(case):
    _, packet = generate_packet(case)
    clinical = [c for c in packet.claims if c.claim_type is ClaimType.CLINICAL]
    assert clinical
    for claim in clinical:
        assert claim.evidence_ids, claim.claim_id
        assert claim.criterion_id


def test_every_criterion_represented(case):
    _, packet = generate_packet(case)
    represented = {c.criterion_id for c in packet.claims}
    assert represented == {"LM-1", "LM-2", "LM-3"}


def test_citations_are_exact(case):
    disclosed, packet = generate_packet(case)
    citations = next(s for s in packet.sections if s.section_id == "sec-citations")
    for assessment in disclosed.assessments:
        for evidence in assessment.evidence:
            assert evidence.excerpt in citations.body


def test_excluded_content_never_appears(case):
    _, packet = generate_packet(case)
    text = packet_text(packet)
    assert UNRELATED_ALLERGY not in text
    assert UNRELATED_SENSITIVE not in text


def test_packet_ends_with_human_review_sentence(case):
    _, packet = generate_packet(case)
    assert packet.sections[-1].body.rstrip().endswith(HUMAN_REVIEW_SENTENCE)


def test_packet_contains_attestation_placeholder_and_warning(case):
    _, packet = generate_packet(case)
    text = packet_text(packet)
    assert "Clinician attestation" in text
    assert "Signature:" in text
    assert "WARNING — human review required" in text


def test_packet_never_guarantees_approval(case):
    _, packet = generate_packet(case)
    text = packet_text(packet).lower()
    for phrase in ("will be approved", "guarantees approval", "approval is certain"):
        assert phrase not in text
    assert "not a prediction of payer approval" in text


def test_remaining_gaps_lists_weak_criteria(case):
    from app.contracts import CriterionStatus, DenialRisk

    weakened = case.model_copy(deep=True)
    weakened.assessments[1].status = CriterionStatus.WEAK
    weakened.assessments[1].denial_risk = DenialRisk.MEDIUM
    _, packet = generate_packet(weakened)
    gaps = next(s for s in packet.sections if s.section_id == "sec-gaps")
    assert "LM-2" in gaps.body
    assert "weak" in gaps.body
