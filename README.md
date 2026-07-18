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

```bash
cd backend
uv sync
uv run pytest tests/contracts   # 57 contract, safety & dataset tests
```

The API server (`app/main.py`) arrives in the parallel build phase — see
`docs/IMPLEMENTATION_PLAN.md`. The frontend can start now against
`contracts/openapi.yaml` and `contracts/examples/`.

## Documentation

Start at [`docs/README.md`](docs/README.md). Key entry points:
[Product spec](docs/PRODUCT_SPEC.md) ·
[Architecture](docs/SYSTEM_ARCHITECTURE.md) ·
[API contract](docs/API_CONTRACT.md) ·
[Frontend handoff](docs/FRONTEND_HANDOFF.md) ·
[Safety & human review](docs/SAFETY_AND_HUMAN_REVIEW.md) ·
[Parallel execution plan](docs/PARALLEL_EXECUTION.md)
