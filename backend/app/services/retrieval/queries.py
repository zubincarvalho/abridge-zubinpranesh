"""Category-routed query plans (Agent C).

Each criterion category maps to tiers of deterministic search terms. Tiers
are cumulative and broaden: tier 1 is specific vocabulary, later tiers widen
the net. The bounded retrieval loop (max 3 iterations) walks these tiers only
when a required criterion's first pass is uncertain — see
docs/AGENT_WORKFLOWS.md §5.

``completion_terms`` exist solely for the ``conservative_therapy`` safety
rule: text that mentions therapy, a referral, or a prescription but contains
no completion/failure language can never score above LOW relevance, because a
referral is never proof of completed therapy and a prescription is never
proof of treatment failure.
"""

from dataclasses import dataclass

from app.contracts import PolicyCriterion

DURATION_ANCHOR = (
    r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|twelve|several)"
    r"\s+(?:day|week|month|year)s?\b"
)

_COMPLETION_TERMS = (
    "completed",
    "has completed",
    "finished",
    "failed",
    "failure",
    "without improvement",
    "no improvement",
    "not improved",
    "without sufficient improvement",
    "did not improve",
)


@dataclass(frozen=True)
class QueryPlan:
    """Cumulative term tiers plus anchors for one criterion category."""

    category: str
    tiers: tuple[tuple[str, ...], ...]
    anchor_patterns: tuple[str, ...] = ()
    completion_terms: tuple[str, ...] = ()


_RAW_TIERS: dict[str, tuple[tuple[str, ...], ...]] = {
    "indication": (
        ("radiculopathy", "m54", "indication", "diagnosis"),
        ("low back pain", "nerve root"),
        ("back pain", "sciatica"),
    ),
    "duration": (
        ("weeks", "months", "duration", "ongoing", "persisted"),
        ("since", "started"),
        ("chronic",),
    ),
    "conservative_therapy": (
        (
            "physical therapy",
            "naproxen",
            "nsaid",
            "anti-inflammatory",
            "home exercise",
            "home-exercise",
            "conservative",
        ),
        ("therapy", "exercise", "medication"),
        ("referral", "treatment"),
    ),
    "exam_findings": (
        (
            "straight-leg raise",
            "straight leg raise",
            "sensation",
            "reflex",
            "dermatomal",
            "motor weakness",
        ),
        ("strength", "weakness", "exam"),
        ("objective",),
    ),
    "red_flags": (
        ("trauma", "fever", "weight loss", "saddle", "bowel", "bladder", "cancer"),
        ("red flag", "red-flag"),
        ("denies",),
    ),
    "functional_limitation": (
        ("workday", "sleep", "activities of daily living", "daily living"),
        ("work", "sitting", "walking"),
        ("difficulty", "limited"),
    ),
    "rationale": (
        ("candidacy", "surgical referral", "epidural", "injection", "change management"),
        ("evaluate", "assess"),
        ("mri", "plan"),
    ),
}

_ANCHORS: dict[str, tuple[str, ...]] = {
    "duration": (DURATION_ANCHOR,),
    "indication": (r"\bm54\.\d+\b",),
    "exam_findings": (r"straight[- ]?leg raise",),
}

_STOPWORDS = frozenset(
    {"record", "documents", "documented", "criterion", "patient", "least", "should", "their"}
)


def _fallback_tier(criterion: PolicyCriterion) -> tuple[str, ...]:
    """Derive one conservative term tier from the criterion's own language."""
    words = [
        word.strip(".,;:()").lower()
        for word in (criterion.label + " " + criterion.requirement).split()
    ]
    terms: list[str] = []
    for word in words:
        if len(word) >= 5 and word not in _STOPWORDS and word not in terms:
            terms.append(word)
    return tuple(terms[:12])


def plan_for(criterion: PolicyCriterion) -> QueryPlan:
    """Return the query plan for a criterion, cumulative across tiers."""
    raw = _RAW_TIERS.get(criterion.category)
    if raw is None:
        tiers: tuple[tuple[str, ...], ...] = (_fallback_tier(criterion),)
    else:
        cumulative: list[tuple[str, ...]] = []
        merged: list[str] = []
        for tier in raw:
            merged = merged + [term for term in tier if term not in merged]
            cumulative.append(tuple(merged))
        tiers = tuple(cumulative)
    return QueryPlan(
        category=criterion.category,
        tiers=tiers,
        anchor_patterns=_ANCHORS.get(criterion.category, ()),
        completion_terms=(
            _COMPLETION_TERMS if criterion.category == "conservative_therapy" else ()
        ),
    )
