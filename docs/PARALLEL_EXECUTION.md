# AuthLens Parallel Execution Plan

Seven parallel agents build on the frozen foundation, each inside a strict
file-ownership boundary. Ownership is **complete and non-overlapping**: if a
path is not yours, you do not edit it — no exceptions, including "trivial"
fixes.

## Frozen after the foundation phase (read-only for ALL parallel agents)

| Path | Why |
|---|---|
| `backend/app/contracts/**` | Shared typed contracts |
| `backend/app/ports/**` | Shared interfaces |
| `contracts/**` | OpenAPI + validated examples (frontend depends on them) |
| `data/fixtures/**` | Demo fixture (tests + demo depend on exact content) |
| `data/policies/**` | Demo policy (criterion text is load-bearing) |
| `synthetic-ambient-fhir-25/**` | **Official Abridge dataset — read-only for everyone, including the integration agent.** Loaded, never modified |
| `backend/pyproject.toml` | Shared manifest — see DEPENDENCY_POLICY.md |
| `backend/tests/contracts/**` | Frozen invariant tests (incl. safety rules) |
| `backend/app/config.py`, `backend/app/__init__.py` | Shared app skeleton |
| `docs/*.md`, `docs/decisions/**` | Foundation docs (agents write only in their two files below) |
| `CLAUDE.md`, `README.md` | Repo governance |

Need a change to a frozen file? Document it in **your agent report**
(what, why, exact proposed diff). Only the integration agent applies it.

## Ownership table

| Agent | Scope | Owns (exclusive write access) |
|---|---|---|
| **A — Data & FHIR** | Fixture/FHIR loading, repositories | `backend/app/adapters/**` · `backend/app/repositories/**` · `backend/app/data/**` · `backend/scripts/**` · `backend/tests/data/**` · `docs/agent_reports/data-and-fhir.md` · `docs/dependency_requests/data-and-fhir.md` |
| **B — LLM runtime & prompts** | Anthropic provider, prompt library | `backend/app/providers/**` · `backend/app/prompts/**` · `backend/tests/providers/**` · `docs/agent_reports/llm-runtime.md` · `docs/dependency_requests/llm-runtime.md` |
| **C — Policy & retrieval** | Policy parsing, evidence retrieval | `backend/app/services/policy/**` · `backend/app/services/retrieval/**` · `backend/app/agents/policy_parser.py` · `backend/app/agents/evidence_retriever.py` · `backend/tests/policy_retrieval/**` · `docs/agent_reports/policy-and-retrieval.md` · `docs/dependency_requests/policy-and-retrieval.md` |
| **D — Evidence, gaps, readiness, clarification** | Mapping, assessment, questions, scoring | `backend/app/services/evidence/**` · `backend/app/services/readiness/**` · `backend/app/services/clarifications/**` · `backend/app/agents/evidence_mapper.py` · `backend/app/agents/gap_detector.py` · `backend/tests/evidence_readiness/**` · `docs/agent_reports/evidence-and-readiness.md` · `docs/dependency_requests/evidence-and-readiness.md` |
| **E — Disclosure, packet, verification, form** | Output pipeline | `backend/app/services/disclosure/**` · `backend/app/services/packet/**` · `backend/app/services/verification/**` · `backend/app/services/form_draft/**` · `backend/app/agents/disclosure_agent.py` · `backend/app/agents/packet_generator.py` · `backend/app/agents/verification_agent.py` · `backend/tests/output_pipeline/**` · `docs/agent_reports/output-pipeline.md` · `docs/dependency_requests/output-pipeline.md` |
| **F — Orchestration, cases, timeline** | Workflow engine, state machine enforcement, events | `backend/app/orchestration/**` · `backend/app/services/cases/**` · `backend/app/events/**` · `backend/tests/orchestration/**` · `docs/agent_reports/orchestration.md` · `docs/dependency_requests/orchestration.md` |
| **G — API** | FastAPI app, routes, wiring surface | `backend/app/api/**` · `backend/app/main.py` · `backend/app/api_dependencies.py` · `backend/tests/api/**` · `docs/agent_reports/api.md` · `docs/dependency_requests/api.md` |

Shared parents (`backend/app/services/`, `backend/app/agents/`,
`backend/tests/`) are namespace directories: agents create only their listed
children. `__init__.py` files inside an agent's owned subtree belong to that
agent. `backend/app/agents/__init__.py` and `backend/app/services/__init__.py`
are created by the **integration agent** (keep them empty until then;
import your modules by full path).

## Integration agent

Runs **only after** all parallel branches are complete. Exclusively owns:

- Dependency wiring (implementations bound to ports in
  `app/api_dependencies.py` review + composition fixes)
- Applying approved dependency requests to `backend/pyproject.toml`
- Applying approved contract/port change requests
- Conflict resolution across branches; shared `__init__.py` files
- End-to-end testing (EVALUATION_PLAN.md layer 3)
- Final documentation updates

## Non-conflict rules (restated, binding)

1. Frozen paths above are read-only for parallel agents.
2. No agent edits files owned by another agent.
3. Contract/port changes → documented in your agent report, not made.
4. New dependency → written to **your** `docs/dependency_requests/<agent>.md`
   file (never edit `pyproject.toml`).
5. Tests go only in your assigned test directory.
6. Every agent finishes by writing its completion report
   (template: `docs/agent_reports/README.md`).

## Interface seams (who depends on whom)

All cross-agent dependencies flow through frozen contracts and ports only:

```
G (api) ──▶ F (orchestrator port) ──▶ C, D, E (stage ports) ──▶ B (LLMProvider)
                    │
                    └──▶ A (CaseRepository, fixture loading)
```

Because every seam is a frozen Protocol, agents develop against fakes and
never need another agent's branch to compile or test.
