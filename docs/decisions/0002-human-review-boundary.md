# ADR 0002 — Human review boundary; no submission

**Status:** Accepted · **Date:** 2026-07-18

## Context

The consequential action in prior authorization is submitting to a payer.
An AI system that submits — or that looks like it might — changes the risk
profile of every upstream error and invites automation complacency.

## Decision

AuthLens terminates at **Ready for Clinician Review**:

- The state machine has no `submitted` state; `ready_for_review` is terminal
  (`ALLOWED_TRANSITIONS` in `backend/app/contracts/case.py`).
- The API has no submission endpoint; the payer form is explicitly a MOCK.
- Two human checkpoints precede the terminal state: the clarification
  checkpoint (clinician answers gap questions, recorded verbatim) and the
  final review itself.
- The `FormDrafter` port accepts only a verified packet — no path from
  unverified text to the reviewer-facing artifact.
- Frozen contract tests assert the absence of submission
  (`test_state_machine.py`, `test_openapi.py`); weakening them is a
  safety-rule violation per SAFETY_AND_HUMAN_REVIEW.md.

## Consequences

- The demo's last beat is a banner, not a "sent" confirmation — by design.
- Real-world submission remains a human act in the payer's own channel.
- Future work (e.g., export formats) must still terminate at human review.
