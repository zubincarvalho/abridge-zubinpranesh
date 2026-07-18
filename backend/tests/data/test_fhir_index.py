"""FHIR flattening, reference normalization, lookup, and extraction helpers."""

import pytest

from app.data import (
    DuplicateIdError,
    FhirResourceIndex,
    MalformedDataError,
    UnresolvedReferenceError,
    normalize_reference,
)
from tests.data.conftest import minimal_record


class TestNormalizeReference:
    def test_urn_uuid(self):
        assert normalize_reference("urn:uuid:abc-123") == "abc-123"

    def test_typed_reference(self):
        assert normalize_reference("Patient/abc-123") == "abc-123"
        assert normalize_reference("MedicationRequest/m.1-x") == "m.1-x"

    def test_plain_id_passthrough(self):
        assert normalize_reference("abc-123") == "abc-123"

    def test_url_not_mistaken_for_typed_reference(self):
        url = "http://example.org/fhir/Patient/abc"
        assert normalize_reference(url) == url


class TestFlatteningRealRecord:
    def test_flattens_all_groups_plus_patient_and_encounter(self, first_record):
        index = FhirResourceIndex.from_record(first_record)
        related = first_record.encounter_fhir["related_resources"]
        expected = sum(len(v) for v in related.values()) + 2  # + Patient + Encounter
        assert len(index) == expected
        assert index.patient() is not None
        assert index.encounter() is not None

    def test_group_counts_match_metadata(self, first_record):
        index = FhirResourceIndex.from_record(first_record)
        for group, count in first_record.metadata["related_resource_counts"].items():
            assert len(index.resources_of_type(group)) == count

    def test_whole_dataset_flattens_without_duplicates(self, dataset):
        total = 0
        for record in dataset:
            index = FhirResourceIndex.from_record(record)
            total += len(index)
        assert total > 25 * 2  # every encounter carries related resources

    def test_extraction_helpers_return_typed_resources(self, dataset):
        # Use the whole dataset so every helper sees at least one hit
        # for the types the dataset ships.
        seen: set[str] = set()
        for record in dataset:
            index = FhirResourceIndex.from_record(record)
            for helper, expected_type in [
                (index.conditions, "Condition"),
                (index.medications, "MedicationRequest"),
                (index.procedures, "Procedure"),
                (index.observations, "Observation"),
                (index.diagnostic_reports, "DiagnosticReport"),
            ]:
                for entry in helper():
                    assert entry.resource["resourceType"] == expected_type
                    seen.add(expected_type)
        assert seen == {
            "Condition",
            "MedicationRequest",
            "Procedure",
            "Observation",
            "DiagnosticReport",
        }

    def test_service_requests_helper(self):
        # The official dataset ships none; a synthetic record proves the path.
        record = minimal_record()
        index = FhirResourceIndex.from_encounter_fhir(
            record["encounter_fhir"],
            patient=record["patient_context"]["patient"],
        )
        (sr,) = index.service_requests()
        assert sr.resource["resourceType"] == "ServiceRequest"


class TestLookupAndResolution:
    def test_deterministic_source_id_lookup(self, first_record):
        index = FhirResourceIndex.from_record(first_record)
        for source_id in index.source_ids:
            entry = index.get(source_id)
            assert entry.source_id == source_id
            # Lookup returns the same content every time.
            assert index.get(source_id).raw == entry.raw

    def test_raw_is_the_original_resource_and_isolated(self, first_record):
        index = FhirResourceIndex.from_record(first_record)
        condition = first_record.encounter_fhir["related_resources"]["Condition"][0]
        entry = index.get(condition["id"])
        assert entry.raw == condition
        mutated = entry.raw
        mutated["status"] = "TAMPERED"
        assert entry.raw == condition

    def test_resolves_subject_and_encounter_urn_references(self, first_record):
        index = FhirResourceIndex.from_record(first_record)
        condition = index.conditions()[0]
        subject = index.resolve_reference(condition.resource["subject"]["reference"])
        assert subject.resource_type == "Patient"
        encounter = index.resolve_reference(
            condition.resource["encounter"]["reference"]
        )
        assert encounter.resource_type == "Encounter"

    def test_resolves_typed_and_plain_references(self):
        record = minimal_record()
        index = FhirResourceIndex.from_encounter_fhir(
            record["encounter_fhir"],
            patient=record["patient_context"]["patient"],
        )
        assert index.resolve_reference("Encounter/enc-1").resource_type == "Encounter"
        assert index.resolve_reference("pat-1").resource_type == "Patient"
        assert index.resolve_reference("urn:uuid:cond-1").resource_type == "Condition"

    def test_unresolved_reference_raises_with_context(self, first_record):
        index = FhirResourceIndex.from_record(first_record)
        with pytest.raises(UnresolvedReferenceError, match="urn:uuid:ghost"):
            index.resolve_reference("urn:uuid:ghost")
        with pytest.raises(UnresolvedReferenceError, match="ghost"):
            index.get("ghost")

    def test_duplicate_resource_ids_rejected(self):
        record = minimal_record()
        dup = dict(record["encounter_fhir"]["related_resources"]["Condition"][0])
        record["encounter_fhir"]["related_resources"]["Condition"].append(dup)
        with pytest.raises(DuplicateIdError, match="cond-1"):
            FhirResourceIndex.from_encounter_fhir(record["encounter_fhir"])

    def test_resource_without_id_rejected(self):
        record = minimal_record()
        del record["encounter_fhir"]["related_resources"]["Condition"][0]["id"]
        with pytest.raises(MalformedDataError, match="no 'id'"):
            FhirResourceIndex.from_encounter_fhir(record["encounter_fhir"])
