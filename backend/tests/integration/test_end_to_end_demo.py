"""End-to-end and safety regression tests for the integrated backend.

These drive the **real** composition — Agent C's policy parser and retriever,
Agent D's evidence mapper / gap detector / readiness, Agent E's disclosure /
packet / verifier / form drafter, and Agent F's orchestrator — through the
FastAPI test client in deterministic mode (no network, no API key).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.contracts import (
    AuthLensCase,
    ClaimType,
    PacketClaim,
    PacketStatus,
    VerificationSeverity,
)
from app.main import create_app
from app.services.form_draft import MockPayerFormDrafter, UnverifiedPacketError
from app.services.verification.verifier import IndependentPacketVerifier

DEMO_FIXTURE_ID = "lumbar_mri_prior_auth"
CLARIFICATION = (
    "Patient completed six weeks of physical therapy and daily NSAID therapy "
    "without meaningful improvement."
)


@pytest.fixture
def client(monkeypatch) -> TestClient:
    # Deterministic mode: reproducible, no network, no key. Built before
    # create_app so the composition resolves the mock-free deterministic path.
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.delenv("AUTHLENS_LLM_MODE", raising=False)
    with TestClient(create_app(seed_demo_on_startup=False)) as test_client:
        yield test_client


def _conservative_criterion_id(case: dict) -> str:
    crit = next(c for c in case["criteria"] if c["category"] == "conservative_therapy")
    return crit["criterion_id"]


def _status_of(case: dict, criterion_id: str) -> str:
    return next(a["status"] for a in case["assessments"] if a["criterion_id"] == criterion_id)


def test_full_demo_flow_through_api(client: TestClient) -> None:
    """The complete point-of-capture readiness flow, acceptance criteria 1–20."""
    # 1. The demo case is the lumbar MRI case.
    demo = client.get("/api/demo-case")
    assert demo.status_code == 200
    demo_body = demo.json()
    assert demo_body["status"] == "intake_ready"
    assert demo_body["policy"]["policy_id"] == "MHP-IMG-2201"
    assert demo_body["requested_service"]["code"] == "72148"

    # 2. Create the case.
    created = client.post("/api/cases", json={"fixture_id": DEMO_FIXTURE_ID})
    assert created.status_code == 201
    case_id = created.json()["case_id"]

    # 3–9. Run analysis: policy parsed into cited criteria; retrieval runs;
    # PT referral + NSAID found; conservative therapy stays weak/missing; the
    # case pauses in awaiting_clarification with exactly one focused question.
    run = client.post(f"/api/cases/{case_id}/run")
    assert run.status_code == 200
    case = run.json()
    assert case["status"] == "awaiting_clarification"

    assert len(case["criteria"]) == 7  # 4. seven parsed criteria
    for crit in case["criteria"]:
        assert crit["requirement"].strip()  # each cites policy requirement text
        assert crit["policy_id"] == "MHP-IMG-2201"

    ct_id = _conservative_criterion_id(case)  # LM-3
    ct_assessment = next(a for a in case["assessments"] if a["criterion_id"] == ct_id)
    # 6. PT referral and NSAID evidence are found (as low-confidence, capped).
    ct_excerpts = " ".join(e["excerpt"].lower() for e in ct_assessment["evidence"])
    assert "physical therapy" in ct_excerpts
    assert "naproxen" in ct_excerpts or "nsaid" in ct_excerpts
    # 7. Failed conservative therapy remains weak or missing (never met yet).
    assert ct_assessment["status"] in {"missing", "weak"}

    # 9. Exactly one focused, open clarification question (for LM-3).
    open_qs = [q for q in case["clarification_questions"] if q["status"] == "open"]
    assert len(open_qs) == 1
    question = open_qs[0]
    assert ct_id in question["criterion_ids"]

    # Readiness before clarification is recorded.
    assert [r["label"] for r in case["readiness_history"]] == ["initial"]
    score_before = case["readiness_history"][0]["score"]

    # 10–11. Submit the clarification; it is recorded with author, timestamp,
    # and provenance (a citable clinician_clarification source).
    answer = client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": question["question_id"], "response": CLARIFICATION},
    )
    assert answer.status_code == 200
    case = answer.json()
    assert len(case["clarifications"]) == 1
    clar = case["clarifications"][0]
    assert clar["response"] == CLARIFICATION  # verbatim
    assert clar["recorded_at"]  # timestamp provenance
    # The clarification resolves as a citable source in the evidence drawer.
    drawer = client.get(f"/api/cases/{case_id}/evidence/{clar['clarification_id']}")
    assert drawer.status_code == 200
    assert drawer.json()["content"] == CLARIFICATION

    # 12–14. The relevant criterion updates to met; readiness increases; the
    # before-and-after snapshots both remain available.
    assert _status_of(case, ct_id) == "met"
    labels = [r["label"] for r in case["readiness_history"]]
    assert labels[0] == "initial" and len(labels) >= 2
    score_after = case["readiness_history"][-1]["score"]
    assert score_after > score_before

    # 15–16. Generate the packet: unrelated PHI excluded, valid citations only.
    packet_resp = client.post(f"/api/cases/{case_id}/generate-packet")
    assert packet_resp.status_code == 200
    case = packet_resp.json()
    assert case["status"] == "packet_drafted"
    decisions = case["disclosure_decisions"]
    assert any(d["decision"] == "exclude" for d in decisions)
    # The unrelated allergic-rhinitis condition is not included.
    included_sources = {d["source_id"] for d in decisions if d["decision"] == "include"}
    assert "fhir-cond-002" not in included_sources
    assert case["packet"]["claims"], "packet has claims"
    for claim in case["packet"]["claims"]:
        if claim["claim_type"] == "clinical":
            assert claim["evidence_ids"], "clinical claims cite evidence"

    # 17. Verification passes.
    verify = client.post(f"/api/cases/{case_id}/verify")
    assert verify.status_code == 200
    case = verify.json()
    assert case["status"] == "verified"
    assert case["verification"]["passed"] is True
    assert case["verification"]["issues"] == []

    # 18–19. Form draft is produced; the case reaches ready_for_review.
    form = client.post(f"/api/cases/{case_id}/form-draft")
    assert form.status_code == 200
    case = form.json()
    assert case["status"] == "ready_for_review"
    assert case["form_draft"]["fields"]

    # 20. No endpoint or state submits the authorization.
    schema = client.get("/openapi.json").json()
    assert not any("submit" in path.lower() for path in schema["paths"])
    case_statuses = set(schema["components"]["schemas"]["CaseStatus"]["enum"])
    assert "submitted" not in case_statuses
    # ready_for_review is terminal — no further workflow POST leaves it.
    assert client.post(f"/api/cases/{case_id}/generate-packet").status_code == 409


def test_pt_referral_alone_cannot_satisfy_conservative_therapy(client: TestClient) -> None:
    """Safety regression: a PT referral (and an NSAID prescription) present in
    the record must NEVER satisfy completed-and-failed conservative therapy on
    their own. Referral != completion; prescription != failure.
    """
    case_id = client.post("/api/cases", json={"fixture_id": DEMO_FIXTURE_ID}).json()[
        "case_id"
    ]
    case = client.post(f"/api/cases/{case_id}/run").json()

    ct_id = _conservative_criterion_id(case)
    assessment = next(a for a in case["assessments"] if a["criterion_id"] == ct_id)

    # The referral and the prescription are both in evidence...
    excerpts = " ".join(e["excerpt"].lower() for e in assessment["evidence"])
    assert "physical therapy" in excerpts
    assert "naproxen" in excerpts or "nsaid" in excerpts
    # ...each capped at low confidence with an explicit limitation note...
    for item in assessment["evidence"]:
        if "referral" in item["excerpt"].lower() or "naproxen" in item["excerpt"].lower():
            assert item["confidence"] == "low"
            assert item["note"], "referral/prescription evidence must carry a limitation note"
    # ...and the criterion is therefore NOT met.
    assert assessment["status"] in {"missing", "weak"}
    assert assessment["status"] != "met"


def test_unsupported_packet_claim_cannot_reach_form_draft(client: TestClient) -> None:
    """Verification regression: an unsupported clinical claim in a packet must
    fail the independent verifier and be refused by the form drafter, so it can
    never reach a form draft.
    """
    # Drive the real pipeline to a genuinely verified packet.
    case_id = client.post("/api/cases", json={"fixture_id": DEMO_FIXTURE_ID}).json()[
        "case_id"
    ]
    run = client.post(f"/api/cases/{case_id}/run").json()
    q = next(q for q in run["clarification_questions"] if q["status"] == "open")
    client.post(
        f"/api/cases/{case_id}/clarifications",
        json={"question_id": q["question_id"], "response": CLARIFICATION},
    )
    client.post(f"/api/cases/{case_id}/generate-packet")
    verified = client.post(f"/api/cases/{case_id}/verify").json()
    assert verified["status"] == "verified"

    case = AuthLensCase.model_validate(verified)
    packet = case.packet
    assert packet is not None

    # Inject an unsupported clinical claim: it cites evidence that does not
    # exist on the case (a fabricated citation), and overstates therapy outcome.
    packet.claims.append(
        PacketClaim(
            claim_id="claim-unsupported-001",
            text="The patient completed and failed twelve weeks of chiropractic therapy.",
            claim_type=ClaimType.CLINICAL,
            criterion_id=_conservative_criterion_id(verified),
            evidence_ids=["ev-does-not-exist-001"],
        )
    )
    packet.status = PacketStatus.DRAFT  # a modified packet is unverified

    # The independent verifier catches it with a BLOCKING issue.
    result = IndependentPacketVerifier().verify(packet, case)
    assert result.passed is False
    assert any(i.severity is VerificationSeverity.BLOCKING for i in result.issues)

    # The form drafter refuses an unverified / failed packet — the unsupported
    # claim cannot reach a form draft.
    with pytest.raises(UnverifiedPacketError):
        MockPayerFormDrafter().draft(packet, result, case)
