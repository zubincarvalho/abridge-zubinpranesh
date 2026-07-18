"""Evidence Mapper tests: verbatim gate, citation preservation, safety caps."""

from __future__ import annotations

from app.contracts import EvidenceConfidence, TextSpan
from app.services.evidence.mapper import DeterministicEvidenceMapper
from app.services.evidence.rules import (
    PRESCRIPTION_LIMITATION_NOTE,
    REFERRAL_LIMITATION_NOTE,
)
from tests.evidence_readiness.conftest import make_candidate


def test_citations_preserved(sources, criteria_by_id):
    """Accepted evidence carries source_id, verbatim excerpt, and a valid span."""
    mapper = DeterministicEvidenceMapper(sources)
    note = sources["note-001"]
    excerpt = "Straight-leg raise is positive on the left at 40 degrees"
    items = mapper.map_evidence(
        criteria_by_id["LM-4"],
        [make_candidate("LM-4", note, excerpt, EvidenceConfidence.HIGH)],
    )
    assert len(items) == 1
    item = items[0]
    assert item.source_id == "note-001"
    assert item.excerpt == excerpt
    assert item.span is not None
    assert note.content[item.span.start : item.span.end] == excerpt


def test_non_verbatim_excerpt_rejected(sources, criteria_by_id):
    """A paraphrase that does not appear character-for-character is rejected."""
    mapper = DeterministicEvidenceMapper(sources)
    note = sources["note-001"]
    items = mapper.map_evidence(
        criteria_by_id["LM-4"],
        [make_candidate("LM-4", note, "SLR positive left 40 deg on exam")],
    )
    assert items == []


def test_wrong_span_is_relocated_not_trusted(sources, criteria_by_id):
    """A candidate with a bad span but a verbatim excerpt gets a corrected span."""
    mapper = DeterministicEvidenceMapper(sources)
    note = sources["note-001"]
    excerpt = "Straight-leg raise is positive on the left at 40 degrees"
    candidate = make_candidate("LM-4", note, excerpt, EvidenceConfidence.HIGH)
    candidate = candidate.model_copy(update={"span": TextSpan(start=0, end=5)})
    items = mapper.map_evidence(criteria_by_id["LM-4"], [candidate])
    assert len(items) == 1
    span = items[0].span
    assert note.content[span.start : span.end] == excerpt


def test_unsupported_evidence_rejected(sources, criteria_by_id):
    """Evidence with no relevance signal for the criterion is not mapped."""
    mapper = DeterministicEvidenceMapper(sources)
    allergy = sources["fhir-cond-002"]  # seasonal allergic rhinitis
    items = mapper.map_evidence(
        criteria_by_id["LM-3"],
        [make_candidate("LM-3", allergy, "Seasonal allergic rhinitis")],
    )
    assert items == []


def test_unknown_source_rejected(sources, criteria_by_id):
    mapper = DeterministicEvidenceMapper(sources)
    note = sources["note-001"]
    candidate = make_candidate("LM-4", note, "Straight-leg raise is positive")
    candidate = candidate.model_copy(update={"source_id": "note-does-not-exist"})
    assert mapper.map_evidence(criteria_by_id["LM-4"], [candidate]) == []


def test_referral_capped_low_with_limitation_note(sources, criteria_by_id):
    """A PT referral maps to the therapy criterion at LOW with an explicit limit."""
    mapper = DeterministicEvidenceMapper(sources)
    referral = sources["fhir-ref-pt-001"]
    items = mapper.map_evidence(
        criteria_by_id["LM-3"],
        [
            make_candidate(
                "LM-3", referral, "Referral to physical therapy", EvidenceConfidence.HIGH
            )
        ],
    )
    assert len(items) == 1
    assert items[0].confidence == EvidenceConfidence.LOW
    assert items[0].note == REFERRAL_LIMITATION_NOTE


def test_prescription_capped_low_with_limitation_note(sources, criteria_by_id):
    mapper = DeterministicEvidenceMapper(sources)
    med = sources["fhir-med-001"]
    items = mapper.map_evidence(
        criteria_by_id["LM-3"],
        [
            make_candidate(
                "LM-3",
                med,
                "Naproxen 500 mg twice daily (NSAID)",
                EvidenceConfidence.HIGH,
            )
        ],
    )
    assert len(items) == 1
    assert items[0].confidence == EvidenceConfidence.LOW
    assert items[0].note == PRESCRIPTION_LIMITATION_NOTE
