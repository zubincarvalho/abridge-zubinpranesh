"""Evidence Mapper agent (Agent D) — EvidenceMapper port implementation.

Maps retrieval candidates to accepted, cited EvidenceItem records for one
criterion. The LLM (via the frozen LLMProvider port and Agent B's
``evidence_mapping`` prompt) judges relevance and grades confidence; the
verbatim-citation gate and the referral/prescription safety caps are
enforced in code afterwards — an LLM answer can never weaken them.

Rejection rules (code-enforced, applied to every returned item):
- Unknown source_id → rejected.
- Excerpt not verbatim in the source → rejected.
- Item not matching any submitted candidate (source + excerpt) → rejected
  (the mapper may only accept, never invent, evidence).
- Referral/prescription-only support on a completed-therapy criterion →
  capped at LOW confidence with an explicit limitation note.
- Patient-reported statements → labeled and capped at MODERATE.

Source citations (source_id, span, fhir_path) are preserved unchanged.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from app.contracts import EvidenceCandidate, EvidenceItem, EvidenceSource, PolicyCriterion
from app.ports.llm_provider import LLMProvider
from app.services.evidence.envelopes import EvidenceMappingEnvelope
from app.services.evidence.mapper import (
    DeterministicEvidenceMapper,
    apply_safety_caps,
    criterion_key,
)
from app.services.evidence.verbatim import resolve_verbatim_span

PROMPT_NAME = "evidence_mapping"


class LLMEvidenceMapper:
    """EvidenceMapper backed by the evidence_mapping prompt + code gates."""

    def __init__(
        self,
        provider: LLMProvider,
        sources: Mapping[str, EvidenceSource],
        prompt_version: str | None = None,
    ) -> None:
        self._provider = provider
        self._sources = dict(sources)
        self._prompt_version = prompt_version

    def map_evidence(
        self, criterion: PolicyCriterion, candidates: list[EvidenceCandidate]
    ) -> list[EvidenceItem]:
        relevant = [c for c in candidates if c.criterion_id == criterion.criterion_id]
        if not relevant:
            return []
        envelope = self._provider.complete_structured(
            system=self._system_prompt(),
            prompt=self._user_prompt(criterion, relevant),
            output_model=EvidenceMappingEnvelope,
        )
        return self._enforce_gates(criterion, relevant, envelope.items)

    def _system_prompt(self) -> str:
        from app.prompts.library import PROMPT_REGISTRY

        return PROMPT_REGISTRY.get(PROMPT_NAME, self._prompt_version).system

    def _user_prompt(
        self, criterion: PolicyCriterion, candidates: list[EvidenceCandidate]
    ) -> str:
        from app.prompts.library import PROMPT_REGISTRY

        template = PROMPT_REGISTRY.get(PROMPT_NAME, self._prompt_version)
        return template.render_user(
            criterion_json=criterion.model_dump_json(),
            candidates_json=json.dumps(
                [c.model_dump(mode="json") for c in candidates], sort_keys=True
            ),
        )

    def _enforce_gates(
        self,
        criterion: PolicyCriterion,
        candidates: list[EvidenceCandidate],
        items: list[EvidenceItem],
    ) -> list[EvidenceItem]:
        candidate_keys = {(c.source_id, c.excerpt) for c in candidates}
        accepted: list[EvidenceItem] = []
        seen: set[tuple[str, str]] = set()
        key = criterion_key(criterion.criterion_id)
        for item in items:
            if (item.source_id, item.excerpt) not in candidate_keys:
                continue  # the mapper may only accept submitted candidates
            dedupe = (item.source_id, item.excerpt)
            if dedupe in seen:
                continue
            source = self._sources.get(item.source_id)
            if source is None:
                continue
            span = resolve_verbatim_span(source.content, item.excerpt, item.span)
            if span is None:
                continue  # not a verbatim quote — rejected regardless of the LLM
            seen.add(dedupe)
            renumbered = item.model_copy(
                update={
                    "evidence_id": f"ev-{key}-{len(accepted) + 1:03d}",
                    "span": span if item.span is not None or span is not None else None,
                }
            )
            accepted.append(apply_safety_caps(renumbered, criterion, source.content))
        return accepted


def build_evidence_mapper(
    sources: Mapping[str, EvidenceSource],
    provider: LLMProvider | None = None,
) -> DeterministicEvidenceMapper | LLMEvidenceMapper:
    """Default factory: deterministic mapper unless a provider is supplied."""
    if provider is None:
        return DeterministicEvidenceMapper(sources)
    return LLMEvidenceMapper(provider, sources)
