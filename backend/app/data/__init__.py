"""Agent A — data loading for AuthLens.

This package owns loading of the official Abridge synthetic dataset
(`synthetic-ambient-fhir-25/`, repo root, READ-ONLY) and the mapping of its
records into the frozen intake contracts. The reference mapping specification
is `backend/tests/contracts/test_abridge_dataset.py`; if this package and
that test disagree, the test is authoritative.
"""

from app.data.abridge import (
    AbridgeDataset,
    AbridgeRecord,
    load_abridge_dataset,
    resolve_dataset_path,
)
from app.data.errors import (
    DataError,
    DatasetNotFoundError,
    DuplicateIdError,
    FixtureNotFoundError,
    MalformedDataError,
    SourceNotFoundError,
    UnresolvedReferenceError,
)
from app.data.fhir_index import FhirResourceIndex, IndexedResource, normalize_reference
from app.data.intake_mapping import (
    CATEGORY_BY_RESOURCE_TYPE,
    IntakeBundle,
    fhir_label,
    map_record,
)

__all__ = [
    "AbridgeDataset",
    "AbridgeRecord",
    "CATEGORY_BY_RESOURCE_TYPE",
    "DataError",
    "DatasetNotFoundError",
    "DuplicateIdError",
    "FhirResourceIndex",
    "FixtureNotFoundError",
    "IndexedResource",
    "IntakeBundle",
    "MalformedDataError",
    "SourceNotFoundError",
    "UnresolvedReferenceError",
    "fhir_label",
    "load_abridge_dataset",
    "map_record",
    "normalize_reference",
    "resolve_dataset_path",
]
