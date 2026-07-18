"""Versioned prompt registry.

Every LLM stage fetches its prompt from here by (name, version) so prompt
identity can be recorded in ProviderResponse metadata and events without
ever logging the prompt text itself.
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field


class PromptNotFoundError(KeyError):
    """Unknown prompt name or version."""


def _version_key(version: str) -> tuple[int, str]:
    # "v2" < "v10" under the vN convention (length before lexicographic).
    return (len(version), version)


@dataclass(frozen=True)
class PromptTemplate:
    """A registered prompt plus its metadata.

    ``permitted_input_types`` names the contract types (or primitive shapes)
    a caller may interpolate into the user template; ``output_contract``
    names the contract the completion must validate against.
    """

    name: str
    version: str
    description: str
    permitted_input_types: tuple[str, ...]
    output_contract: str
    system: str
    user_template: str

    @property
    def placeholders(self) -> tuple[str, ...]:
        names = [
            fname
            for _, fname, _, _ in string.Formatter().parse(self.user_template)
            if fname
        ]
        return tuple(dict.fromkeys(names))

    def render_user(self, **inputs: str) -> str:
        """Fill the user template; unknown or missing placeholders are errors."""
        expected = set(self.placeholders)
        provided = set(inputs)
        if provided != expected:
            missing = sorted(expected - provided)
            extra = sorted(provided - expected)
            raise ValueError(
                f"prompt {self.name}@{self.version} placeholder mismatch: "
                f"missing={missing} unexpected={extra}"
            )
        return self.user_template.format(**inputs)


@dataclass
class PromptRegistry:
    _prompts: dict[tuple[str, str], PromptTemplate] = field(default_factory=dict)

    def register(self, template: PromptTemplate) -> None:
        key = (template.name, template.version)
        if key in self._prompts:
            raise ValueError(f"prompt {template.name}@{template.version} already registered")
        self._prompts[key] = template

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        """Return the prompt at ``version``, or the latest version if omitted."""
        if version is not None:
            try:
                return self._prompts[(name, version)]
            except KeyError:
                raise PromptNotFoundError(f"{name}@{version}") from None
        versions = sorted((v for n, v in self._prompts if n == name), key=_version_key)
        if not versions:
            raise PromptNotFoundError(name)
        return self._prompts[(name, versions[-1])]

    def names(self) -> tuple[str, ...]:
        return tuple(sorted({name for name, _ in self._prompts}))

    def versions(self, name: str) -> tuple[str, ...]:
        versions = tuple(sorted((v for n, v in self._prompts if n == name), key=_version_key))
        if not versions:
            raise PromptNotFoundError(name)
        return versions
