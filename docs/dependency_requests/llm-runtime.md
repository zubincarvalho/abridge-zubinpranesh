# Dependency requests — Agent B (LLM runtime & prompts)

**None.**

The LLM runtime uses only packages already in `backend/pyproject.toml`:
`anthropic` (provider SDK — the only module importing it is
`app/providers/anthropic_provider.py`), `pydantic` (structured-output
validation), and stdlib (`json`, `time`, `hashlib`, `logging`, `os`,
`dataclasses`, `string`). Tests use the existing dev deps `pytest` and
`httpx` (to construct SDK exception objects in stubs).

A hand-rolled bounded retry loop was chosen over adding `tenacity` so the
retry count stays observable in `ProviderResponse.attempts` and no new
dependency is needed.
