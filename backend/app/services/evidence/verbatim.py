"""Verbatim citation checks — enforced in code, before any LLM judgment.

Every accepted evidence excerpt must appear character-for-character in its
source content (docs/SAFETY_AND_HUMAN_REVIEW.md rule 8). These helpers are
the single implementation of that gate for Agent D's mapper and rubrics.
"""

from __future__ import annotations

from app.contracts import TextSpan


def span_matches(content: str, excerpt: str, span: TextSpan) -> bool:
    """True when ``content[span.start:span.end]`` equals ``excerpt`` exactly."""
    if span.start > span.end or span.end > len(content):
        return False
    return content[span.start : span.end] == excerpt


def locate(content: str, excerpt: str) -> TextSpan | None:
    """Span of the first exact occurrence of ``excerpt``, or None."""
    if not excerpt:
        return None
    index = content.find(excerpt)
    if index < 0:
        return None
    return TextSpan(start=index, end=index + len(excerpt))


def resolve_verbatim_span(
    content: str, excerpt: str, span: TextSpan | None = None
) -> TextSpan | None:
    """Verified span for a verbatim excerpt, or None when it is not verbatim.

    A provided span is trusted only if it matches; otherwise the excerpt is
    re-located. A None result means the excerpt must be rejected.
    """
    if span is not None and span_matches(content, excerpt, span):
        return span
    return locate(content, excerpt)
