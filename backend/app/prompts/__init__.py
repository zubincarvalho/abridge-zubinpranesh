"""AuthLens versioned prompt library (Agent B).

Usage::

    from app.prompts import PROMPT_REGISTRY
    template = PROMPT_REGISTRY.get("gap_detection")          # latest version
    template = PROMPT_REGISTRY.get("gap_detection", "v1")    # pinned version
"""

from app.prompts.library import (
    CLINICIAN_REVIEW_NOTICE,
    PROMPT_REGISTRY,
    REQUIRED_PROMPT_NAMES,
    SHARED_SAFETY_RULES,
)
from app.prompts.registry import PromptNotFoundError, PromptRegistry, PromptTemplate

__all__ = [
    "CLINICIAN_REVIEW_NOTICE",
    "PROMPT_REGISTRY",
    "PromptNotFoundError",
    "PromptRegistry",
    "PromptTemplate",
    "REQUIRED_PROMPT_NAMES",
    "SHARED_SAFETY_RULES",
]
