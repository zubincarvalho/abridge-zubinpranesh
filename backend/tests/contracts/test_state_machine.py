"""Case state machine invariants (safety-relevant; do not weaken)."""

from app.contracts import ALLOWED_TRANSITIONS, CaseStatus, can_transition


def test_no_submitted_state():
    assert "submitted" not in {s.value for s in CaseStatus}
    for status in CaseStatus:
        assert "submit" not in status.value


def test_every_status_has_a_transition_entry():
    assert set(ALLOWED_TRANSITIONS) == set(CaseStatus)


def test_ready_for_review_is_terminal():
    assert ALLOWED_TRANSITIONS[CaseStatus.READY_FOR_REVIEW] == frozenset()


def test_happy_path_is_reachable():
    path = [
        CaseStatus.DRAFT,
        CaseStatus.INTAKE_READY,
        CaseStatus.ANALYZING,
        CaseStatus.AWAITING_CLARIFICATION,
        CaseStatus.REANALYZING,
        CaseStatus.AWAITING_CLARIFICATION,
        CaseStatus.PACKET_DRAFTED,
        CaseStatus.VERIFIED,
        CaseStatus.READY_FOR_REVIEW,
    ]
    for current, target in zip(path, path[1:]):
        assert can_transition(current, target), f"{current} -> {target}"


def test_verification_failure_loop():
    assert can_transition(CaseStatus.PACKET_DRAFTED, CaseStatus.VERIFICATION_FAILED)
    assert can_transition(CaseStatus.VERIFICATION_FAILED, CaseStatus.PACKET_DRAFTED)


def test_no_shortcuts_around_verification():
    """The form draft can only follow VERIFIED; nothing skips verification."""
    for status, targets in ALLOWED_TRANSITIONS.items():
        if CaseStatus.READY_FOR_REVIEW in targets:
            assert status == CaseStatus.VERIFIED
        if CaseStatus.VERIFIED in targets:
            assert status == CaseStatus.PACKET_DRAFTED
