"""Deterministic markdown extraction for payer policy documents (Agent C).

Extracts ``### <ID>. <label>`` criterion sections with their verbatim body
text and exact character offsets. Purely mechanical: the requirement text is
always a substring of the source document, so nothing can be invented.
"""

import re
from dataclasses import dataclass

_HEADING_RE = re.compile(
    r"^###\s+(?P<cid>[A-Z][A-Z0-9]{1,5}-\d+)\.\s+(?P<label>\S.*?)\s*$", re.MULTILINE
)
_NEXT_SECTION_RE = re.compile(r"^#{2,3}\s", re.MULTILINE)

# Multi-word markers only: a bare "if" inside an example clause must not
# reclassify a required criterion as conditional.
_CONDITIONAL_MARKERS = (
    "only if",
    "only when",
    "if applicable",
    "when applicable",
    "where applicable",
    "applies only",
    "unless",
)

_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class RawCriterionSection:
    """One ``### ID. label`` section with its verbatim body and offsets."""

    criterion_id: str
    label: str
    body: str
    heading_line: int
    heading_start: int
    body_start: int
    body_end: int


def extract_criterion_sections(policy_text: str) -> list[RawCriterionSection]:
    """Return every criterion section in document order.

    The body is the verbatim text between the heading and the next ``##`` or
    ``###`` heading (or end of document), trimmed of surrounding whitespace
    with offsets adjusted so ``policy_text[body_start:body_end] == body``.
    """
    sections: list[RawCriterionSection] = []
    for match in _HEADING_RE.finditer(policy_text):
        next_heading = _NEXT_SECTION_RE.search(policy_text, match.end())
        raw_start = match.end()
        raw_end = next_heading.start() if next_heading else len(policy_text)
        raw_body = policy_text[raw_start:raw_end]
        stripped = raw_body.strip()
        body_start = raw_start + raw_body.find(stripped) if stripped else raw_start
        body_end = body_start + len(stripped)
        sections.append(
            RawCriterionSection(
                criterion_id=match.group("cid"),
                label=match.group("label"),
                body=stripped,
                heading_line=policy_text.count("\n", 0, match.start()) + 1,
                heading_start=match.start(),
                body_start=body_start,
                body_end=body_end,
            )
        )
    return sections


def conditional_sentence(requirement: str) -> str | None:
    """Return the verbatim sentence carrying a conditionality marker, if any.

    Used to separate required from conditional criteria without paraphrasing:
    the applicability note is always exact policy language.
    """
    for sentence in _SENTENCE_BREAK_RE.split(requirement):
        lowered = sentence.lower()
        if any(marker in lowered for marker in _CONDITIONAL_MARKERS):
            return sentence.strip()
    return None
