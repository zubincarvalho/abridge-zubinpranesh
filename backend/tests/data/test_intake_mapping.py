"""Dataset record -> frozen intake contracts, per the reference mapping spec
in backend/tests/contracts/test_abridge_dataset.py (authoritative)."""

from app.contracts import EncounterNote, EncounterTranscript, PatientSummary
from app.data import map_record


def test_every_record_maps_into_strict_contracts(dataset):
    for record in dataset:
        bundle = map_record(record)
        PatientSummary.model_validate(bundle.patient.model_dump())
        EncounterNote.model_validate(bundle.note.model_dump())
        EncounterTranscript.model_validate(bundle.transcript.model_dump())
        assert bundle.patient.chart_items


def test_source_id_conventions(first_record):
    bundle = map_record(first_record)
    assert bundle.note.source_id == f"note-{first_record.encounter_id}"
    assert bundle.transcript.source_id == f"transcript-{first_record.encounter_id}"
    fhir_ids = {
        r["id"]
        for group in first_record.encounter_fhir["related_resources"].values()
        for r in group
    }
    assert {item.source_id for item in bundle.patient.chart_items} == fhir_ids


def test_note_transcript_and_metadata_preserved_verbatim(first_record):
    bundle = map_record(first_record)
    assert bundle.note.text == first_record.note
    assert bundle.note.title == first_record.metadata["visit_title"]
    assert bundle.transcript.text == first_record.transcript
    assert bundle.patient.patient_id == first_record.metadata["patient_id"]
    assert bundle.patient.birth_date == (
        first_record.patient_context["patient"]["birthDate"]
    )


def test_display_name_marked_synthetic_and_labels_nonempty(dataset):
    for record in dataset:
        bundle = map_record(record)
        assert bundle.patient.display_name.endswith("(synthetic)")
        for item in bundle.patient.chart_items:
            assert item.display.strip()


def test_mapping_does_not_mutate_the_record(first_record):
    raw_before = first_record.raw
    map_record(first_record)
    assert first_record.raw == raw_before
