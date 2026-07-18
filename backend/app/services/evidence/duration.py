"""Deterministic symptom-duration parsing from documented text.

Only explicitly written durations count. Vague temporal language
("persistent", "chronic", "ongoing") is detected separately and never
converted into a number of weeks — "persistent pain" does not prove six
weeks (docs/SAFETY_AND_HUMAN_REVIEW.md).
"""

from __future__ import annotations

import re

_WORD_NUMBERS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}

_DURATION_PATTERN = re.compile(
    r"\b(?P<num>\d+(?:\.\d+)?|" + "|".join(_WORD_NUMBERS) + r")"
    r"(?:\s*\(\d+\))?"  # e.g. "six (6) weeks"
    r"[-\s]*(?P<unit>day|week|month|year)s?\b",
    re.IGNORECASE,
)

_VAGUE_TEMPORAL_PATTERN = re.compile(
    r"\bchronic\b|\bpersistent\b|\bongoing\b|\blong-?standing\b|\bfor (?:a )?while\b",
    re.IGNORECASE,
)

# Follow-up / return-visit instructions carry a duration ("return in 4 weeks")
# that is a scheduling interval, not a statement of how long a symptom or
# therapy has lasted. Such a duration must never be counted as a symptom or
# therapy duration.
_SCHEDULING_PATTERN = re.compile(
    r"\breturn in\b|\breturn to (?:clinic|office)\b|\bfollow[-\s]?up\b|\brecheck\b|"
    r"\breassess\b|\bre-?evaluate in\b|\bnext visit\b|\bcome back\b|\bor sooner\b",
    re.IGNORECASE,
)

_DAYS_PER_UNIT = {"day": 1.0, "week": 7.0, "month": 30.44, "year": 365.25}

SIX_WEEKS_DAYS = 42.0


def parse_durations_days(text: str) -> list[float]:
    """All explicitly documented durations in ``text``, converted to days."""
    durations: list[float] = []
    for match in _DURATION_PATTERN.finditer(text):
        raw = match.group("num").lower()
        value = _WORD_NUMBERS.get(raw)
        number = float(value) if value is not None else float(raw)
        durations.append(number * _DAYS_PER_UNIT[match.group("unit").lower()])
    return durations


def has_vague_temporal_language(text: str) -> bool:
    return bool(_VAGUE_TEMPORAL_PATTERN.search(text))


def is_scheduling_statement(text: str) -> bool:
    """True if the text is a follow-up/return-visit instruction.

    A scheduling interval ("Return in 4 weeks or sooner …") is never a
    statement of symptom or therapy duration, so its duration must be
    excluded from duration assessment.
    """
    return bool(_SCHEDULING_PATTERN.search(text))


def required_days_from_requirement(requirement: str, default: float = SIX_WEEKS_DAYS) -> float:
    """The duration threshold a criterion's own text documents, else default."""
    durations = parse_durations_days(requirement)
    return min(durations) if durations else default
