"""Compatibility: the official Abridge dataset must map into our contracts.

The dataset (`synthetic-ambient-fhir-25/`, repo root) is READ-ONLY. The
mapping below is the **reference specification** for Agent A's loader in
`backend/app/data/` (see docs/ABRIDGE_DATASET.md): if the loader and this
test disagree, this test is authoritative.

Mapping (record -> AuthLens intake contracts):
- metadata.patient_id / patient resource  -> PatientSummary
- note (+ metadata.visit_title)           -> EncounterNote  (source_id: note-<encounter_id>)
- transcript                              -> EncounterTranscript (source_id: transcript-<encounter_id>)
- encounter_fhir.related_resources[*]     -> ChartItem per resource (source_id: FHIR resource id)
"""

import json
from pathlib import Path

import pytest

from app.contracts import ChartItem, EncounterNote, EncounterTranscript, PatientSummary
from tests.contracts.conftest import REPO_ROOT

DATASET_DIR = REPO_ROOT / "synthetic-ambient-fhir-25"
JSONL = DATASET_DIR / "synthetic-ambient-fhir-25.jsonl"

# FHIR resourceType -> ChartItem.category (loader spec; keep in sync with docs)
CATEGORY_BY_RESOURCE_TYPE = {
    "Condition": "condition",
    "MedicationRequest": "medication",
    "Procedure": "procedure",
    "Observation": "observation",
    "DiagnosticReport": "observation",
    "Immunization": "other",
    "ImagingStudy": "other",
    "ServiceRequest": "service_request",
}


def fhir_label(resource: dict) -> str:
    """Display label for a FHIR resource; generic fallback when uncoded."""
    code = (
        resource.get("code")
        or resource.get("vaccineCode")
        or resource.get("medicationCodeableConcept")
    )
    if isinstance(code, dict):
        if code.get("text"):
            return code["text"]
        for coding in code.get("coding", []):
            if coding.get("display"):
                return coding["display"]
    # e.g. MedicationRequest with a bare medicationReference URN
    return f"{resource.get('resourceType', 'Resource')} (unlabeled)"


def map_record(record: dict) -> tuple[PatientSummary, EncounterNote, EncounterTranscript]:
    meta = record["metadata"]
    fhir_patient = record["patient_context"]["patient"]
    name = fhir_patient["name"][0]
    display_name = " ".join([*name.get("given", []), name.get("family", "")]).strip()

    chart_items = []
    for group, resources in record["encounter_fhir"]["related_resources"].items():
        category = CATEGORY_BY_RESOURCE_TYPE.get(group, "other")
        for resource in resources:
            chart_items.append(
                ChartItem(
                    source_id=resource["id"],
                    category=category,
                    display=fhir_label(resource),
                    detail=f"{group}; status: {resource.get('status', 'n/a')}",
                )
            )

    patient = PatientSummary(
        patient_id=meta["patient_id"],
        display_name=f"{display_name} (synthetic)",
        birth_date=fhir_patient["birthDate"],
        sex=fhir_patient.get("gender", "unknown"),
        chart_items=chart_items,
    )
    note = EncounterNote(
        source_id=f"note-{meta['encounter_id']}",
        title=meta["visit_title"],
        text=record["note"],
    )
    transcript = EncounterTranscript(
        source_id=f"transcript-{meta['encounter_id']}",
        text=record["transcript"],
    )
    return patient, note, transcript


@pytest.fixture(scope="module")
def records() -> list[dict]:
    assert DATASET_DIR.is_dir(), "official Abridge dataset missing from repo root"
    return [json.loads(line) for line in JSONL.read_text().splitlines() if line.strip()]


def test_dataset_files_agree(records):
    array = json.loads((DATASET_DIR / "synthetic-ambient-fhir-25.json").read_text())
    summary = json.loads((DATASET_DIR / "summary.json").read_text())
    assert len(records) == 25
    assert array == records, "jsonl and json array must carry identical records"
    assert summary["records"] == 25 and summary["synthetic"] is True
    assert {e["id"] for e in summary["index"]} == {r["id"] for r in records}


def test_every_record_is_marked_synthetic(records):
    for record in records:
        assert record["metadata"]["synthetic"] is True


def test_every_record_maps_into_contracts(records):
    for record in records:
        patient, note, transcript = map_record(record)
        # round-trip through strict validation
        PatientSummary.model_validate(patient.model_dump())
        EncounterNote.model_validate(note.model_dump())
        EncounterTranscript.model_validate(transcript.model_dump())
        assert note.text.strip() and transcript.text.strip()
        assert patient.chart_items, "each encounter carries FHIR context"


def test_source_ids_unique_within_each_record(records):
    for record in records:
        patient, note, transcript = map_record(record)
        ids = [note.source_id, transcript.source_id] + [
            item.source_id for item in patient.chart_items
        ]
        assert len(ids) == len(set(ids)), f"duplicate source_id in {record['id']}"


def test_all_resource_groups_have_a_category_mapping(records):
    groups = set()
    for record in records:
        groups |= set(record["encounter_fhir"]["related_resources"])
    unmapped = groups - set(CATEGORY_BY_RESOURCE_TYPE)
    assert not unmapped, f"add ChartItem category mapping for: {unmapped}"


def test_every_chart_item_has_a_nonempty_label(records):
    for record in records:
        patient, _, _ = map_record(record)
        for item in patient.chart_items:
            assert item.display.strip()
