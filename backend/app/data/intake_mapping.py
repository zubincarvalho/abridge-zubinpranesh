"""Map an Abridge dataset record into the frozen intake contracts.

This mirrors the authoritative reference mapping in
`backend/tests/contracts/test_abridge_dataset.py` (per docs/ABRIDGE_DATASET.md:
if this module and that test disagree, the test wins):

- metadata.patient_id / patient resource  -> PatientSummary
- note (+ metadata.visit_title)           -> EncounterNote  (source_id: note-<encounter_id>)
- transcript                              -> EncounterTranscript (source_id: transcript-<encounter_id>)
- encounter_fhir.related_resources[*]     -> ChartItem per resource (source_id: FHIR resource id)
"""

from dataclasses import dataclass

from app.contracts import ChartItem, EncounterNote, EncounterTranscript, PatientSummary
from app.data.abridge import AbridgeRecord

# FHIR resourceType -> ChartItem.category (keep in sync with the contract test)
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


@dataclass(frozen=True)
class IntakeBundle:
    """The intake-contract view of one dataset record."""

    patient: PatientSummary
    note: EncounterNote
    transcript: EncounterTranscript


def map_record(record: AbridgeRecord) -> IntakeBundle:
    meta = record.metadata
    fhir_patient = record.patient_context["patient"]
    name = fhir_patient["name"][0]
    display_name = " ".join([*name.get("given", []), name.get("family", "")]).strip()

    chart_items = []
    for group, resources in record.encounter_fhir["related_resources"].items():
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
        text=record.note,
    )
    transcript = EncounterTranscript(
        source_id=f"transcript-{meta['encounter_id']}",
        text=record.transcript,
    )
    return IntakeBundle(patient=patient, note=note, transcript=transcript)
