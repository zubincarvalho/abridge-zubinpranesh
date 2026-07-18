"""Deterministic sentence-level text search (Agent C).

Splits source text into sentences with exact character offsets and matches
lowercase query terms. Every hit is a verbatim slice of the source:
``text[hit.sentence.start:hit.sentence.end] == hit.sentence.text`` always
holds, which is what makes downstream citations verifiable.
"""

import re
from dataclasses import dataclass

_SENTENCE_BREAK_RE = re.compile(r"(?<=[.!?])\s+|\n+")

# Cues that a sentence records something as explicitly absent. Only used to
# flag documented negative clinical findings — never to discard a hit.
_NEGATION_CUES = ("denies", "denied", "no ", "no,", "not ", "without", "negative")


@dataclass(frozen=True)
class Sentence:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class TextHit:
    sentence: Sentence
    matched_terms: tuple[str, ...]
    anchor_matched: bool
    negated: bool


def iter_sentences(text: str) -> list[Sentence]:
    """Split ``text`` into trimmed sentences with verbatim offsets."""
    sentences: list[Sentence] = []
    cursor = 0
    boundaries = [match.span() for match in _SENTENCE_BREAK_RE.finditer(text)]
    boundaries.append((len(text), len(text)))
    for break_start, break_end in boundaries:
        segment = text[cursor:break_start]
        stripped = segment.strip()
        if stripped:
            start = cursor + segment.find(stripped)
            sentences.append(Sentence(text=stripped, start=start, end=start + len(stripped)))
        cursor = break_end
    return sentences


def find_text_hits(
    text: str, terms: tuple[str, ...], anchor_patterns: tuple[str, ...] = ()
) -> list[TextHit]:
    """Return sentences matching at least one term or anchor pattern."""
    compiled_anchors = [re.compile(pattern, re.IGNORECASE) for pattern in anchor_patterns]
    hits: list[TextHit] = []
    for sentence in iter_sentences(text):
        lowered = sentence.text.lower()
        matched = tuple(term for term in terms if term in lowered)
        anchor_matched = any(anchor.search(sentence.text) for anchor in compiled_anchors)
        if not matched and not anchor_matched:
            continue
        negated = any(cue in lowered for cue in _NEGATION_CUES)
        hits.append(
            TextHit(
                sentence=sentence,
                matched_terms=matched,
                anchor_matched=anchor_matched,
                negated=negated,
            )
        )
    return hits
