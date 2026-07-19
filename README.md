# AuthLens

**Prior authorization readiness, at the point of capture.**

AuthLens checks encounter documentation against a payer's medical-necessity
policy *while the patient is still in the room* — downstream of an
Abridge-style ambient note.

It parses the policy into discrete criteria, maps each one to a **verbatim
cited excerpt** from the note, transcript, or FHIR chart, classifies what's
missing, asks the clinician one precise question, and produces a verified,
source-grounded PA packet and mock form — stopping at **Ready for Clinician
Review**.

It never diagnoses, never recommends treatment, never predicts payer
approval, and **never submits anything**.

> All patient, clinician, and payer data here is **hackathon-authored
> synthetic data**. The payer "Meridian Health Plans" is fictional.
> See `data/` and ADR 0004.

---

## The problem

Prior auth happens days after the visit, in a back office, from a note the
clinician has already moved on from. A missing line of documentation costs a
week — and the one person who could have fixed it in five seconds was the
physician who saw the patient.

AuthLens moves that check to the moment the documentation is created.

---

## Run it in two minutes

Two processes. **`DEMO_MODE=1` is required** — see the note below it.

```bash
# Terminal 1 — backend (http://localhost:8000)
cd backend
uv sync
DEMO_MODE=1 uv run uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (http://localhost:5173)
cd authlens
npm install
npm run dev
```

Open **http://localhost:5173**, pick the *Lumbar MRI — Conservative Therapy
Gap* scenario, and click **Run Analysis**.

> ⚠️ **Always set `DEMO_MODE=1`.** Provider mode is resolved by the *presence*
> of `ANTHROPIC_API_KEY`, not its validity — so a stale or unfunded key in
> your environment silently selects live mode and the pipeline fails at the
> first LLM stage. Deterministic mode needs no key and is fully reproducible.
> Live mode is an explicit opt-in (`AUTHLENS_LLM_MODE=live` + a funded key)
> and never silently falls back to the mock.

---

## What you'll see

The demo case: **lumbar-spine MRI (CPT 72148)** for chronic low back pain with
radicular symptoms, against policy **MHP-IMG-2201**.

1. **The agent timeline streams live.** Each agent reports its own
   proof-of-work — criteria parsed, excerpts cited, criteria assessed.
2. **The evidence matrix** shows all 7 criteria. Every clinical claim carries a
   verbatim quote with a character span. Click any citation to jump to the
   exact highlighted text in the note.
3. **Six of seven criteria are met — one is not.** The chart shows an NSAID
   and a *PT referral*, but the policy requires *completed and failed*
   conservative therapy. A referral is not proof of completed therapy, so
   AuthLens will not infer it.
4. **It asks one question.** The clinician answers, and readiness rises from
   **79 → 93**.
5. **Packet drafted, independently verified, form populated — then it stops.**
   `ready_for_review` is terminal.

---

## The agents

An 11-stage pipeline orchestrated over frozen ports. Seven stages are
LLM-backed agents (`app/agents/`); `form_drafting` is a deterministic service:

| Stage | Agent | Does |
|---|---|---|
| `policy_parsing` | Policy Agent | Splits the payer policy into discrete, checkable criteria |
| `evidence_retrieval` | Evidence Retrieval Agent | Pulls candidate spans from note, transcript, FHIR chart |
| `evidence_mapping` | Evidence Mapper Agent | Binds each criterion to verbatim excerpts + spans |
| `gap_detection` | Gap & Readiness Agent | Classifies met / weak / missing; scores readiness |
| `disclosure_review` | Disclosure Agent | Minimum-necessary review — unrelated PHI excluded by default |
| `packet_generation` | Packet Agent | Assembles the source-grounded PA packet |
| `verification` | Verification Agent | Independently re-checks every claim against its citation |
| `form_drafting` | Form Agent | Populates the mock payer form |

`intake`, `clarification`, and `human_review` are the three non-agent stages.

---

## Safety posture

These are enforced in code and covered by tests, not just documented:

- **No autonomous submission.** There is no submission endpoint and no
  `submitted` state. `ready_for_review` is terminal.
- **No diagnosis, no treatment recommendation, no approval prediction.**
- **Source-grounded or absent.** Every clinical claim cites evidence; every
  excerpt is a verbatim quote with a span. When evidence is missing, the
  output is `missing` + a clarification question — never an inference.
