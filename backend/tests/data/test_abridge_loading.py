"""Loading the official Abridge dataset: formats, config, immutability, errors."""

import json

import pytest

from app.data import (
    DatasetNotFoundError,
    DuplicateIdError,
    MalformedDataError,
    load_abridge_dataset,
    resolve_dataset_path,
)
from app.data.abridge import DATASET_PATH_ENV_VAR, DEFAULT_DATASET_DIR
from tests.data.conftest import (
    DATASET_DIR,
    JSON_PATH,
    JSONL_PATH,
    minimal_record,
    write_jsonl,
)


class TestPathResolution:
    def test_default_is_repo_dataset_dir(self, monkeypatch):
        monkeypatch.delenv(DATASET_PATH_ENV_VAR, raising=False)
        assert resolve_dataset_path() == DEFAULT_DATASET_DIR

    def test_env_var_overrides_default(self, monkeypatch, tmp_path):
        monkeypatch.setenv(DATASET_PATH_ENV_VAR, str(tmp_path))
        assert resolve_dataset_path() == tmp_path

    def test_explicit_path_overrides_env_var(self, monkeypatch, tmp_path):
        monkeypatch.setenv(DATASET_PATH_ENV_VAR, "/nowhere")
        assert resolve_dataset_path(tmp_path) == tmp_path

    def test_loading_via_env_var(self, monkeypatch):
        monkeypatch.setenv(DATASET_PATH_ENV_VAR, str(JSONL_PATH))
        assert len(load_abridge_dataset()) == 25


class TestOfficialDatasetLoads:
    def test_directory_load_finds_jsonl(self, dataset):
        assert len(dataset) == 25
        assert dataset.source == str(DATASET_DIR)

    def test_jsonl_and_json_agree(self):
        from_jsonl = load_abridge_dataset(JSONL_PATH)
        from_json = load_abridge_dataset(JSON_PATH)
        assert from_jsonl.record_ids == from_json.record_ids
        first = from_jsonl.record_ids[0]
        assert from_jsonl.get(first).raw == from_json.get(first).raw

    def test_zip_load(self, dataset_zip, dataset):
        from_zip = load_abridge_dataset(dataset_zip)
        assert from_zip.record_ids == dataset.record_ids

    def test_record_accessors_and_lookup(self, dataset, first_record):
        record = dataset.get(first_record.record_id)
        assert record.record_id == f"{record.patient_id}::{record.encounter_id}"
        assert record.metadata["synthetic"] is True
        assert record.note.strip() and record.transcript.strip()
        assert record.after_visit_summary.strip()
        assert isinstance(record.after_visit_summary_provenance, dict)
        assert "related_resources" in record.encounter_fhir
        assert record.patient_context["patient"]["resourceType"] == "Patient"

    def test_unknown_record_id_raises(self, dataset):
        with pytest.raises(DatasetNotFoundError, match="no-such-record"):
            dataset.get("no-such-record")


class TestOriginalRecordsNeverModified:
    def test_mutating_accessor_results_does_not_leak_back(self, dataset, first_record):
        raw_before = first_record.raw

        meta = first_record.metadata
        meta["visit_title"] = "TAMPERED"
        fhir = first_record.encounter_fhir
        fhir["related_resources"].clear()
        raw_copy = first_record.raw
        raw_copy["note"] = "TAMPERED"

        assert first_record.raw == raw_before
        assert first_record.metadata["visit_title"] != "TAMPERED"
        assert dataset.get(first_record.record_id).encounter_fhir["related_resources"]

    def test_dataset_files_on_disk_untouched(self, dataset):
        # Loading must never rewrite the official files.
        on_disk = [
            json.loads(line)
            for line in JSONL_PATH.read_text().splitlines()
            if line.strip()
        ]
        assert [r["id"] for r in on_disk] == dataset.record_ids


class TestMalformedInputs:
    def test_missing_path_raises_with_guidance(self, tmp_path):
        with pytest.raises(DatasetNotFoundError, match=DATASET_PATH_ENV_VAR):
            load_abridge_dataset(tmp_path / "nope")

    def test_directory_without_record_files(self, tmp_path):
        (tmp_path / "schema.json").write_text("{}")
        with pytest.raises(DatasetNotFoundError, match="no record file"):
            load_abridge_dataset(tmp_path)

    def test_malformed_jsonl_reports_line(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text(json.dumps(minimal_record()) + "\n{not json\n")
        with pytest.raises(MalformedDataError, match="line 2"):
            load_abridge_dataset(path)

    def test_malformed_json_array(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text('{"not": "an array"}')
        with pytest.raises(MalformedDataError, match="array"):
            load_abridge_dataset(path)

    def test_missing_required_keys(self, tmp_path):
        record = minimal_record()
        del record["transcript"]
        with pytest.raises(MalformedDataError, match="transcript"):
            load_abridge_dataset(write_jsonl(tmp_path / "r.jsonl", [record]))

    def test_duplicate_record_ids(self, tmp_path):
        records = [minimal_record(), minimal_record()]
        with pytest.raises(DuplicateIdError, match="pat-1::enc-1"):
            load_abridge_dataset(write_jsonl(tmp_path / "r.jsonl", records))

    def test_unsupported_suffix(self, tmp_path):
        path = tmp_path / "records.csv"
        path.write_text("id\n")
        with pytest.raises(MalformedDataError, match="unsupported"):
            load_abridge_dataset(path)

    def test_bad_zip(self, tmp_path):
        path = tmp_path / "bad.zip"
        path.write_bytes(b"this is not a zip")
        with pytest.raises(MalformedDataError, match="zip"):
            load_abridge_dataset(path)
