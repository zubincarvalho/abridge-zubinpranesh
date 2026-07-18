"""Demo-fixture adapter and the unified FixtureProvider."""

import json

import pytest

from app.adapters import (
    ABRIDGE_FIXTURE_PREFIX,
    DEMO_FIXTURE_ID,
    FixtureProvider,
    load_demo_fixture,
)
from app.contracts import AuthLensCase, CaseStatus, SourceType
from app.data import DatasetNotFoundError, FixtureNotFoundError, SourceNotFoundError


@pytest.fixture(scope="module")
def provider() -> FixtureProvider:
    return FixtureProvider()


class TestDemoFixtureLoading:
    def test_loads_and_validates(self):
        fixture = load_demo_fixture()
        assert fixture.fixture_id == DEMO_FIXTURE_ID
        assert fixture.synthetic is True
        assert fixture.requested_service.code == "72148"
        assert fixture.policy.policy_id == "MHP-IMG-2201"
        assert fixture.encounter_transcript is not None
        # Annotation keys are stripped, not smuggled into contracts.
        assert not hasattr(fixture.encounter_note, "_gap_note")

    def test_missing_file(self, tmp_path):
        with pytest.raises(DatasetNotFoundError, match="not found"):
            load_demo_fixture(tmp_path / "missing.json")

    def test_malformed_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{broken")
        with pytest.raises(Exception, match="malformed JSON"):
            load_demo_fixture(path)

    def test_missing_required_keys(self, tmp_path):
        path = tmp_path / "partial.json"
        path.write_text(json.dumps({"fixture_id": "x"}))
        with pytest.raises(Exception, match="missing required keys"):
            load_demo_fixture(path)


class TestFixtureProvider:
    def test_lists_demo_and_all_dataset_fixtures(self, provider, dataset):
        fixture_ids = provider.list_fixture_ids()
        assert fixture_ids[0] == DEMO_FIXTURE_ID
        assert len(fixture_ids) == 1 + len(dataset)
        assert all(
            fid.startswith(ABRIDGE_FIXTURE_PREFIX) for fid in fixture_ids[1:]
        )

    def test_builds_demo_case(self, provider):
        case = provider.build_case(DEMO_FIXTURE_ID, case_id="case-demo-001")
        AuthLensCase.model_validate(case.model_dump())
        assert case.status == CaseStatus.INTAKE_READY
        assert case.synthetic is True
        assert case.patient.patient_id == "pt-demo-001"
        assert case.encounter_note.source_id == "note-001"
        assert case.policy.policy_id == "MHP-IMG-2201"

    def test_builds_abridge_case(self, provider, dataset, first_record):
        fixture_id = f"{ABRIDGE_FIXTURE_PREFIX}{first_record.record_id}"
        case = provider.build_case(fixture_id, case_id="case-abridge-001")
        AuthLensCase.model_validate(case.model_dump())
        assert case.patient.patient_id == first_record.patient_id
        assert case.encounter_note.text == first_record.note
        assert case.encounter_transcript.text == first_record.transcript
        assert case.patient.chart_items
        # Dataset ships no policies/orders: demo frame is reused.
        assert case.policy.policy_id == "MHP-IMG-2201"

    def test_unknown_fixture_id(self, provider):
        with pytest.raises(FixtureNotFoundError, match="unknown fixture_id"):
            provider.build_case("nope", case_id="case-x")
        with pytest.raises(FixtureNotFoundError, match="no Abridge dataset record"):
            provider.build_case(f"{ABRIDGE_FIXTURE_PREFIX}ghost", case_id="case-x")


class TestEvidenceSourceLookup:
    def test_demo_sources_cover_note_transcript_chart_and_policy(self, provider):
        sources = provider.evidence_sources(DEMO_FIXTURE_ID)
        by_id = {s.source_id: s for s in sources}
        assert by_id["note-001"].source_type == SourceType.ENCOUNTER_NOTE
        assert by_id["transcript-001"].source_type == SourceType.ENCOUNTER_TRANSCRIPT
        assert by_id["fhir-sr-mri-001"].source_type == SourceType.FHIR_RESOURCE
        assert by_id["MHP-IMG-2201"].source_type == SourceType.PAYER_POLICY
        assert "Lumbar" in by_id["MHP-IMG-2201"].content

    def test_demo_note_content_is_verbatim(self, provider):
        fixture = load_demo_fixture()
        source = provider.get_evidence_source(DEMO_FIXTURE_ID, "note-001")
        assert source.content == fixture.encounter_note.text

    def test_abridge_fhir_source_is_original_raw_resource(
        self, provider, first_record
    ):
        fixture_id = f"{ABRIDGE_FIXTURE_PREFIX}{first_record.record_id}"
        condition = first_record.encounter_fhir["related_resources"]["Condition"][0]
        source = provider.get_evidence_source(fixture_id, condition["id"])
        assert source.source_type == SourceType.FHIR_RESOURCE
        assert source.fhir_resource_type == "Condition"
        assert json.loads(source.content) == condition

    def test_lookup_is_deterministic(self, provider, first_record):
        fixture_id = f"{ABRIDGE_FIXTURE_PREFIX}{first_record.record_id}"
        first = provider.get_evidence_source(fixture_id, f"note-{first_record.encounter_id}")
        second = provider.get_evidence_source(fixture_id, f"note-{first_record.encounter_id}")
        assert first == second

    def test_unknown_source_id(self, provider):
        with pytest.raises(SourceNotFoundError, match="ghost"):
            provider.get_evidence_source(DEMO_FIXTURE_ID, "ghost")