- **A referral is never proof of completed therapy**; a prescription is never
  proof of treatment failure (at most `weak` support).
- **No chain-of-thought is ever logged** — not in events, logs, artifacts, or
  test snapshots.
- **Minimum necessary.** Unrelated PHI is excluded by default; packet content
  requires an explicit INCLUDE disclosure decision.

---

## How it was built

Seven Claude Code agents built the subsystems **in parallel** against frozen
contracts and ports, then an integration agent wired them together.

The contracts (`backend/app/contracts/`, `backend/app/ports/`, `contracts/`)
were frozen *before* parallel work began and never edited during it — each
agent coded against interfaces and local fakes, so the subsystems composed on
first integration. See [`docs/PARALLEL_EXECUTION.md`](docs/PARALLEL_EXECUTION.md)
and [`docs/INTEGRATION_REPORT.md`](docs/INTEGRATION_REPORT.md).

```bash
cd backend
uv run pytest                  # 351 passed, 1 skipped (opt-in live LLM)
uv run pytest tests/contracts  # 57 frozen contract & safety-invariant tests
```

---

## Repository layout

```
authlens/              React + Vite frontend
backend/               FastAPI backend
  app/contracts/       Frozen Pydantic v2 contracts (authoritative schemas)
  app/ports/           Frozen component interfaces (Protocols)
  app/agents/          Seven LLM-backed pipeline agents
  app/services/        Deterministic services (readiness, form draft, ...)
  app/orchestration/   Workflow orchestrator + state machine
  app/providers/       LLM provider (deterministic mock / live Anthropic)
  tests/contracts/     Frozen contract & safety-invariant tests
contracts/             OpenAPI spec + validated example payloads
data/fixtures/         Synthetic demo case (frozen)
data/policies/         Synthetic payer policy (frozen)
docs/                  Full documentation (start at docs/README.md)
synthetic-ambient-fhir-25/   Official Abridge dataset (READ-ONLY)
CLAUDE.md              Rules for Claude Code agents
```

---

## Driving it headlessly

The full demo without the UI:

```bash
BASE=http://localhost:8000/api
CID=$(curl -s -X POST $BASE/cases -H 'content-type: application/json' \
      -d '{"fixture_id":"lumbar_mri_prior_auth"}' | python -c 'import sys,json;print(json.load(sys.stdin)["case_id"])')
curl -s -X POST $BASE/cases/$CID/run > /dev/null                      # → awaiting_clarification (readiness 79)
QID=$(curl -s $BASE/cases/$CID | python -c 'import sys,json;print([q["question_id"] for q in json.load(sys.stdin)["clarification_questions"] if q["status"]=="open"][0])')
curl -s -X POST $BASE/cases/$CID/clarifications -H 'content-type: application/json' \
     -d "{\"question_id\":\"$QID\",\"response\":\"Patient completed six weeks of physical therapy and daily NSAID therapy without meaningful improvement.\"}" > /dev/null
curl -s -X POST $BASE/cases/$CID/generate-packet > /dev/null          # → packet_drafted
curl -s -X POST $BASE/cases/$CID/verify > /dev/null                   # → verified (readiness 93)
curl -s -X POST $BASE/cases/$CID/form-draft | python -m json.tool     # → ready_for_review
```

`POST /cases/{id}/run/stream` is the same pipeline as `/run`, streaming
per-agent progress as NDJSON — this is what the UI timeline consumes.

---

## Documentation

Start at [`docs/README.md`](docs/README.md).

[Product spec](docs/PRODUCT_SPEC.md) ·
[Architecture](docs/SYSTEM_ARCHITECTURE.md) ·
[API contract](docs/API_CONTRACT.md) ·
[Safety & human review](docs/SAFETY_AND_HUMAN_REVIEW.md) ·
[Agent workflows](docs/AGENT_WORKFLOWS.md) ·
[Parallel execution plan](docs/PARALLEL_EXECUTION.md) ·
[Integration report](docs/INTEGRATION_REPORT.md) ·
[Evaluation plan](docs/EVALUATION_PLAN.md) ·
[Abridge dataset usage](docs/ABRIDGE_DATASET.md)
</content>
</invoke>
