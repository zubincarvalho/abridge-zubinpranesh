"""Resolve every addressable evidence source in a case to its content.

Shared by the disclosure filter (candidate enumeration), the packet
generator (rendering focused excerpts with source labels), and the packet
verifier (verbatim-excerpt checks). Content is always the exact stored
text of the source so ``EvidenceItem.excerpt`` substring checks are
meaningful.
"""

from dataclasses import dataclass

from app.contracts import AuthLensCase, SourceType


@dataclass(frozen=True)
class ResolvedSource:
    """One addressable source with its exact content."""

    source_id: str
    source_type: SourceType
    label: str
    content: str
    chart_category: str | None = None


def resolve_sources(case: AuthLensCase) -> dict[str, ResolvedSource]:
    """Return every addressable source in the case, keyed by source_id.

    Covers the encounter note, the transcript (when present), every chart
    item, and every recorded clinician clarification (clarifications are
    citable sources; see docs/DATA_CONTRACTS.md).
    """
    sources: dict[str, ResolvedSource] = {}

    note = case.encounter_note
    sources[note.source_id] = ResolvedSource(
        source_id=note.source_id,
        source_type=SourceType.ENCOUNTER_NOTE,
        label=note.title,
        content=note.text,
    )

    if case.encounter_transcript is not None:
        transcript = case.encounter_transcript
        sources[transcript.source_id] = ResolvedSource(
            source_id=transcript.source_id,
            source_type=SourceType.ENCOUNTER_TRANSCRIPT,
            label="Encounter transcript",
            content=transcript.text,
        )

    for item in case.patient.chart_items:
        content = item.display if item.detail is None else f"{item.display} — {item.detail}"
        sources[item.source_id] = ResolvedSource(
            source_id=item.source_id,
            source_type=SourceType.FHIR_RESOURCE,
            label=item.display,
            content=content,
            chart_category=item.category,
        )

    for clarification in case.clarifications:
        sources[clarification.clarification_id] = ResolvedSource(
            source_id=clarification.clarification_id,
            source_type=SourceType.CLINICIAN_CLARIFICATION,
            label="Clinician clarification",
            content=clarification.response,
        )

    return sources


def criterion_support_by_source(case: AuthLensCase) -> dict[str, set[str]]:
    """Map each cited source_id to the criterion ids its evidence supports."""
    support: dict[str, set[str]] = {}
    for assessment in case.assessments:
        for evidence in assessment.evidence:
            support.setdefault(evidence.source_id, set()).add(assessment.criterion_id)
    return support
