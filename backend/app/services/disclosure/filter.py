"""Minimum-necessary disclosure filter (implements the DisclosureFilter port).

Rules (docs/SAFETY_AND_HUMAN_REVIEW.md rule #7):

- The default is EXCLUDE. An item is included only when its evidence is
  linked to a policy criterion by an assessment, or it is the requested
  service order itself.
- Every decision states a reason — for inclusions, which criteria need the
  item; for exclusions, why it is unrelated.
- Sensitive content is labeled with a ``phi_category`` and its reason flags
  it for clinician review, whether included or excluded.
- The filter never emits a blanket include: each candidate is reviewed
  one by one, so a broad chart dump is structurally impossible.
"""

from app.contracts import (
    AuthLensCase,
    DisclosureDecision,
    DisclosureDecisionType,
)
from app.services.disclosure.sources import (
    ResolvedSource,
    criterion_support_by_source,
    resolve_sources,
)

# Keyword heuristics for sensitive PHI categories. Matching is intentionally
# broad: a false positive only adds a human-review flag, never an automatic
# disclosure.
_SENSITIVE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "behavioral_health": (
        "depress",
        "anxiety",
        "psychiatr",
        "psycholog",
        "bipolar",
        "schizophren",
        "suicid",
        "counseling",
        "ptsd",
        "adhd",
    ),
    "substance_use": (
        "alcohol",
        "opioid",
        "substance use",
        "cannabis",
        "cocaine",
        "overdose",
        "addiction",
        "withdrawal",
    ),
    "reproductive_health": (
        "pregnan",
        "contracept",
        "abortion",
        "fertility",
        "ivf",
    ),
    "infectious_disease": (
        "hiv",
        "hepatitis",
        "syphilis",
        "gonorrhea",
        "chlamydia",
    ),
    "genetic": ("genetic test", "brca", "chromosom"),
}

_REVIEW_FLAG = "Sensitive category — flagged for clinician review of this disclosure decision."


def detect_phi_category(text: str) -> str | None:
    lowered = text.lower()
    for category, keywords in _SENSITIVE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return None


class MinimumNecessaryDisclosureFilter:
    """Deterministic minimum-necessary review over every candidate item."""

    def review(self, case: AuthLensCase) -> list[DisclosureDecision]:
        """Return one decision per candidate item; unrelated PHI is excluded."""
        sources = resolve_sources(case)
        support = criterion_support_by_source(case)
        labels = {c.criterion_id: c.label for c in case.criteria}

        decisions: list[DisclosureDecision] = []
        for index, source in enumerate(sources.values(), start=1):
            decisions.append(
                self._decide(
                    decision_id=f"dd-{index:03d}",
                    source=source,
                    criterion_ids=sorted(support.get(source.source_id, set())),
                    criterion_labels=labels,
                )
            )
        return decisions

    def _decide(
        self,
        *,
        decision_id: str,
        source: ResolvedSource,
        criterion_ids: list[str],
        criterion_labels: dict[str, str],
    ) -> DisclosureDecision:
        phi_category = detect_phi_category(source.content)

        if criterion_ids:
            named = ", ".join(
                f"{cid} ({criterion_labels[cid]})" if cid in criterion_labels else cid
                for cid in criterion_ids
            )
            plural = "criteria" if len(criterion_ids) > 1 else "criterion"
            reason = f"Needed as cited evidence for policy {plural} {named}."
            decision = DisclosureDecisionType.INCLUDE
        elif source.chart_category == "service_request":
            reason = "The requested service order itself; required to identify what is being authorized."
            decision = DisclosureDecisionType.INCLUDE
        else:
            reason = (
                "Not linked to any policy criterion for the requested service; "
                "excluded under minimum-necessary disclosure."
            )
            decision = DisclosureDecisionType.EXCLUDE

        if phi_category is not None:
            reason = f"{reason} {_REVIEW_FLAG}"

        return DisclosureDecision(
            decision_id=decision_id,
            source_id=source.source_id,
            item_description=source.label,
            decision=decision,
            reason=reason,
            phi_category=phi_category,
        )
