import json
import zipfile
from pathlib import Path

import pytest

from app.data.abridge import DEFAULT_DATASET_DIR, load_abridge_dataset

DATASET_DIR = DEFAULT_DATASET_DIR
JSONL_PATH = DATASET_DIR / "synthetic-ambient-fhir-25.jsonl"
JSON_PATH = DATASET_DIR / "synthetic-ambient-fhir-25.json"


@pytest.fixture(scope="session")
def dataset():
    return load_abridge_dataset()


@pytest.fixture(scope="session")
def first_record(dataset):
    return next(iter(dataset))


@pytest.fixture()
def dataset_zip(tmp_path: Path) -> Path:
    """The real dataset .jsonl repackaged into a zip archive (in tmp)."""
    archive = tmp_path / "dataset.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(JSONL_PATH, arcname="synthetic-ambient-fhir-25.jsonl")
    return archive


def minimal_record(record_id: str = "pat-1::enc-1", **overrides) -> dict:
    """A tiny structurally valid record for synthetic error-path tests."""
    record = {
        "id": record_id,
        "metadata": {
            "synthetic": True,
            "patient_id": "pat-1",
            "encounter_id": "enc-1",
            "visit_title": "Test visit",
        },
        "patient_context": {
            "patient": {
                "resourceType": "Patient",
                "id": "pat-1",
                "name": [{"given": ["Test"], "family": "Patient"}],
                "birthDate": "1980-01-01",
                "gender": "female",
            }
        },
        "encounter_fhir": {
            "encounter": {"resourceType": "Encounter", "id": "enc-1", "status": "finished"},
            "related_resources": {
                "Condition": [
                    {
                        "resourceType": "Condition",
                        "id": "cond-1",
                        "code": {"text": "Test condition"},
                        "subject": {"reference": "urn:uuid:pat-1"},
                        "encounter": {"reference": "Encounter/enc-1"},
                        "status": "active",
                    }
                ],
                "ServiceRequest": [
                    {
                        "resourceType": "ServiceRequest",
                        "id": "sr-1",
                        "code": {"coding": [{"display": "Test service request"}]},
                        "subject": {"reference": "pat-1"},
                        "status": "active",
                    }
                ],
            },
        },
        "transcript": "DR: Hello.\nPT: Hi.",
        "note": "SUBJECTIVE: test.",
        "after_visit_summary": "You were seen today.",
        "after_visit_summary_provenance": {"method": "test"},
    }
    record.update(overrides)
    return record


def write_jsonl(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path
