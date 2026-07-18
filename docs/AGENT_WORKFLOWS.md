# AuthLens Agent Workflows

How AuthLens applies the patterns from Anthropic's
[Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents).
The governing decision (ADR [0001](decisions/0001-controlled-workflow.md)):
**AuthLens is a controlled workflow, not an agent swarm.** The overall
control flow is deterministic Python; LLM calls are narrow, typed stages.

## Pattern map

| Pattern | Where AuthLens uses it |
|---|---|
| Prompt chaining | Sequential stages: policy parsing → retrieval → mapping → gap detection → clarification → disclosure → packet → verification → form |
| Routing | Criterion `category` selects the retrieval/assessment strategy; service type selects the policy (single service in the demo) |
| Parallelization | Independent evidence searches, one per criterion, run concurrently |
| Evaluator–optimizer | Packet Verifier (evaluator) vs Packet Generator (optimizer) loop until zero blocking issues |
| Bounded agent loop | Only inside per-criterion retrieval, max 3 iterations, only when the first pass is uncertain |
| Deterministic orchestration | `WorkflowOrchestrator` owns sequencing, state transitions, and events; no LLM decides control flow |
| Narrow, documented tools | Each stage is a port with a typed contract in/out and a docstring stating its rules |
| Human checkpoints | (1) Clarification: the clinician answers gap questions before the packet exists. (2) Ready for Clinician Review: terminal state; a human acts outside AuthLens |

## 1. Prompt chaining (sequential workflow stages)

Each stage consumes the typed output of the previous stage and produces its
own typed artifact. Chaining lets every prompt be small, checkable, and
independently testable:

```
PayerPolicy + policy text ──PolicyParser──▶ list[PolicyCriterion]
criterion + case sources ──EvidenceRetriever──▶ list[EvidenceCandidate]
criterion + candidates ──EvidenceMapper──▶ list[EvidenceItem]
criterion + evidence + clarifications ──GapDetector──▶ CriterionAssessment
assessments ──GapDetector──▶ list[ClarificationQuestion], ReadinessSummary
case ──DisclosureFilter──▶ list[DisclosureDecision]
case (included content only) ──PacketGenerator──▶ PriorAuthorizationPacket
packet + case ──PacketVerifier──▶ VerificationResult
verified packet + verification + case ──FormDrafter──▶ PriorAuthorizationFormDraft
```

Between stages the orchestrator runs **programmatic gates** (not LLM calls):
excerpts must appear verbatim in their source; every criterion must receive
exactly one assessment; readiness is computed deterministically from
assessment counts.

## 2. Routing (service and policy categories)

- **Criterion category routing.** `PolicyCriterion.category`
  (`indication`, `duration`, `conservative_therapy`, `exam_findings`,
  `red_flags`, `functional_limitation`, `rationale`) routes each criterion to
  a category-specific retrieval query template and assessment rubric. The
  `conservative_therapy` rubric hard-codes the referral ≠ completion and
  prescription ≠ failure rules.
- **Service/policy routing.** The case's `RequestedService` selects which
  payer policy applies. The demo ships one service (lumbar MRI, CPT 72148)
  and one policy (MHP-IMG-2201); the routing seam exists so more can be added
  without changing contracts.

## 3. Parallelization (independent chart searches)

Evidence retrieval for one criterion never depends on another criterion's
results, so the orchestrator fans out one retrieval task per criterion
(sectioning) and joins before mapping. See diagram 4 in
SYSTEM_ARCHITECTURE.md. Implementations use `asyncio.gather` (or a thread
pool) — parallelism is an orchestration concern, invisible to the port.

## 4. Evaluator–optimizer (verification)

The Packet Generator (optimizer) and Packet Verifier (evaluator) are
**independent implementations with independent prompts** — the verifier is
not the generator grading its own work. The evaluator checks every claim:

1. Cited evidence exists and quotes its source verbatim.
2. The claim does not overstate the evidence (referral/prescription rules).
3. Policy claims match the parsed criteria.
4. No excluded content appears in the packet.

Any `blocking` issue → `verification_failed`; the regenerated packet
receives the issue list as input. The loop is bounded by the human operator
(each round is an explicit API call), not an autonomous retry loop.

## 5. Bounded agent loop (uncertain retrieval only)

The **only** agentic loop in AuthLens lives inside per-criterion retrieval:
if the first search pass is uncertain (no hits, or low-confidence hits for a
criterion the policy marks required), the retriever may reformulate its query
and search again, **at most 3 iterations**, then must return its honest
result. It has no other tools, cannot touch other criteria, cannot mutate
case state, and cannot extend its own budget.

## 6. Deterministic orchestration

`WorkflowOrchestrator` (Agent F) is plain Python:

- Sequences stages in fixed order per operation.
- Enforces `ALLOWED_TRANSITIONS` on every status change.
- Emits `AgentEvent` records (started/completed/failed) around every stage.
- Contains zero prompts and makes zero LLM calls itself.

## 7. Narrow, thoroughly documented tools

Every capability is a port (`backend/app/ports/`) with:

- Typed contract inputs and outputs (never raw strings between stages).
- A docstring stating the stage's purpose **and its hard rules**.
- No framework leakage (no FastAPI, no SDK types across the boundary — only
  `LLMProvider` touches the Anthropic SDK).

## 8. Human checkpoints before consequential actions

| Checkpoint | Before | Mechanism |
|---|---|---|
| Clarification | Any packet exists | `awaiting_clarification` state; questions answered by the clinician via POST /clarifications; answers recorded verbatim |
| Proceed to packet | Disclosure + packet generation | Explicit clinician-triggered POST /generate-packet (never automatic) |
| Ready for Clinician Review | Anything leaving AuthLens | Terminal state; no submission code path exists anywhere |

## Anti-patterns we explicitly rejected

- **Unconstrained agent swarm** — no self-directed agents choosing their own
  tools or spawning sub-agents (ADR 0001).
- **Generic chatbot / basic RAG** — no free-text Q&A endpoint; every LLM
  output validates against a contract or the call fails.
- **LLM-computed scores** — readiness scoring is deterministic arithmetic
  over assessment counts, so before/after comparisons are stable.
