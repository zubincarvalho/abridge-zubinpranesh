"""LLM-backed mapper: code gates must hold regardless of what the LLM returns."""

from __future__ import annotations

from app.agents.evidence_mapper import LLMEvidenceMapper, build_evidence_mapper
from app.contracts import EvidenceConfidence
from app.providers.mock_provider import MockLLMProvider
from app.services.evidence.mapper import DeterministicEvidenceMapper
from app.services.evidence.rules import REFERRAL_LIMITATION_NOTE
from tests.evidence_readiness.conftest import make_candidate


def _envelope_payload(items):
    return {"items": items}


def _item_payload(source_id, source_type, excerpt, confidence="high", **extra):
    return {
        "evidence_id": "ev-raw-001",
        "source_id": source_id,
        "source_type": source_type,
        "excerpt": excerpt,
        "span": None,
        "fhir_path": None,
        "confidence": confidence,
        "note": None,
        **extra,
    }


def test_llm_cannot_upgrade_referral_to_high(sources, criteria_by_id):
    """Even if the model grades a referral HIGH, code caps it at LOW + note."""
    provider = MockLLMProvider(
        structured_responses={
            "EvidenceMappingEnvelope": _envelope_payload(
                [
                    _item_payload(
                        "fhir-ref-pt-001",
                        "fhir_resource",
                        "Referral to physical therapy",
                        confidence="high",
                    )
                ]
            )
        }
    )
    mapper = LLMEvidenceMapper(provider, sources)
    items = mapper.map_evidence(
        criteria_by_id["LM-3"],
        [make_candidate("LM-3", sources["fhir-ref-pt-001"], "Referral to physical therapy")],
    )
    assert len(items) == 1
    assert items[0].confidence == EvidenceConfidence.LOW
    assert items[0].note == REFERRAL_LIMITATION_NOTE


def test_llm_invented_evidence_rejected(sources, criteria_by_id):
    """Items not among the submitted candidates are dropped in code."""
    provider = MockLLMProvider(
        structured_responses={
            "EvidenceMappingEnvelope": _envelope_payload(
                [
                    _item_payload(
                        "note-001",
                        "encounter_note",
                        "Patient completed six weeks of PT without improvement",
                    )
                ]
            )
        }
    )
    mapper = LLMEvidenceMapper(provider, sources)
    items = mapper.map_evidence(
        criteria_by_id["LM-3"],
        [make_candidate("LM-3", sources["fhir-ref-pt-001"], "Referral to physical therapy")],
    )
    assert items == []


def test_llm_non_verbatim_excerpt_rejected(sources, criteria_by_id):
    """A candidate whose excerpt isn't verbatim never survives, even accepted."""
    candidate = make_candidate("LM-4", sources["note-001"], "SLR positive on the left")
    provider = MockLLMProvider(
        structured_responses={
            "EvidenceMappingEnvelope": _envelope_payload(
                [_item_payload("note-001", "encounter_note", "SLR positive on the left")]
            )
        }
    )
    mapper = LLMEvidenceMapper(provider, sources)
    assert mapper.map_evidence(criteria_by_id["LM-4"], [candidate]) == []


def test_no_candidates_no_llm_call(sources, criteria_by_id):
    provider = MockLLMProvider()
    mapper = LLMEvidenceMapper(provider, sources)
    assert mapper.map_evidence(criteria_by_id["LM-3"], []) == []
    assert provider.calls == []


def test_factory_defaults_to_deterministic(sources):
    assert isinstance(build_evidence_mapper(sources), DeterministicEvidenceMapper)
    assert isinstance(
        build_evidence_mapper(sources, MockLLMProvider()), LLMEvidenceMapper
    )
