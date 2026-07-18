"""Adapter for the hand-authored demo fixture.

Loads `data/fixtures/lumbar_mri_prior_auth.json` (frozen, synthetic,
hackathon-authored) and validates every section against the frozen intake
contracts. The fixture file is read-only; underscore-prefixed annotation keys
(`_synthetic_notice`, `_gap_note`) and the demo hint
(`expected_demo_clarification`) are ignored by the adapter.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.config import get_settings
from app.contracts import (
    EncounterNote,
    EncounterTranscript,
    PatientSummary,
    PayerPolicy,
    RequestedService,
)
from app.data.errors import DatasetNotFoundError, MalformedDataError


@dataclass(frozen=True)
class DemoFixture:
    """Validated intake content of one demo fixture file."""

    fixture_id: str
    synthetic: bool
    patient: PatientSummary
    encounter_note: EncounterNote
    encounter_transcript: EncounterTranscript | None
    requested_service: RequestedService
    clinical_indication: str
    indication_codes: list[str]
    policy: PayerPolicy


def load_demo_fixture(path: str | Path | None = None) -> DemoFixture:
    """Load and validate a demo fixture JSON file.

    Defaults to `Settings.demo_fixture_path` (overridable via the
    ``AUTHLENS_DEMO_FIXTURE_PATH`` environment variable).
    """
    resolved = Path(path) if path is not None else get_settings().demo_fixture_path
    if not resolved.exists():
        raise DatasetNotFoundError(f"demo fixture not found at {resolved}")

    try:
        data = json.loads(resolved.read_text())
    except json.JSONDecodeError as exc:
        raise MalformedDataError(
            f"malformed JSON in fixture {resolved}: line {exc.lineno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise MalformedDataError(f"fixture {resolved} must be a JSON object")

    required = (
        "fixture_id",
        "patient",
        "encounter_note",
        "requested_service",
        "clinical_indication",
        "policy",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise MalformedDataError(
            f"fixture {resolved} is missing required keys: {', '.join(missing)}"
        )

    # Annotation keys (leading underscore) never reach the contracts.
    note_raw = {
        k: v for k, v in data["encounter_note"].items() if not k.startswith("_")
    }
    transcript_raw = data.get("encounter_transcript")

    try:
        return DemoFixture(
            fixture_id=data["fixture_id"],
            synthetic=bool(data.get("synthetic", True)),
            patient=PatientSummary.model_validate(data["patient"]),
            encounter_note=EncounterNote.model_validate(note_raw),
            encounter_transcript=(
                EncounterTranscript.model_validate(transcript_raw)
                if transcript_raw is not None
                else None
            ),
            requested_service=RequestedService.model_validate(
                data["requested_service"]
            ),
            clinical_indication=data["clinical_indication"],
            indication_codes=list(data.get("indication_codes", [])),
            policy=PayerPolicy.model_validate(data["policy"]),
        )
    except ValidationError as exc:
        raise MalformedDataError(
            f"fixture {resolved} does not satisfy the intake contracts: {exc}"
        ) from exc
