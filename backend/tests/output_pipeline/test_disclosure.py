"""Minimum-necessary disclosure filter tests."""

from app.agents.disclosure_agent import DisclosureAgent
from app.contracts import DisclosureDecisionType


def decisions_by_source(case):
    return {d.source_id: d for d in DisclosureAgent().review(case)}


def test_every_candidate_gets_a_decision(case):
    decisions = decisions_by_source(case)
    expected = {"note-001", "clar-001"} | {
        item.source_id for item in case.patient.chart_items
    }
    assert set(decisions) == expected


def test_unrelated_information_excluded(case):
    decisions = decisions_by_source(case)
    assert decisions["fhir-cond-allergy"].decision is DisclosureDecisionType.EXCLUDE
    assert decisions["fhir-cond-mh"].decision is DisclosureDecisionType.EXCLUDE
    assert "minimum-necessary" in decisions["fhir-cond-allergy"].reason


def test_relevant_evidence_retained(case):
    decisions = decisions_by_source(case)
    for source_id in ("note-001", "fhir-cond-back", "clar-001", "fhir-ref-pt"):
        assert decisions[source_id].decision is DisclosureDecisionType.INCLUDE, source_id


def test_included_items_explain_which_criteria_need_them(case):
    decisions = decisions_by_source(case)
    assert "LM-1" in decisions["fhir-cond-back"].reason
    assert "LM-3" in decisions["clar-001"].reason
    assert "requested service order" in decisions["fhir-sr-mri"].reason


def test_every_decision_has_a_reason(case):
    for decision in DisclosureAgent().review(case):
        assert decision.reason.strip()


def test_sensitive_item_flagged_for_human_review(case):
    decision = decisions_by_source(case)["fhir-cond-mh"]
    assert decision.phi_category == "behavioral_health"
    assert "clinician review" in decision.reason


def test_no_broad_chart_dump(case):
    """Exclusion is the default: uncited items never ride along."""
    decisions = DisclosureAgent().review(case)
    excluded = [d for d in decisions if d.decision is DisclosureDecisionType.EXCLUDE]
    assert excluded, "an unrelated chart must produce exclusions"
    cited = {e.source_id for a in case.assessments for e in a.evidence}
    for decision in decisions:
        if decision.decision is DisclosureDecisionType.INCLUDE:
            assert (
                decision.source_id in cited
                or "requested service order" in decision.reason
            )
