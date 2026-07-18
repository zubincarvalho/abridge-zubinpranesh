# AuthLens System Architecture

Backend-first FastAPI service. Deterministic Python orchestration calls
narrow, typed LLM stages through ports; all state is typed contracts; the
frontend renders everything from the case-state response.

Principles (per Anthropic's [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)):
deterministic orchestration for the overall workflow; prompt chaining for
sequential stages; routing by criterion category; parallelization for
independent chart searches; evaluator–optimizer for verification; a bounded
agent loop only for uncertain retrieval; narrow documented tools; human
checkpoints before consequential actions. Details in
[AGENT_WORKFLOWS.md](AGENT_WORKFLOWS.md).

## 1. Component architecture

```mermaid
flowchart LR
    subgraph Frontend["Clinical Workflow Console (separate build)"]
        UI[React console]
    end

    subgraph API["backend/app/api (Agent G)"]
        R[FastAPI routes]
    end

    subgraph Orchestration["backend/app/orchestration (Agent F)"]
        WO[Workflow Orchestrator<br/>deterministic Python]
        EV[Event log / timeline]
        CS[Case service + state machine]
    end

    subgraph Stages["LLM-backed stages (Agents C, D, E)"]
        PP[Policy Parser]
        ER[Evidence Retriever<br/>parallel per criterion]
        EM[Evidence Mapper]
        GD[Gap Detector +<br/>Clarifications + Readiness]
        DF[Disclosure Filter]
        PG[Packet Generator]
        PV[Packet Verifier]
        FD[Form Drafter]
    end

    subgraph Runtime["backend/app/providers (Agent B)"]
        LLM[LLM Provider<br/>Anthropic SDK]
    end

    subgraph Data["backend/app/adapters + repositories (Agent A)"]
        REPO[Case Repository]
        FIX[Fixture loader<br/>data/fixtures + data/policies]
    end

    UI -->|JSON per contracts/openapi.yaml| R
    R --> WO
    WO --> CS --> REPO
    WO --> EV
    WO --> PP & ER & EM & GD & DF & PG & PV & FD
    PP & ER & EM & GD & DF & PG & PV --> LLM
    FD -. verified packet only .-> PV
    REPO --> FIX
```

The stages depend only on `app/contracts` and `app/ports` — never on each
other or on FastAPI. The orchestrator is the only component that sequences
stages and mutates case state.

## 2. Workflow sequence

```mermaid
sequenceDiagram
    actor Clinician
    participant FE as Frontend
    participant API as FastAPI
    participant WO as Orchestrator
    participant ST as LLM stages
    participant DB as Case repo

    Clinician->>FE: Open demo case
    FE->>API: POST /api/cases/{id}/run
    API->>WO: start_analysis(id)
    WO->>ST: parse policy → 7 criteria
    par one search per criterion
        WO->>ST: retrieve evidence (LM-1..LM-7)
    end
    WO->>ST: map evidence (verbatim excerpts)
    WO->>ST: assess criteria + detect gaps
    WO->>WO: compute readiness (deterministic)
    WO->>DB: save case (awaiting_clarification)
    API-->>FE: AuthLensCase (matrix, question, score)

    Clinician->>FE: Answers "8 weeks PT completed, no improvement"
    FE->>API: POST /api/cases/{id}/clarifications
    API->>WO: submit_clarification(...)
    WO->>ST: re-assess LM-3 with recorded answer
    WO->>DB: save (readiness 79 → 93)
    API-->>FE: AuthLensCase

    Clinician->>FE: Proceed to packet
    FE->>API: POST generate-packet
    WO->>ST: disclosure review → include/exclude
    WO->>ST: generate packet (cited claims)
    FE->>API: POST verify
    WO->>ST: verify every claim (evaluator)
    alt blocking issue found
        WO->>DB: verification_failed → regenerate
    else all claims pass
        WO->>DB: verified
    end
    FE->>API: POST form-draft
    WO->>ST: populate mock form from verified packet
    WO->>DB: ready_for_review (terminal)
    API-->>FE: AuthLensCase — "Ready for Clinician Review"
    Note over Clinician,DB: AuthLens stops here. Nothing is submitted.
```

## 3. Case state machine

Authoritative table: `backend/app/contracts/case.py::ALLOWED_TRANSITIONS`.
There is **no `submitted` state**; `ready_for_review` is terminal.

```mermaid
stateDiagram-v2
    [*] --> draft
    draft --> intake_ready: inputs loaded
    intake_ready --> analyzing: POST run
    analyzing --> awaiting_clarification: analysis complete
    awaiting_clarification --> reanalyzing: POST clarifications
    reanalyzing --> awaiting_clarification: re-evaluation complete
    awaiting_clarification --> packet_drafted: POST generate-packet
    packet_drafted --> verified: POST verify (passed)
    packet_drafted --> verification_failed: POST verify (blocking issue)
    verification_failed --> packet_drafted: POST generate-packet (regenerate)
    verified --> ready_for_review: POST form-draft
    ready_for_review --> [*]: terminal — human review only
```

## 4. Parallel evidence retrieval

Retrieval fans out one bounded task per criterion; each searches all sources
independently. A criterion whose first pass is uncertain may loop — bounded
at 3 iterations — with reformulated queries before honestly returning what it
found (possibly nothing).

```mermaid
flowchart TB
    C[7 parsed criteria] --> F{fan out<br/>one task per criterion}
    F --> S1[LM-1 search]
    F --> S3[LM-3 search]
    F --> S7[LM-7 search]
    subgraph one_task["each task (bounded loop, max 3 iterations)"]
        Q[formulate query for<br/>criterion category] --> SRC[search note, transcript,<br/>FHIR chart, clarifications]
        SRC --> CHK{confident<br/>hit or miss?}
        CHK -- uncertain, budget left --> Q
        CHK -- yes / budget exhausted --> OUT[EvidenceCandidates<br/>verbatim excerpts + spans]
    end
    S1 & S3 & S7 --> J[join: all criteria done]
    J --> M[Evidence Mapper<br/>accept / reject candidates]
```

## 5. Verification and human-review gates

Two gates stand between analysis and the finished artifact: the machine
verification gate (evaluator–optimizer) and the human review boundary.

```mermaid
flowchart TB
    PKT[Packet draft<br/>every statement = claim + evidence_ids] --> V{Verifier<br/>independent checks}
    V -->|checks| K1[Every clinical claim cites evidence<br/>that exists and quotes source verbatim]
    V -->|checks| K2[No overstated claims:<br/>referral ≠ completed therapy<br/>prescription ≠ treatment failure]
    V -->|checks| K3[Policy claims match parsed criteria]
    V -->|checks| K4[No excluded PHI leaked into packet]
    K1 & K2 & K3 & K4 --> D{any blocking issue?}
    D -- yes --> FAIL[verification_failed<br/>issues listed with suggested fixes]
    FAIL --> REGEN[regenerate packet<br/>optimizer consumes issues]
    REGEN --> PKT
    D -- no --> OK[verified]
    OK --> FORM[Form Drafter<br/>accepts VERIFIED packet only]
    FORM --> HR[/READY FOR CLINICIAN REVIEW/]
    HR -.-> HUMAN[Human clinician acts outside AuthLens.<br/>No submission path exists in the system.]

    CLAR[Clarification checkpoint:<br/>clinician answers gap questions] -.->|human checkpoint #1| PKT
    HR -->|human checkpoint #2| HUMAN
```

## Technology choices

| Concern | Choice | Rationale |
|---|---|---|
| Language / framework | Python 3.11+, FastAPI | Spec default; fast to build, typed |
| Contracts | Pydantic v2, `extra="forbid"` | Drift caught at validation time |
| LLM | Anthropic Python SDK, `claude-opus-4-8` default | Single provider port; model configurable via `AUTHLENS_ANTHROPIC_MODEL` |
| Persistence | In-memory repository | Demo scope; port allows swapping later |
| Orchestration | Plain Python in `app/orchestration` | Deterministic, testable, no LLM in control flow |
| API docs | `contracts/openapi.yaml` (hand-maintained mirror) | Frontend can codegen without running the backend |
