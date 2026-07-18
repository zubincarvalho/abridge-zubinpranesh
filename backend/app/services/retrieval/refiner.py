"""Optional LLM relevance refiner (Agent C).

Runs strictly *after* deterministic filtering and is safe by construction:

- The model sees only the already-filtered candidate excerpts — never the
  full note, transcript, or chart, so a dense chart is never forwarded.
- The model may only *drop* candidates (select which candidate_ids to keep);
  it can never add text, rewrite an excerpt, or raise a confidence.
- On any provider error, or if the model keeps nothing / references unknown
  ids, the deterministic result stands unchanged (fail open to honesty).
- The refiner never judges whether a criterion is satisfied — the prompt
  forbids it and the output shape cannot express it.
"""

from typing import Protocol, Sequence

from pydantic import BaseModel, Field

from app.contracts import EvidenceCandidate, PolicyCriterion
from app.ports.llm_provider import LLMProvider


class RefinerSelection(BaseModel):
    """Typed output contract for the refiner call: ids to keep, nothing else."""

    keep_candidate_ids: list[str] = Field(default_factory=list)


class CandidateRefiner(Protocol):
    def refine(
        self, criterion: PolicyCriterion, candidates: Sequence[EvidenceCandidate]
    ) -> list[EvidenceCandidate]:
        ...


_SYSTEM = (
    "You are a retrieval relevance filter for prior-authorization documentation review. "
    "You receive one payer policy criterion and a list of evidence excerpts that were "
    "already selected by deterministic filters. Return only the candidate_ids whose "
    "excerpt text is relevant to the criterion's subject matter. Hard rules: never "
    "judge or state whether the criterion is fulfilled by the patient's record; never "
    "add, rewrite, paraphrase, or quote text beyond the given candidate_ids; a referral "
    "or prescription is never proof of completed or failed therapy; when unsure whether "
    "an excerpt is relevant, keep it."
)


class LLMCandidateRefiner:
    """Drops clearly irrelevant candidates via one bounded structured call."""

    def __init__(self, llm: LLMProvider, min_candidates_to_refine: int = 4) -> None:
        self._llm = llm
        self._min_candidates = min_candidates_to_refine

    def refine(
        self, criterion: PolicyCriterion, candidates: Sequence[EvidenceCandidate]
    ) -> list[EvidenceCandidate]:
        if len(candidates) < self._min_candidates:
            return list(candidates)
        lines = [
            f"- candidate_id={candidate.candidate_id}: {candidate.excerpt}"
            for candidate in candidates
        ]
        prompt = (
            f"Policy criterion {criterion.criterion_id} ({criterion.category}): "
            f"{criterion.requirement}\n\nCandidate excerpts:\n" + "\n".join(lines)
        )
        try:
            selection = self._llm.complete_structured(
                system=_SYSTEM,
                prompt=prompt,
                output_model=RefinerSelection,
                max_tokens=1024,
            )
        except Exception:
            return list(candidates)
        keep_ids = set(selection.keep_candidate_ids)
        kept = [candidate for candidate in candidates if candidate.candidate_id in keep_ids]
        return kept or list(candidates)
