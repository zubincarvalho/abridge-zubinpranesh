"""Independent packet verifier tests: every safety check must block."""

import pytest

from app.agents.verification_agent import VerificationAgent
from app.contracts import (
    ClaimType,
    CriterionStatus,
    PacketClaim,
    VerificationSeverity,
)
from app.services.verification.revision import SafeRevisionError
from tests.output_pipeline.conftest import generate_packet


def blocking(result):
    return [i for i in result.issues if i.severity is VerificationSeverity.BLOCKING]


def add_claim(packet, **overrides):
    claim = PacketClaim(
        claim_id="clm-bad",
        text="placeholder",
        claim_type=ClaimType.CLINICAL,
        criterion_id="LM-1",
        evidence_ids=["ev-lm1-note"],
        **{},
    ).model_copy(update=overrides)
    return packet.model_copy(update={"claims": [*packet.claims, claim]})


def test_valid_packet_passes(case):
    disclosed, packet = generate_packet(case)
    result = VerificationAgent().verify(packet, disclosed)
    assert result.passed, [i.description for i in result.issues]
    assert result.checked_claim_count == len(packet.claims)


def test_unsupported_claim_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(
        packet, text="The patient has severe canal stenosis.", evidence_ids=[]
    )
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("cites no evidence" in i.description for i in blocking(result))


def test_invalid_citation_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(packet, evidence_ids=["ev-does-not-exist"])
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("unknown evidence id" in i.description for i in blocking(result))


def test_non_verbatim_excerpt_blocked(case):
    disclosed, packet = generate_packet(case)
    tampered = disclosed.model_copy(deep=True)
    tampered.assessments[0].evidence[0].excerpt = "back pain, paraphrased loosely"
    result = VerificationAgent().verify(packet, tampered)
    assert not result.passed
    assert any("not a verbatim quote" in i.description for i in blocking(result))


def test_evidence_from_wrong_criterion_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(packet, criterion_id="LM-2", evidence_ids=["ev-lm1-note"])
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("does not support this claim" in i.description for i in blocking(result))


def test_invented_policy_requirement_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(
        packet,
        text="Policy MHP-IMG-2201 requires a prior CT scan within 30 days.",
        claim_type=ClaimType.POLICY,
        criterion_id="LM-99",
        evidence_ids=[],
    )
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("does not exist in the parsed policy" in i.description for i in blocking(result))


def test_misstated_policy_requirement_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(
        packet,
        text="Policy requires bariatric surgery consultation and psychiatric screening first.",
        claim_type=ClaimType.POLICY,
        criterion_id="LM-1",
        evidence_ids=[],
    )
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("must be restated from the policy" in i.description or "not be invented" in i.description
               for i in blocking(result))


def test_referral_presented_as_completion_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(
        packet,
        text="The patient completed a full course of physical therapy.",
        criterion_id="LM-3",
        evidence_ids=["ev-lm3-ref"],
    )
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("never proof of completed" in i.description for i in blocking(result))


def test_prescription_presented_as_failure_blocked(case):
    disclosed, packet = generate_packet(case)
    packet = add_claim(
        packet,
        text="Medication treatment failed to relieve the patient's symptoms.",
        criterion_id="LM-3",
        evidence_ids=["ev-lm3-med"],
    )
    result = VerificationAgent().verify(packet, disclosed)
    assert not result.passed
    assert any("never proof of" in i.description and "failure" in i.description
               for i in blocking(result))


def test_missing_criterion_blocked(case):
    disclosed, packet = generate_packet(case)
    pruned = packet.model_copy(
        update={"claims": [c for c in packet.claims if c.criterion_id != "LM-3"]}
    )
    result = VerificationAgent().verify(pruned, disclosed)
    assert not result.passed
    assert any("LM-3" in i.description and "not" in i.description for i in blocking(result))


def test_excluded_content_leak_blocked(case):
    disclosed, packet = generate_packet(case)
    leaked = packet.model_copy(deep=True)
    leaked.sections[0].body += " History also notable for seasonal allergic rhinitis."
    result = VerificationAgent().verify(leaked, disclosed)
    assert not result.passed
    assert any("leaked" in i.description or "excluded" in i.description.lower()
               for i in blocking(result))


def test_approval_guarantee_blocked(case):
    disclosed, packet = generate_packet(case)
    bragging = packet.model_copy(deep=True)
    bragging.sections[3].body += " This request will be approved."
    result = VerificationAgent().verify(bragging, disclosed)
    assert not result.passed
    assert any("guarantee" in i.description.lower() for i in blocking(result))


def test_hidden_conflict_blocked(case):
    conflicted = case.model_copy(deep=True)
    conflicted.assessments[1].status = CriterionStatus.CONFLICTING
    disclosed, packet = generate_packet(conflicted)
    scrubbed = packet.model_copy(deep=True)
    for section in scrubbed.sections:
        section.body = section.body.replace("conflict", "resolved").replace(
            "Conflict", "Resolved"
        )
    result = VerificationAgent().verify(scrubbed, disclosed)
    assert not result.passed
    assert any("conflict" in i.description.lower() for i in blocking(result))

    # And the honestly generated packet keeps the conflict visible.
    honest = VerificationAgent().verify(packet, disclosed)
    assert not any("conflict" in i.description.lower() for i in blocking(honest))


def test_missing_human_review_sentence_blocked(case):
    disclosed, packet = generate_packet(case)
    stripped = packet.model_copy(deep=True)
    stripped.sections[-1].body = "Please review."
    result = VerificationAgent().verify(stripped, disclosed)
    assert not result.passed
    assert any("human-review" in i.description for i in blocking(result))


# --- single safe revision ----------------------------------------------


def test_safe_revision_fixes_formatting_only_once(case):
    disclosed, packet = generate_packet(case)
    stripped = packet.model_copy(deep=True)
    stripped.sections[-1].body = "Please review."
    agent = VerificationAgent()
    result = agent.verify(stripped, disclosed)
    assert not result.passed

    revised = agent.revise_once(stripped, result)
    assert agent.verify(revised, disclosed).passed

    with pytest.raises(SafeRevisionError):
        agent.revise_once(stripped, result)


def test_safe_revision_never_fixes_a_missing_fact(case):
    disclosed, packet = generate_packet(case)
    bad = add_claim(
        packet, text="The patient has severe canal stenosis.", evidence_ids=[]
    )
    bad = bad.model_copy(deep=True)
    bad.sections[-1].body = "Please review."  # add a safe issue alongside
    agent = VerificationAgent()
    result = agent.verify(bad, disclosed)

    revised = agent.revise_once(bad, result)
    re_result = agent.verify(revised, disclosed)
    assert not re_result.passed
    assert any("cites no evidence" in i.description for i in blocking(re_result))
