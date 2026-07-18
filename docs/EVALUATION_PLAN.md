# AuthLens Evaluation Plan

Three layers: frozen contract tests (already running), per-component tests
(parallel agents, in their own test directories), and end-to-end demo checks
(integration agent).

## Layer 1 — contract tests (frozen, run on every change)

`cd backend && uv run pytest tests/contracts` — 51 tests covering:

- Every `contracts/examples/*.json` validates against its Pydantic model.
- Evidence spans quote their sources verbatim.
- State machine: no `submitted`, terminal `ready_for_review`, no path around
  verification.
- `contracts/openapi.yaml` is valid OpenAPI, lists exactly the 12 endpoints,
  and its `CaseStatus` enum matches the contract.
- The fixture stays synthetic-labeled and preserves the LM-3 gap (the note
  must never document completed therapy).
- All contract/port modules import.

## Layer 2 — component tests (per parallel agent)

Each agent adds tests **only** in its assigned directory
(PARALLEL_EXECUTION.md). Required minimums:

| Agent | Directory | Must cover |
|---|---|---|
| A | `tests/data/` | Fixture loader builds a valid `AuthLensCase`; repository CRUD + reset; unknown-id errors |
| B | `tests/providers/` | Structured output validation + bounded retry; no-logging of prompts/completions; SDK isolation (only providers import `anthropic`) |
| C | `tests/policy_retrieval/` | Policy parses to exactly LM-1..LM-7 with faithful requirement text; retrieval returns verbatim excerpts with correct spans; bounded loop stops at 3 iterations; empty result is returned honestly |
| D | `tests/evidence_readiness/` | **Safety-critical:** referral/prescription evidence yields at most `weak` for LM-3; clarification evidence flips LM-3 to `met`; readiness formula deterministic (79 → 93 on the fixture); question wording matches the spec |
| E | `tests/output_pipeline/` | Excluded content never appears in packet or form; every clinical claim has evidence; verifier flags a deliberately overstated claim (seeded fault); form drafter raises on unverified packet |
| F | `tests/orchestration/` | Illegal transitions rejected without mutation; events emitted per stage in order; failure leaves state unchanged |
| G | `tests/api/` | Endpoint ↔ contract conformance against `openapi.yaml`; error envelope shape; status codes per API_CONTRACT.md |

LLM-dependent tests must run against a **fake LLMProvider** (deterministic
canned outputs) so the suite is offline and reproducible; live-model runs are
manual spot checks.

## Layer 3 — end-to-end demo checks (integration agent)

Scripted run of the full demo path against a live server (fake or real
provider), asserting at each step:

1. `run` → LM-3 `missing`, high risk; question text contains the six-weeks
   wording; readiness snapshot recorded.
2. `clarifications` → LM-3 `met` citing the clarification; readiness strictly
   increased; question marked `answered`.
3. `generate-packet` → allergic-rhinitis item excluded with reason; packet
   claims all carry evidence.
4. `verify` → passes on the happy path; **fault injection**: mutate a claim
   to overstate evidence and assert verification fails with a blocking issue.
5. `form-draft` → fields trace to claims; attestation present; status
   terminal; further workflow calls return 409.
6. `demo/reset` → converges to the seeded state.

## Grounding audit (manual, pre-demo)

With a live model, run the pipeline 3 times and audit: every excerpt is
verbatim (automated check), every rationale mentions only cited evidence, no
diagnosis/treatment/approval language anywhere (grep-list: "diagnos",
"should be treated", "recommend treatment", "will be approved",
"guarantee"). Record results in `docs/agent_reports/`.

## Non-goals

No accuracy benchmarks against real payer data, no latency SLOs, no load
tests — out of scope for the hackathon.
