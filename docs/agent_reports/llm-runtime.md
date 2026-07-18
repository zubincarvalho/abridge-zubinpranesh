# Agent B (LLM runtime & prompts) — completion report

**Date:** 2026-07-18 · **Scope:** Anthropic LLM provider, deterministic mock provider, environment-driven configuration, and the versioned prompt library.

## Delivered

### `backend/app/providers/`
- `anthropic_provider.py` — `AnthropicLLMProvider`, the only module in the
  repo importing `anthropic`. Implements the frozen `LLMProvider` port:
  - `complete` — plain-text completion via `messages.create` with system
    prompt.
  - `complete_structured` — appends the output model's JSON Schema to the
    prompt, extracts/parses JSON (tolerating markdown fences), validates
    with Pydantic, and retries validation failures up to
    `max_retries` more times with a **sanitized** repair hint (error types
    and field paths only — never input values). Exhaustion raises
    `LLMStructuredOutputError`.
  - Transient failures (connection/timeout, 429, 5xx) are retried with
    exponential backoff (SDK auto-retry is disabled so attempts stay
    observable); exhaustion raises `LLMTransientError`; non-retryable API
    errors raise `LLMProviderError` immediately.
  - Extra optional keyword args `prompt_name` / `prompt_version` (defaults
    `None`) remain structurally compatible with the frozen Protocol and
    let callers tag calls with prompt identity.
  - Logs metadata only (`authlens.llm` logger): model, prompt name/version,
    latency, attempts, validation status, stop reason, token counts. Never
    prompts, completions, chain-of-thought, or the API key.
- `mock_provider.py` — `MockLLMProvider`: no network; `complete` returns a
  stable digest of (system, prompt) or a canned response; `complete_structured`
  serves registered payloads validated through the same Pydantic contract;
  records calls and the same `ProviderResponse` metadata.
- `config.py` — `LLMProviderConfig.from_env()` reading `ANTHROPIC_API_KEY`,
  `ANTHROPIC_MODEL` (default `claude-opus-4-8`), `DEMO_MODE`,
  `ANTHROPIC_TIMEOUT_SECONDS`, `ANTHROPIC_MAX_RETRIES`,
  `ANTHROPIC_MAX_TOKENS`. Does not touch the frozen `app/config.py`.
- `errors.py` — `LLMProviderError`, `LLMConfigurationError` (missing key at
  construction), `LLMTransientError`, `LLMStructuredOutputError`. SDK
  exception types never cross the port boundary.
- `response.py` — `ProviderResponse` (model, prompt name/version, latency
  ms, attempts, validation status, stop reason, token usage; deliberately
  no field for prompt/completion text). Exposed as `provider.last_response`.
- `factory.py` — `build_llm_provider()`: `DEMO_MODE` → mock, else Anthropic.

### `backend/app/prompts/`
- `registry.py` — `PromptTemplate` (name, version, description,
  **permitted_input_types**, **output_contract**, system, user template with
  strict placeholder validation) and `PromptRegistry` with pinned-version and
  latest-version lookup (`vN` natural ordering), duplicate rejection, and
  `PromptNotFoundError`.
- `library.py` — the six versioned prompts (`v1`): `policy_parsing`,
  `evidence_mapping`, `gap_detection`, `disclosure_minimization`,
  `packet_generation`, `packet_verification`. All share
  `SHARED_SAFETY_RULES` encoding the hard rules: supplied-evidence-only, no
  invented payer criteria, no diagnosis/treatment recommendations, source
  IDs + verbatim citations, missing ≠ negative evidence, referral ≠
  completion / prescription ≠ failure (weak at most), explicit uncertainty
  marking, and no chain-of-thought in output. Packet generation and
  verification both require the literal
  "Requires clinician review before submission."

### `backend/tests/providers/`
30 tests (plus 1 opt-in live test) covering: mock determinism and
structured validation; structured-output success, fence tolerance,
validation retry-then-succeed, bounded failure, sanitized errors; transient
retry-then-succeed, retry exhaustion, non-retryable short-circuit; missing
API key; response metadata; log hygiene (no key/prompt/completion in log
records); prompt version lookup, metadata completeness, and safety-rule
presence in every prompt. `test_live_integration.py` runs only with
`ANTHROPIC_API_KEY` set **and** `AUTHLENS_RUN_LIVE_LLM_TESTS=1`.

## Tests
- Command: `cd backend && uv run pytest tests/providers`
- Result: **30 passed, 1 skipped** (live test, needs credentials + opt-in).
- Frozen suite check: `uv run pytest tests/contracts` — **57 passed** (green).

## Contract-change requests
None. The frozen `LLMProvider` port was implementable as-is; prompt
identity is carried via additional optional keyword arguments, which keeps
structural compatibility with the Protocol.

## Dependency requests
See `docs/dependency_requests/llm-runtime.md` — **none**.

## Known gaps / follow-ups for integration
- **List-shaped outputs need envelope models.** `complete_structured`
  validates one Pydantic model, so stages whose logical output is
  `list[PolicyCriterion]` etc. should define a small wrapper model
  (e.g. `{"criteria": [...]}`) in their own package. Prompt
  `output_contract` metadata names the underlying frozen contract.
- **Mock provider needs canned payloads per stage.** In `DEMO_MODE` the
  factory returns a bare `MockLLMProvider`; consuming agents / the
  integration agent should register demo payloads (or construct the mock
  with `structured_responses=...`) for their stage's output models.
- `gap_detection` is a single prompt covering criterion assessment and
  clarification-question drafting; if Agent D prefers a dedicated
  clarification prompt, it can be added as a new registry entry without
  changing existing versions.
- Providers are synchronous (matching the port). If orchestration (Agent F)
  parallelizes retrieval with `asyncio`, wrap calls in a thread executor.
