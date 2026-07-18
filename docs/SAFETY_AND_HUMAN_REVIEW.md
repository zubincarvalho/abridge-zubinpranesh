# AuthLens Safety and Human Review

These rules are product requirements with the same standing as the contracts.
**No agent may weaken them** — not in code, prompts, tests, or docs. Where a
rule is machine-checkable it is enforced by frozen contract tests
(`backend/tests/contracts/`); weakening a rule includes weakening its test.

## Hard rules

| # | Rule | Enforcement |
|---|---|---|
| 1 | **No diagnosis.** AuthLens assesses documentation against a policy; it never asserts what the patient has. Indication codes are inputs from the clinician, echoed as `indication_codes`. | Prompt rules (Agent B/D); no contract field for AI-generated diagnoses exists |
| 2 | **No treatment recommendations.** Clarification questions ask what was documented/done, never what should be done. | Gap-detector prompt rules; evaluation checks (EVALUATION_PLAN.md) |
| 3 | **No approval guarantees or predictions.** `ReadinessSummary` measures documentation completeness only; UI copy and `attestation` say so explicitly. | Contract docstrings; fixed attestation text; frontend rule #3 |
| 4 | **No submission.** No submission endpoint, no `submitted` state, no config flag to add one. `ready_for_review` is terminal. | `ALLOWED_TRANSITIONS`; `test_state_machine.py::test_no_submitted_state`; `test_openapi.py::test_no_submission_endpoint` |
| 5 | **Referral ≠ completed therapy.** A referral order may support at most `weak` for a completed-therapy criterion. | GapDetector port docstring; demo fixture is built to catch violations; eval checks |
| 6 | **Prescription ≠ treatment failure.** Same rule for medications on the list. | Same as #5 |
| 7 | **No unrelated PHI exposure.** Every candidate item gets an explicit disclosure decision; the default is exclusion; the packet may contain INCLUDE'd content only; the verifier re-checks for leaks. | DisclosureFilter + PacketVerifier port rules; `test_ready_state_is_complete_and_improved` asserts an exclusion exists |
| 8 | **Source-grounded outputs only.** Every clinical claim carries `evidence_ids`; every evidence excerpt is a verbatim quote with a span; unverifiable statements are removed at verification. | `EvidenceItem` contract; verbatim-span test; verifier check #1 |
| 9 | **No chain-of-thought in logs or artifacts.** `AgentEvent.detail` is a human-readable summary; providers never log prompts or completions. | LLMProvider port rules; events contract docstring |
| 10 | **Not a chatbot / not basic RAG.** No free-text conversational endpoint; every LLM output must validate against a typed contract. | API surface (fixed endpoint list); `complete_structured` validation |

## The two human checkpoints

1. **Clarification (before any packet exists).** Analysis halts in
   `awaiting_clarification`. The clinician — not the model — decides whether
   to answer questions or proceed. Answers are recorded **verbatim** as
   `ClinicianClarification` and become citable evidence attributed to the
   clinician, never paraphrased into the note.
2. **Ready for Clinician Review (terminal).** The verified packet and mock
   form stop here. Any real-world action (reviewing, editing, submitting via
   the payer's own channel) is a human act outside AuthLens.

## The machine gate: verification

Between packet generation and the form draft, an independent verifier checks
**every** claim (see SYSTEM_ARCHITECTURE.md §5). The `FormDrafter` port
accepts only a `verified` packet plus its passing `VerificationResult` and
must raise otherwise — there is no code path from unverified text to the
form.

## Failure posture

- A stage failure marks the event `failed` and leaves case status unchanged
  (no partial transitions).
- Verification failures are **expected outcomes**, not errors: HTTP 200 with
  `verification_failed`, with issues and suggested resolutions rendered for
  the human.
- When evidence is absent, the honest output is `missing` plus a
  clarification question — never an inferred fact.

## Data handling (demo scope)

All patient data in this repository is synthetic and labeled
(ADR [0004](decisions/0004-synthetic-demo-fixture.md)). No real PHI may be
added to the repo. The disclosure-review machinery exists so the design is
right when real data ever enters the picture — but the demo never uses any.
