"""Unified fixture registry: demo fixture + Abridge dataset records as cases.

Fixture ids (used by `POST /api/cases` per docs/ABRIDGE_DATASET.md):
- ``lumbar_mri_prior_auth`` — the canonical hand-authored demo case
- ``abridge:<record_id>`` — any of the 25 official dataset encounters

The provider also builds the deterministic evidence-source index for a
fixture, so `GET /api/cases/{case_id}/evidence/{source_id}` can resolve every
citable source id (note, transcript, chart items / raw FHIR resources, and
the payer policy document) without re-deriving anything.

Dataset cases get chart, note, and transcript panels fully populated; the
requested service and payer policy stay the demo lumbar-MRI ones because the
dataset ships no orders or policies (see docs/ABRIDGE_DATASET.md — policies
remain hackathon-authored).
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from app.adapters.fixture_loader import DemoFixture, load_demo_fixture
from app.config import REPO_ROOT
from app.contracts import (
    AuthLensCase,
    CaseStatus,
    EvidenceSource,
    SourceType,
)
from app.data.abridge import AbridgeDataset, AbridgeRecord, load_abridge_dataset
from app.data.errors import FixtureNotFoundError, SourceNotFoundError
from app.data.fhir_index import FhirResourceIndex
from app.data.intake_mapping import fhir_label, map_record

DEMO_FIXTURE_ID = "lumbar_mri_prior_auth"
ABRIDGE_FIXTURE_PREFIX = "abridge:"


class FixtureProvider:
    """Read-only registry of synthetic intake fixtures."""

    def __init__(
        self,
        demo_fixture_path: str | Path | None = None,
        dataset_path: str | Path | None = None,
        include_dataset: bool = True,
    ):
        self._demo_fixture_path = demo_fixture_path
        self._dataset_path = dataset_path
        self._include_dataset = include_dataset
        self._demo_fixture: DemoFixture | None = None
        self._dataset: AbridgeDataset | None = None

    # --- lazy loading -----------------------------------------------------

    def _demo(self) -> DemoFixture:
        if self._demo_fixture is None:
            self._demo_fixture = load_demo_fixture(self._demo_fixture_path)
        return self._demo_fixture

    def _abridge(self) -> AbridgeDataset:
        if self._dataset is None:
            self._dataset = load_abridge_dataset(self._dataset_path)
        return self._dataset

    def _abridge_record(self, fixture_id: str) -> AbridgeRecord:
        record_id = fixture_id[len(ABRIDGE_FIXTURE_PREFIX):]
        dataset = self._abridge()
        if record_id not in dataset:
            raise FixtureNotFoundError(
                f"no Abridge dataset record {record_id!r} "
                f"(known fixtures: {DEMO_FIXTURE_ID}, "
                f"{ABRIDGE_FIXTURE_PREFIX}<record_id>)"
            )
        return dataset.get(record_id)

    # --- registry ---------------------------------------------------------

    def list_fixture_ids(self) -> list[str]:
        fixture_ids = [DEMO_FIXTURE_ID]
        if self._include_dataset:
            fixture_ids += [
                f"{ABRIDGE_FIXTURE_PREFIX}{record_id}"
                for record_id in self._abridge().record_ids
            ]
        return fixture_ids

    def has(self, fixture_id: str) -> bool:
        if fixture_id == DEMO_FIXTURE_ID:
            return True
        if self._include_dataset and fixture_id.startswith(ABRIDGE_FIXTURE_PREFIX):
            return fixture_id[len(ABRIDGE_FIXTURE_PREFIX):] in self._abridge()
        return False

    # --- case construction ------------------------------------------------

    def build_case(
        self,
        fixture_id: str,
        case_id: str,
        now: datetime | None = None,
        status: CaseStatus = CaseStatus.INTAKE_READY,
    ) -> AuthLensCase:
        """Build an intake-stage AuthLensCase from a fixture. Never mutates sources."""
        now = now or datetime.now(timezone.utc)
        demo = self._demo()

        if fixture_id == DEMO_FIXTURE_ID:
            return AuthLensCase(
                case_id=case_id,
                status=status,
                created_at=now,
                updated_at=now,
                synthetic=True,
                patient=demo.patient,
                requested_service=demo.requested_service,
                clinical_indication=demo.clinical_indication,
                indication_codes=demo.indication_codes,
                encounter_note=demo.encounter_note,
                encounter_transcript=demo.encounter_transcript,
                policy=demo.policy,
            )

        if fixture_id.startswith(ABRIDGE_FIXTURE_PREFIX):
            record = self._abridge_record(fixture_id)
            bundle = map_record(record)
            return AuthLensCase(
                case_id=case_id,
                status=status,
                created_at=now,
                updated_at=now,
                synthetic=True,
                patient=bundle.patient,
                # The dataset ships no orders or payer policies; the demo
                # lumbar-MRI service and policy provide the assessment frame.
                requested_service=demo.requested_service,
                clinical_indication=record.metadata["visit_title"],
                indication_codes=[],
                encounter_note=bundle.note,
                encounter_transcript=bundle.transcript,
                policy=demo.policy,
            )

        raise FixtureNotFoundError(
            f"unknown fixture_id {fixture_id!r} "
            f"(known: {DEMO_FIXTURE_ID}, {ABRIDGE_FIXTURE_PREFIX}<record_id>)"
        )

    # --- evidence-source index (citation drawer) --------------------------

    def evidence_sources(self, fixture_id: str) -> list[EvidenceSource]:
        """Every citable source for a fixture, in deterministic order."""
        if fixture_id == DEMO_FIXTURE_ID:
            return self._demo_sources()
        if fixture_id.startswith(ABRIDGE_FIXTURE_PREFIX):
            return self._abridge_sources(self._abridge_record(fixture_id))
        raise FixtureNotFoundError(f"unknown fixture_id {fixture_id!r}")

    def get_evidence_source(self, fixture_id: str, source_id: str) -> EvidenceSource:
        """Deterministic lookup by source id for the frontend citation drawer."""
        for source in self.evidence_sources(fixture_id):
            if source.source_id == source_id:
                return source
        raise SourceNotFoundError(
            f"no evidence source {source_id!r} in fixture {fixture_id!r}"
        )

    def _policy_source(self) -> EvidenceSource | None:
        policy = self._demo().policy
        policy_path = REPO_ROOT / policy.source_document
        if not policy_path.is_file():
            return None
        return EvidenceSource(
            source_id=policy.policy_id,
            source_type=SourceType.PAYER_POLICY,
            label=policy.policy_title,
            content=policy_path.read_text(),
        )

    def _demo_sources(self) -> list[EvidenceSource]:
        demo = self._demo()
        sources = [
            EvidenceSource(
                source_id=demo.encounter_note.source_id,
                source_type=SourceType.ENCOUNTER_NOTE,
                label=demo.encounter_note.title,
                content=demo.encounter_note.text,
            )
        ]
        if demo.encounter_transcript is not None:
            sources.append(
                EvidenceSource(
                    source_id=demo.encounter_transcript.source_id,
                    source_type=SourceType.ENCOUNTER_TRANSCRIPT,
                    label="Encounter transcript",
                    content=demo.encounter_transcript.text,
                )
            )
        for item in demo.patient.chart_items:
            content = item.display if item.detail is None else f"{item.display}\n{item.detail}"
            sources.append(
                EvidenceSource(
                    source_id=item.source_id,
                    source_type=SourceType.FHIR_RESOURCE,
                    label=item.display,
                    content=content,
                )
            )
        policy_source = self._policy_source()
        if policy_source is not None:
            sources.append(policy_source)
        return sources

    def _abridge_sources(self, record: AbridgeRecord) -> list[EvidenceSource]:
        bundle = map_record(record)
        index = FhirResourceIndex.from_record(record)
        sources = [
            EvidenceSource(
                source_id=bundle.note.source_id,
                source_type=SourceType.ENCOUNTER_NOTE,
                label=bundle.note.title,
                content=bundle.note.text,
            ),
            EvidenceSource(
                source_id=bundle.transcript.source_id,
                source_type=SourceType.ENCOUNTER_TRANSCRIPT,
                label="Encounter transcript",
                content=bundle.transcript.text,
            ),
        ]
        for item in bundle.patient.chart_items:
            entry = index.get(item.source_id)
            sources.append(
                EvidenceSource(
                    source_id=item.source_id,
                    source_type=SourceType.FHIR_RESOURCE,
                    label=fhir_label(entry.resource),
                    # Original raw FHIR resource, pretty-printed; key order is
                    # the file's own order, so output is deterministic.
                    content=json.dumps(entry.raw, indent=2, ensure_ascii=False),
                    fhir_resource_type=entry.resource_type,
                )
            )
        policy_source = self._policy_source()
        if policy_source is not None:
            sources.append(policy_source)
        return sources
