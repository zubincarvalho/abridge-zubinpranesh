"""Flattened, id-indexed view over a record's FHIR context.

`encounter_fhir.related_resources` groups resources by type; this module
flattens them (plus the Encounter and Patient resources) into one indexed
collection with deterministic lookup by source id — the same ids the intake
mapping uses for `ChartItem.source_id`, so the frontend citation drawer can
resolve any cited chart item back to its original raw FHIR resource.

Reference normalization accepts the three shapes seen in FHIR data:
``urn:uuid:<id>``, ``ResourceType/<id>``, and a plain ``<id>``.
"""

import copy
import re
from dataclasses import dataclass, field

from app.data.abridge import AbridgeRecord
from app.data.errors import DuplicateIdError, MalformedDataError, UnresolvedReferenceError

_URN_UUID_PREFIX = "urn:uuid:"
# FHIR relative reference: ResourceType/<id> (id: letters, digits, -, ., max 64)
_TYPED_REFERENCE = re.compile(r"^[A-Za-z]+/[A-Za-z0-9\-\.]{1,64}$")


def normalize_reference(reference: str) -> str:
    """Reduce a FHIR reference to the bare resource id.

    ``urn:uuid:abc`` -> ``abc``; ``Patient/abc`` -> ``abc``; ``abc`` -> ``abc``.
    """
    if reference.startswith(_URN_UUID_PREFIX):
        return reference[len(_URN_UUID_PREFIX):]
    if _TYPED_REFERENCE.match(reference):
        return reference.split("/", 1)[1]
    return reference


@dataclass(frozen=True)
class IndexedResource:
    """One flattened FHIR resource. `resource` is this index's private copy."""

    source_id: str
    resource_type: str
    group: str  # the related_resources group key it came from (or its type)
    resource: dict = field(repr=False)

    @property
    def raw(self) -> dict:
        """Deep copy of the original raw FHIR resource."""
        return copy.deepcopy(self.resource)


class FhirResourceIndex:
    """Deterministic id -> resource index over one encounter's FHIR context."""

    def __init__(self, entries: list[IndexedResource], describe: str = "fhir index"):
        self.describe = describe
        self._entries = entries
        self._by_id: dict[str, IndexedResource] = {}
        for entry in entries:
            if entry.source_id in self._by_id:
                existing = self._by_id[entry.source_id]
                raise DuplicateIdError(
                    f"duplicate FHIR resource id {entry.source_id!r} in "
                    f"{describe}: {existing.resource_type} vs {entry.resource_type}"
                )
            self._by_id[entry.source_id] = entry

    # --- construction -----------------------------------------------------

    @classmethod
    def from_encounter_fhir(
        cls,
        encounter_fhir: dict,
        patient: dict | None = None,
        describe: str = "fhir index",
    ) -> "FhirResourceIndex":
        """Flatten related_resources (+ Encounter, + optional Patient)."""
        entries: list[IndexedResource] = []

        def add(resource: dict, group: str) -> None:
            if not isinstance(resource, dict) or not resource.get("id"):
                raise MalformedDataError(
                    f"{describe}: resource in group {group!r} has no 'id'"
                )
            entries.append(
                IndexedResource(
                    source_id=resource["id"],
                    resource_type=resource.get("resourceType", group),
                    group=group,
                    resource=copy.deepcopy(resource),
                )
            )

        if patient is not None:
            add(patient, "Patient")
        encounter = encounter_fhir.get("encounter")
        if encounter is not None:
            add(encounter, "Encounter")
        for group, resources in encounter_fhir.get("related_resources", {}).items():
            for resource in resources:
                add(resource, group)
        return cls(entries, describe=describe)

    @classmethod
    def from_record(cls, record: AbridgeRecord) -> "FhirResourceIndex":
        return cls.from_encounter_fhir(
            record.encounter_fhir,
            patient=record.patient_context.get("patient"),
            describe=f"record {record.record_id}",
        )

    # --- lookup -----------------------------------------------------------

    @property
    def source_ids(self) -> list[str]:
        return [entry.source_id for entry in self._entries]

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, source_id: str) -> bool:
        return source_id in self._by_id

    def get(self, source_id: str) -> IndexedResource:
        try:
            return self._by_id[source_id]
        except KeyError:
            raise UnresolvedReferenceError(
                f"no FHIR resource with id {source_id!r} in {self.describe} "
                f"({len(self._entries)} resources indexed)"
            ) from None

    def resolve_reference(self, reference: str) -> IndexedResource:
        """Resolve urn:uuid:/typed/plain references to an indexed resource."""
        source_id = normalize_reference(reference)
        try:
            return self._by_id[source_id]
        except KeyError:
            raise UnresolvedReferenceError(
                f"reference {reference!r} (normalized to {source_id!r}) does "
                f"not resolve to any resource in {self.describe}"
            ) from None

    # --- extraction helpers ----------------------------------------------

    def resources_of_type(self, resource_type: str) -> list[IndexedResource]:
        return [e for e in self._entries if e.resource_type == resource_type]

    def _single_of_type(self, resource_type: str) -> IndexedResource | None:
        matches = self.resources_of_type(resource_type)
        return matches[0] if matches else None

    def patient(self) -> IndexedResource | None:
        return self._single_of_type("Patient")

    def encounter(self) -> IndexedResource | None:
        return self._single_of_type("Encounter")

    def conditions(self) -> list[IndexedResource]:
        return self.resources_of_type("Condition")

    def medications(self) -> list[IndexedResource]:
        return self.resources_of_type("MedicationRequest")

    def procedures(self) -> list[IndexedResource]:
        return self.resources_of_type("Procedure")

    def service_requests(self) -> list[IndexedResource]:
        return self.resources_of_type("ServiceRequest")

    def observations(self) -> list[IndexedResource]:
        return self.resources_of_type("Observation")

    def diagnostic_reports(self) -> list[IndexedResource]:
        return self.resources_of_type("DiagnosticReport")
