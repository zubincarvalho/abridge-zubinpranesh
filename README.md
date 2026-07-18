# AuthLens

**Point-of-capture prior authorization readiness agent** — a backend-first
healthcare AI hackathon project built downstream of an Abridge-style
encounter note.

AuthLens checks the encounter documentation against a payer's
medical-necessity policy *while the patient is still in the room*: it parses
the policy into discrete criteria, maps each criterion to exact cited
evidence in the note/transcript/FHIR chart, classifies gaps, asks the
clinician precise clarification questions, and produces a verified,
source-grounded prior authorization packet and mock form — stopping at
**Ready for Clinician Review**. It never diagnoses, never recommends
treatment, never predicts approval, and never submits anything.

> All patient, clinician, and payer data in this repository is
> **hackathon-authored synthetic data** (see `data/` and ADR 0004).

## Demo scenario

Lumbar-spine MRI (CPT 72148) for chronic low back pain with radicular
symptoms. The chart shows an NSAID and a PT referral — but the payer policy
requires *completed and failed* conservative therapy. AuthLens flags the gap,
asks one question, and readiness rises from 79 to 93 after the clinician's
answer. Full walkthrough: `docs/PRODUCT_SPEC.md`.

## Repository layout

```
CLAUDE.md              Rules for Claude Code agents (read before contributing)
docs/                  Documentation (start at docs/README.md)
contracts/             OpenAPI spec + validated example payloads (frontend contract)
backend/               FastAPI backend
  app/contracts/       Frozen Pydantic v2 contracts (authoritative schemas)
  app/ports/           Frozen component interfaces (Protocols)
  app/config.py        Settings (Anthropic model, fixture paths)
  tests/contracts/     Frozen contract & safety-invariant tests
data/fixtures/         Synthetic demo case (frozen, hackathon-authored)
data/policies/         Synthetic payer policy (frozen, hackathon-authored)
synthetic-ambient-fhir-25/  Official Abridge synthetic dataset (READ-ONLY — never modify)
```

## Quick start

The backend is fully integrated. All commands run from `backend/`.

```bash
cd backend
uv sync                                    # install dependencies

uv run pytest                              # full suite: 351 passed, 1 skipped
uv run pytest tests/contracts              # 57 frozen contract & safety tests

# Run the API in deterministic demo mode (reproducible; no API key needed):
DEMO_MODE=1 uv run uvicorn app.main:app --reload --port 8000
```

Then drive the full demo (from another shell):

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

**Provider mode.** Deterministic mode (`DEMO_MODE=1`) is fully reproducible and
requires no key. Live LLM mode is an explicit opt-in
(`AUTHLENS_LLM_MODE=live` + `ANTHROPIC_API_KEY`); it never silently falls back
to the mock — see [`docs/INTEGRATION_REPORT.md`](docs/INTEGRATION_REPORT.md).
Realistic response payloads for the frontend live in
[`docs/frontend_examples/`](docs/frontend_examples/).

## Documentation

Start at [`docs/README.md`](docs/README.md). Key entry points:
[Product spec](docs/PRODUCT_SPEC.md) ·
[Architecture](docs/SYSTEM_ARCHITECTURE.md) ·
[API contract](docs/API_CONTRACT.md) ·
[Frontend handoff](docs/FRONTEND_HANDOFF.md) ·
[Safety & human review](docs/SAFETY_AND_HUMAN_REVIEW.md) ·
[Parallel execution plan](docs/PARALLEL_EXECUTION.md)
