# ADR 0001 — Controlled workflow, not an agent swarm

**Status:** Accepted · **Date:** 2026-07-18

## Context

AuthLens automates a safety-sensitive clinical-administrative task. Anthropic's
"Building Effective Agents" guidance is to use the simplest structure that
works: deterministic workflows where control flow is known, agents only where
open-ended exploration is required. Prior authorization readiness has a fixed,
auditable pipeline — the steps are known in advance.

## Decision

The overall workflow is **deterministic Python orchestration** over narrow,
typed LLM stages (prompt chaining + routing + parallelization +
evaluator–optimizer). Exactly one bounded agent loop exists: per-criterion
evidence retrieval may iterate up to 3 times when its first pass is
uncertain. No LLM ever chooses the control flow, spawns agents, selects
tools, or mutates case state. All model access goes through a single
`LLMProvider` port.

## Consequences

- Every stage is independently testable against fakes; failures are localized.
- The timeline shown to clinicians reflects real, fixed stages — auditable.
- We give up open-ended flexibility (fine: the demo is one fixed workflow).
- Adding a new service/policy means adding data + routing entries, not agents.
