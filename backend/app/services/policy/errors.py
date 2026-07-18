"""Errors raised by the deterministic policy parsing service (Agent C).

Parsing fails loudly rather than guessing: an unsupported policy, a
duplicate criterion id, or a criterion without citable source text is an
error — never a silently invented or dropped requirement.
"""


class PolicyParseError(ValueError):
    """Base error for policy parsing failures."""


class UnsupportedPolicyError(PolicyParseError):
    """No registered route matches the given payer policy."""


class DuplicateCriterionError(PolicyParseError):
    """The policy text declares the same criterion id more than once."""


class MissingCitationError(PolicyParseError):
    """A criterion heading has no requirement text to cite."""
