"""Form drafter tests: verified-packet-only gate, no submission surface."""

from datetime import datetime, timezone

import pytest

from app.contracts import (
    PacketStatus,
    PriorAuthorizationFormDraft,
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)
from app.services.form_draft.drafter import (
    MockPayerFormDrafter,
    UnverifiedPacketError,
)
from tests.output_pipeline.conftest import generate_packet, verified_pipeline


def test_unverified_packet_cannot_create_form(case):
    disclosed, packet = generate_packet(case)
    assert packet.status is PacketStatus.DRAFT
    passing = VerificationResult(
        verification_id="ver-x",
        packet_id=packet.packet_id,
        passed=True,
        checked_claim_count=len(packet.claims),
        issues=[],
        verified_at=datetime.now(timezone.utc),
    )
    with pytest.raises(UnverifiedPacketError):
        MockPayerFormDrafter().draft(packet, passing, disclosed)


def test_failed_verification_cannot_create_form(case):
    disclosed, verified, result = verified_pipeline(case)
    failing = result.model_copy(
        update={
            "passed": False,
            "issues": [
                VerificationIssue(
                    issue_id="vi-001",
                    severity=VerificationSeverity.BLOCKING,
                    description="Unsupported claim.",
                )
            ],
        }
    )
    with pytest.raises(UnverifiedPacketError):
        MockPayerFormDrafter().draft(verified, failing, disclosed)


def test_mismatched_verification_cannot_create_form(case):
    disclosed, verified, result = verified_pipeline(case)
    other = result.model_copy(update={"packet_id": "pkt-other"})
    with pytest.raises(UnverifiedPacketError):
        MockPayerFormDrafter().draft(verified, other, disclosed)


def test_arbitrary_prose_rejected(case):
    disclosed, verified, result = verified_pipeline(case)
    with pytest.raises(UnverifiedPacketError):
        MockPayerFormDrafter().draft(
            "Patient definitely needs this MRI, please approve.", result, disclosed
        )


def test_unknown_packet_id_rejected(case):
    disclosed, verified, result = verified_pipeline(case)
    on_case = disclosed.model_copy(
        update={"packet": verified, "verification": result}
    )
    with pytest.raises(UnverifiedPacketError):
        MockPayerFormDrafter().draft_by_id(on_case, "pkt-forged")


def test_verified_packet_creates_form(case):
    disclosed, verified, result = verified_pipeline(case)
    form = MockPayerFormDrafter().draft(verified, result, disclosed)
    assert isinstance(form, PriorAuthorizationFormDraft)
    assert form.packet_id == verified.packet_id
    assert form.case_id == disclosed.case_id
    assert "(MOCK)" in form.payer_form_name


def test_draft_by_id_uses_case_record(case):
    disclosed, verified, result = verified_pipeline(case)
    on_case = disclosed.model_copy(
        update={"packet": verified, "verification": result}
    )
    form = MockPayerFormDrafter().draft_by_id(on_case, verified.packet_id)
    assert form.packet_id == verified.packet_id


def test_final_state_is_ready_for_review(case):
    disclosed, verified, result = verified_pipeline(case)
    form = MockPayerFormDrafter().draft(verified, result, disclosed)
    assert form.status == "ready_for_review"
    assert "CLINICIAN REVIEW" in form.attestation
    assert "Not a guarantee of approval" in form.attestation


def test_fields_trace_to_claims(case):
    disclosed, verified, result = verified_pipeline(case)
    form = MockPayerFormDrafter().draft(verified, result, disclosed)
    known_claims = {c.claim_id for c in verified.claims}
    clinical_fields = [f for f in form.fields if f.field_id.startswith("f-crit-")]
    assert clinical_fields
    for field in clinical_fields:
        assert field.source_claim_ids
        assert set(field.source_claim_ids) <= known_claims


def test_unresolved_warnings_included(case):
    disclosed, verified, result = verified_pipeline(case)
    warned = result.model_copy(
        update={
            "issues": [
                VerificationIssue(
                    issue_id="vi-w1",
                    severity=VerificationSeverity.WARNING,
                    description="Citation placement: section sec-x references unknown claim clm-x.",
                )
            ]
        }
    )
    form = MockPayerFormDrafter().draft(verified, warned, disclosed)
    warnings_field = next(f for f in form.fields if f.field_id == "f-warnings")
    assert "unknown claim" in warnings_field.value


def test_no_submission_field_or_action_exists(case):
    disclosed, verified, result = verified_pipeline(case)
    drafter = MockPayerFormDrafter()
    form = drafter.draft(verified, result, disclosed)

    # No API on the drafter or the draft suggests submission.
    for obj in (drafter, form):
        for name in dir(obj):
            assert "submit" not in name.lower(), name

    # No field or value exposes a submit action; status is the only literal.
    assert form.status == "ready_for_review"
    for field in form.fields:
        assert "submit" not in field.field_id.lower()
        assert "submit" not in field.label.lower()
    # The attestation explicitly says it was not sent anywhere.
    assert "Not sent to any payer" in form.attestation
