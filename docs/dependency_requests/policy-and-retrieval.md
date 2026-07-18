# Dependency requests — Agent C (policy & retrieval)

None. Agent C uses only the standard library (`re`, `dataclasses`, `enum`,
`concurrent.futures`), Pydantic (already in `backend/pyproject.toml`), and the
frozen contracts/ports. The optional LLM refiner goes through the
`LLMProvider` port and never imports `anthropic`.
