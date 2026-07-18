# ADR 0003 — Contract-first parallel development

**Status:** Accepted · **Date:** 2026-07-18

## Context

Seven Claude Code agents plus a frontend build concurrently under hackathon
time pressure. Parallel work fails on shared mutable surfaces: schemas,
manifests, and cross-cutting files.

## Decision

Freeze the shared surfaces **before** parallel work starts:

- `backend/app/contracts/` (Pydantic v2, `extra="forbid"`) and
  `backend/app/ports/` (Protocols) are written first and frozen.
- `contracts/openapi.yaml` + `contracts/examples/*.json` mirror the contracts
  so the frontend builds without a running backend; examples are generated
  from the models and revalidated by frozen tests.
- Strict, non-overlapping file ownership per agent (PARALLEL_EXECUTION.md);
  cross-agent needs flow only through ports, so everyone codes against fakes.
- `pyproject.toml` is frozen; dependencies go through per-agent request files
  (DEPENDENCY_POLICY.md).
- Contract changes are requested in agent reports and applied only by the
  integration agent, who re-runs contract tests and regenerates examples.

## Consequences

- Merge conflicts are structurally impossible outside integration.
- Contract mistakes found mid-build cost a request/apply round-trip — the
  price of stability; mitigated by generating examples early and testing the
  full demo shape now.
- The integration agent is a deliberate serialization point at the end.
