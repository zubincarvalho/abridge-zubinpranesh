"""The synthetic demo fixture must load into the contracts and stay labeled."""

from app.contracts import (
    EncounterNote,
    EncounterTranscript,
    PatientSummary,
    PayerPolicy,
    RequestedService,
)
from tests.contracts.conftest import POLICY_PATH


def test_fixture_parts_validate(fixture_data):
    PatientSummary.model_validate(fixture_data["patient"])
    note = {k: v for k, v in fixture_data["encounter_note"].items() if not k.startswith("_")}
    EncounterNote.model_validate(note)
    EncounterTranscript.model_validate(fixture_data["encounter_transcript"])
    RequestedService.model_validate(fixture_data["requested_service"])
    policy = PayerPolicy.model_validate(fixture_data["policy"])
    assert policy.synthetic is True


def test_fixture_is_labeled_synthetic(fixture_data):
    assert fixture_data["synthetic"] is True
    assert "SYNTHETIC" in fixture_data["_synthetic_notice"]


def test_policy_document_is_labeled_synthetic():
    text = POLICY_PATH.read_text()
    assert "SYNTHETIC" in text
    for cid in ["LM-1", "LM-2", "LM-3", "LM-4", "LM-5", "LM-6", "LM-7"]:
        assert cid in text


def test_fixture_contains_the_demo_gap(fixture_data):
    """NSAID + PT referral present, completed-therapy documentation absent."""
    items = {i["source_id"]: i for i in fixture_data["patient"]["chart_items"]}
    assert items["fhir-med-001"]["category"] == "medication"
    assert items["fhir-ref-pt-001"]["category"] == "referral"
    note_text = fixture_data["encounter_note"]["text"].lower()
    assert "completed" not in note_text, "the note must NOT document completed therapy"
    assert fixture_data["expected_demo_clarification"]["criterion_id"] == "LM-3"
