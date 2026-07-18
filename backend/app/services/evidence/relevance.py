"""Deterministic relevance signals: does an excerpt bear on a category at all?

The mapper rejects any candidate with no relevance signal for its
criterion's category — unsupported mappings never become cited evidence.
Signals are transparent keyword/pattern checks, not judgments of strength;
strength is graded separately as confidence.
"""

from __future__ import annotations

from app.services.evidence.duration import has_vague_temporal_language, parse_durations_days
from app.services.evidence.rules import contains_diagnosis_code

CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "indication": (
        "radiculopathy",
        "low back pain",
        "indication",
        "diagnosis",
        "stenosis",
        "herniation",
    ),
    "duration": ("ongoing", "since", "chronic", "persistent", "week", "month", "year", "day"),
    "conservative_therapy": (
        "physical therapy",
        "therapy",
        "nsaid",
        "naproxen",
        "ibuprofen",
        "anti-inflammatory",
        "home-exercise",
        "home exercise",
        "conservative",
        "medication",
        "referral",
        "chiropractic",
    ),
    "exam_findings": (
        "straight-leg",
        "straight leg",
        "sensation",
        "strength",
        "reflex",
        "exam",
        "motor",
        "dermatomal",
        "tenderness",
        "range of motion",
        "radiculopathy",
    ),
    "red_flags": (
        "denies",
        "trauma",
        "fever",
        "weight loss",
        "saddle",
        "bowel",
        "bladder",
        "cancer",
        "red flag",
        "red-flag",
        "infection",
        "malignancy",
    ),
    "functional_limitation": (
        "work",
        "sleep",
        "daily",
        "activities",
        "function",
        "sitting",
        "standing",
        "walking",
        "adl",
    ),
    "rationale": (
        "mri",
        "evaluate",
        "assess",
        "candidacy",
        "surgical",
        "injection",
        "management",
        "guide",
        "imaging",
    ),
}


def has_relevance_signal(category: str, excerpt: str) -> bool:
    """True when the excerpt shows a deterministic signal for the category."""
    lowered = excerpt.lower()
    if any(keyword in lowered for keyword in CATEGORY_KEYWORDS.get(category, ())):
        return True
    if category == "duration":
        return bool(parse_durations_days(excerpt)) or has_vague_temporal_language(excerpt)
    if category in ("indication", "exam_findings"):
        return contains_diagnosis_code(excerpt)
    return False
