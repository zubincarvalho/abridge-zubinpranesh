"""Loader for the official Abridge synthetic dataset.

The dataset (`synthetic-ambient-fhir-25/` at the repo root) is READ-ONLY:
this module only ever opens its files for reading and hands out deep copies,
so no caller can mutate the original records.

Supported inputs (resolved by `resolve_dataset_path` / `load_abridge_dataset`):
- a directory containing `*.jsonl` (preferred) or `*.json` record files
- a `.jsonl` file (one record per line)
- a `.json` file (array of records)
- a `.zip` archive containing either of the above

The path is configurable: explicit argument, then the
``AUTHLENS_ABRIDGE_DATASET_PATH`` environment variable, then the default
`<repo root>/synthetic-ambient-fhir-25`.
"""

import copy
import json
import os
import zipfile
from collections.abc import Iterator
from pathlib import Path

from app.config import REPO_ROOT
from app.data.errors import DatasetNotFoundError, DuplicateIdError, MalformedDataError

DATASET_PATH_ENV_VAR = "AUTHLENS_ABRIDGE_DATASET_PATH"
DEFAULT_DATASET_DIR = REPO_ROOT / "synthetic-ambient-fhir-25"

# Files in the dataset directory that are not record files.
_NON_RECORD_BASENAMES = {"summary.json", "schema.json"}

_REQUIRED_RECORD_KEYS = (
    "id",
    "metadata",
    "patient_context",
    "encounter_fhir",
    "transcript",
    "note",
    "after_visit_summary",
)


class AbridgeRecord:
    """One dataset record. The underlying dict is private and never mutated.

    Accessors return deep copies so callers can do whatever they want with
    the result without touching the loaded original.
    """

    def __init__(self, raw: dict, origin: str):
        self._raw = raw
        self.origin = origin  # file (and line) the record came from, for errors

    @property
    def record_id(self) -> str:
        return self._raw["id"]

    @property
    def patient_id(self) -> str:
        return self._raw["metadata"]["patient_id"]

    @property
    def encounter_id(self) -> str:
        return self._raw["metadata"]["encounter_id"]

    @property
    def metadata(self) -> dict:
        return copy.deepcopy(self._raw["metadata"])

    @property
    def patient_context(self) -> dict:
        return copy.deepcopy(self._raw["patient_context"])

    @property
    def encounter_fhir(self) -> dict:
        return copy.deepcopy(self._raw["encounter_fhir"])

    @property
    def transcript(self) -> str:
        return self._raw["transcript"]

    @property
    def note(self) -> str:
        return self._raw["note"]

    @property
    def after_visit_summary(self) -> str:
        return self._raw["after_visit_summary"]

    @property
    def after_visit_summary_provenance(self) -> dict | None:
        return copy.deepcopy(self._raw.get("after_visit_summary_provenance"))

    @property
    def raw(self) -> dict:
        """Deep copy of the full original record."""
        return copy.deepcopy(self._raw)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"AbridgeRecord(id={self.record_id!r})"


class AbridgeDataset:
    """An ordered, id-indexed collection of AbridgeRecords."""

    def __init__(self, records: list[AbridgeRecord], source: str):
        self.source = source
        self._records = records
        self._by_id: dict[str, AbridgeRecord] = {}
        for record in records:
            if record.record_id in self._by_id:
                raise DuplicateIdError(
                    f"duplicate record id {record.record_id!r} in {source} "
                    f"({record.origin})"
                )
            self._by_id[record.record_id] = record

    @property
    def record_ids(self) -> list[str]:
        return [record.record_id for record in self._records]

    def get(self, record_id: str) -> AbridgeRecord:
        try:
            return self._by_id[record_id]
        except KeyError:
            raise DatasetNotFoundError(
                f"no dataset record with id {record_id!r} in {self.source} "
                f"({len(self._records)} records loaded)"
            ) from None

    def __contains__(self, record_id: str) -> bool:
        return record_id in self._by_id

    def __iter__(self) -> Iterator[AbridgeRecord]:
        return iter(self._records)

    def __len__(self) -> int:
        return len(self._records)


def resolve_dataset_path(path: str | Path | None = None) -> Path:
    """Resolve the dataset location: explicit arg > env var > repo default."""
    if path is not None:
        return Path(path)
    env_value = os.environ.get(DATASET_PATH_ENV_VAR)
    if env_value:
        return Path(env_value)
    return DEFAULT_DATASET_DIR


def load_abridge_dataset(path: str | Path | None = None) -> AbridgeDataset:
    """Load the dataset from a directory, .jsonl/.json file, or .zip archive."""
    resolved = resolve_dataset_path(path)
    if not resolved.exists():
        raise DatasetNotFoundError(
            f"Abridge dataset not found at {resolved} — pass a path, set "
            f"{DATASET_PATH_ENV_VAR}, or restore {DEFAULT_DATASET_DIR}"
        )

    if resolved.is_dir():
        record_file = _pick_record_file(
            [p for p in sorted(resolved.iterdir()) if p.is_file()],
            describe=str(resolved),
        )
        raw_records = _parse_record_text(record_file.read_text(), str(record_file))
    elif resolved.suffix == ".zip":
        raw_records = _load_from_zip(resolved)
    elif resolved.suffix in (".jsonl", ".json"):
        raw_records = _parse_record_text(resolved.read_text(), str(resolved))
    else:
        raise MalformedDataError(
            f"unsupported dataset path {resolved} — expected a directory or a "
            ".jsonl/.json/.zip file"
        )

    records = [
        _validate_record(raw, origin) for raw, origin in raw_records
    ]
    return AbridgeDataset(records, source=str(resolved))


def _pick_record_file(candidates: list[Path], describe: str) -> Path:
    """Prefer .jsonl over .json; ignore summary/schema and other files."""
    jsonl = [p for p in candidates if p.suffix == ".jsonl"]
    if jsonl:
        return jsonl[0]
    json_files = [
        p
        for p in candidates
        if p.suffix == ".json" and p.name not in _NON_RECORD_BASENAMES
    ]
    if json_files:
        return json_files[0]
    raise DatasetNotFoundError(
        f"no record file (*.jsonl or *.json) found in {describe}"
    )


def _load_from_zip(archive: Path) -> list[tuple[dict, str]]:
    try:
        with zipfile.ZipFile(archive) as zf:
            names = [n for n in sorted(zf.namelist()) if not n.endswith("/")]
            member = _pick_record_file(
                [Path(n) for n in names], describe=str(archive)
            )
            # _pick_record_file returns a Path built from the member name;
            # map back to the exact archive member string.
            member_name = next(n for n in names if Path(n) == member)
            text = zf.read(member_name).decode("utf-8")
    except zipfile.BadZipFile as exc:
        raise MalformedDataError(f"{archive} is not a valid zip archive: {exc}") from exc
    return _parse_record_text(text, f"{archive}!{member_name}")


def _parse_record_text(text: str, origin: str) -> list[tuple[dict, str]]:
    """Parse .jsonl (one record per line) or .json (array) content."""
    if origin.endswith(".jsonl"):
        records: list[tuple[dict, str]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append((json.loads(line), f"{origin}:{line_number}"))
            except json.JSONDecodeError as exc:
                raise MalformedDataError(
                    f"malformed JSON on line {line_number} of {origin}: {exc.msg}"
                ) from exc
        return records

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MalformedDataError(
            f"malformed JSON in {origin}: line {exc.lineno}: {exc.msg}"
        ) from exc
    if not isinstance(parsed, list):
        raise MalformedDataError(
            f"{origin} must contain a JSON array of records, got "
            f"{type(parsed).__name__}"
        )
    return [(record, f"{origin}[{index}]") for index, record in enumerate(parsed)]


def _validate_record(raw: object, origin: str) -> AbridgeRecord:
    if not isinstance(raw, dict):
        raise MalformedDataError(
            f"record at {origin} must be a JSON object, got {type(raw).__name__}"
        )
    missing = [key for key in _REQUIRED_RECORD_KEYS if key not in raw]
    if missing:
        raise MalformedDataError(
            f"record at {origin} is missing required keys: {', '.join(missing)}"
        )
    encounter_fhir = raw["encounter_fhir"]
    if (
        not isinstance(encounter_fhir, dict)
        or "encounter" not in encounter_fhir
        or "related_resources" not in encounter_fhir
    ):
        raise MalformedDataError(
            f"record at {origin}: encounter_fhir must contain 'encounter' and "
            "'related_resources'"
        )
    return AbridgeRecord(raw, origin=origin)
