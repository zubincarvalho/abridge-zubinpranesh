"""Local, deterministic fakes for every port the orchestrator depends on.

These stand in for Agents A/C/D/E so orchestration tests never import
another agent's implementation. The fakes honor the port docstrings
(verbatim excerpts, draft-only packets, form drafter raising on unverified
input) so the orchestrator's gates are exercised realistically.
"""

import time
from datetime import datetime, timezone

from app.contracts import (
    AuthLensCase,
    ClaimType,
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    DisclosureDecision,
    DisclosureDecisionType,
    EvidenceCandidate,
    EvidenceConfidence,
    EvidenceItem,
    FormDraftField,
    PacketClaim,
    PacketSection,
    PacketStatus,
    PayerPolicy,
    PolicyCriterion,
    PriorAuthorizationFormDraft,
    PriorAuthorizationPacket,
    ReadinessSummary,
    SourceType,
    TextSpan,
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)

NOTE_TEXT = (
    "Chronic low back pain radiating to the left leg. "
    "Symptoms present for 8 weeks despite home exercise. "
    "MRI lumbar spine without contrast is requested."
)
TRANSCRIPT_TEXT = "Clinician: The back pain has been going on about two months now."
POLICY_TEXT = (
    "Lumbar MRI is medically necessary when pain persists at least 6 weeks "
    "and a course of conservative therapy has been completed and failed."
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FakeCaseRepository:
    """Minimal dict-backed CaseRepository (deep-copy isolation, KeyError raises)."""

    def __init__(self) -> None:
        self._cases: dict[str, AuthLensCase] = {}

    def create(self, case: AuthLensCase) -> AuthLensCase:
        if case.case_id in self._cases:
            raise KeyError(case.case_id)
        self._cases[case.case_id] = case.model_copy(deep=True)
        return case.model_copy(deep=True)

    def get(self, case_id: str) -> AuthLensCase:
        return self._cases[case_id].model_copy(deep=True)

    def save(self, case: AuthLensCase) -> AuthLensCase:
        if case.case_id not in self._cases:
            raise KeyError(case.case_id)
        self._cases[case.case_id] = case.model_copy(deep=True)
        return case.model_copy(deep=True)

    def list_case_ids(self) -> list[str]:
        return list(self._cases)

    def reset(self) -> None:
        self._cases.clear()


class FakePolicyParser:
    """Three fixed criteria; LM-3 (conservative therapy) is the engineered gap."""

    def parse(self, policy: PayerPolicy, policy_text: str) -> list[PolicyCriterion]:
        assert policy_text  # the orchestrator must pass the loaded text
        return [
            PolicyCriterion(
                criterion_id="LM-1",
                policy_id=policy.policy_id,
                label="Documented indication",
                requirement="Low back pain with radicular features is documented.",
                category="indication",
            ),
            PolicyCriterion(
                criterion_id="LM-2",
                policy_id=policy.policy_id,
                label="Symptom duration at least 6 weeks",
                requirement="Symptoms have persisted for at least 6 weeks.",
                category="duration",
            ),
            PolicyCriterion(
                criterion_id="LM-3",
                policy_id=policy.policy_id,
                label="Conservative therapy completed and failed",
                requirement="A course of conservative therapy was completed and failed.",
                category="conservative_therapy",
            ),
        ]


def _note_candidate(case: AuthLensCase, criterion_id: str, excerpt: str) -> EvidenceCandidate:
    start = case.encounter_note.text.index(excerpt)
    return EvidenceCandidate(
        candidate_id=f"cand-{criterion_id}",
        criterion_id=criterion_id,
        source_id=case.encounter_note.source_id,
        source_type=SourceType.ENCOUNTER_NOTE,
        excerpt=excerpt,
        span=TextSpan(start=start, end=start + len(excerpt)),
        confidence=EvidenceConfidence.HIGH,
        relevance_rationale="Directly states the criterion requirement.",
    )


class FakeEvidenceRetriever:
    """LM-1/LM-2 hit the note; LM-3 finds nothing until a clarification exists."""

    def __init__(self, fail_first_n_for: dict[str, int] | None = None) -> None:
        self.fail_first_n_for = dict(fail_first_n_for or {})
        self.calls: dict[str, int] = {}

    def retrieve(
        self, case: AuthLensCase, criterion: PolicyCriterion
    ) -> list[EvidenceCandidate]:
        cid = criterion.criterion_id
        self.calls[cid] = self.calls.get(cid, 0) + 1
        if self.fail_first_n_for.get(cid, 0) >= self.calls[cid]:
            raise RuntimeError(f"transient retrieval failure for {cid}")
        if cid == "LM-1":
            return [
                _note_candidate(
                    case, cid, "Chronic low back pain radiating to the left leg."
                )
            ]
        if cid == "LM-2":
            return [
                _note_candidate(
                    case, cid, "Symptoms present for 8 weeks despite home exercise."
                )
            ]
        if cid == "LM-3" and case.clarifications:
            clarification = case.clarifications[-1]
            return [
                EvidenceCandidate(
                    candidate_id=f"cand-{cid}-clar",
                    criterion_id=cid,
                    source_id=clarification.clarification_id,
                    source_type=SourceType.CLINICIAN_CLARIFICATION,
                    excerpt=clarification.response,
                    span=TextSpan(start=0, end=len(clarification.response)),
                    confidence=EvidenceConfidence.HIGH,
                    relevance_rationale="Clinician answered the therapy question.",
                )
            ]
        return []  # honest miss


class FakeEvidenceMapper:
    def map_evidence(
        self, criterion: PolicyCriterion, candidates: list[EvidenceCandidate]
    ) -> list[EvidenceItem]:
        return [
            EvidenceItem(
                evidence_id=f"ev-{candidate.candidate_id}",
                source_id=candidate.source_id,
                source_type=candidate.source_type,
                excerpt=candidate.excerpt,
                span=candidate.span,
                confidence=candidate.confidence,
            )
            for candidate in candidates
        ]


class NonVerbatimMapper(FakeEvidenceMapper):
    """Violates the verbatim rule so the orchestrator gate must catch it."""

    def map_evidence(self, criterion, candidates):
        items = super().map_evidence(criterion, candidates)
        return [
            item.model_copy(update={"excerpt": "THIS TEXT IS NOT IN THE SOURCE", "span": None})
            for item in items
        ]


class FakeGapDetector:
    def assess(
        self,
        criterion: PolicyCriterion,
        evidence: list[EvidenceItem],
        clarifications: list[ClinicianClarification],
    ) -> CriterionAssessment:
        if not evidence:
            return CriterionAssessment(
                criterion_id=criterion.criterion_id,
                status=CriterionStatus.MISSING,
                denial_risk=DenialRisk.HIGH,
                rationale="No evidence found in the provided sources.",
                evidence=[],
                clarification_question_id=f"q-{criterion.criterion_id}",
            )
        if criterion.category == "conservative_therapy" and all(
            item.source_type not in (SourceType.CLINICIAN_CLARIFICATION,)
            and item.source_id.startswith("src-chart-referral")
            for item in evidence
        ):
            # Referral != completed therapy: at most WEAK.
            return CriterionAssessment(
                criterion_id=criterion.criterion_id,
                status=CriterionStatus.WEAK,
                denial_risk=DenialRisk.MEDIUM,
                rationale="Only a referral is documented; completion is not.",
                evidence=evidence,
                clarification_question_id=f"q-{criterion.criterion_id}",
            )
        return CriterionAssessment(
            criterion_id=criterion.criterion_id,
            status=CriterionStatus.MET,
            denial_risk=DenialRisk.LOW,
            rationale=f'Cited evidence states: "{evidence[0].excerpt}"',
            evidence=evidence,
        )

    def generate_clarifications(
        self,
        assessments: list[CriterionAssessment],
        criteria: list[PolicyCriterion],
    ) -> list[ClarificationQuestion]:
        labels = {c.criterion_id: c.label for c in criteria}
        return [
            ClarificationQuestion(
                question_id=f"q-{assessment.criterion_id}",
                criterion_ids=[assessment.criterion_id],
                question=f"What was documented for: {labels[assessment.criterion_id]}?",
                why_needed="This criterion has no supporting documentation yet.",
                status="open",
            )
            for assessment in assessments
            if assessment.status in (CriterionStatus.MISSING, CriterionStatus.WEAK)
        ]

    def compute_readiness(
        self, assessments: list[CriterionAssessment], label: str
    ) -> ReadinessSummary:
        counts = {status: 0 for status in CriterionStatus}
        for assessment in assessments:
            counts[assessment.status] += 1
        considered = (
            counts[CriterionStatus.MET]
            + counts[CriterionStatus.WEAK]
            + counts[CriterionStatus.MISSING]
            + counts[CriterionStatus.CONFLICTING]
        )
        score = (
            round(
                100
                * (counts[CriterionStatus.MET] + 0.5 * counts[CriterionStatus.WEAK])
                / considered
            )
            if considered
            else 100
        )
        if counts[CriterionStatus.MISSING] or counts[CriterionStatus.CONFLICTING]:
            risk = DenialRisk.HIGH
        elif counts[CriterionStatus.WEAK]:
            risk = DenialRisk.MEDIUM
        else:
            risk = DenialRisk.LOW
        return ReadinessSummary(
            label=label,
            score=int(score),
            criteria_met=counts[CriterionStatus.MET],
            criteria_weak=counts[CriterionStatus.WEAK],
            criteria_missing=counts[CriterionStatus.MISSING],
            criteria_conflicting=counts[CriterionStatus.CONFLICTING],
            criteria_not_applicable=counts[CriterionStatus.NOT_APPLICABLE],
            overall_denial_risk=risk,
            computed_at=_now(),
        )


class FakeDisclosureFilter:
    """Includes service-relevant sources; excludes the unrelated condition."""

    def review(self, case: AuthLensCase) -> list[DisclosureDecision]:
        decisions = [
            DisclosureDecision(
                decision_id="disc-note",
                source_id=case.encounter_note.source_id,
                item_description="Encounter note",
                decision=DisclosureDecisionType.INCLUDE,
                reason="Directly documents the indication for the requested MRI.",
            )
        ]
        for item in case.patient.chart_items:
            if item.category == "referral":
                decisions.append(
                    DisclosureDecision(
                        decision_id=f"disc-{item.source_id}",
                        source_id=item.source_id,
                        item_description=item.display,
                        decision=DisclosureDecisionType.INCLUDE,
                        reason="Conservative-therapy referral is policy-relevant.",
                    )
                )
            else:
                decisions.append(
                    DisclosureDecision(
                        decision_id=f"disc-{item.source_id}",
                        source_id=item.source_id,
                        item_description=item.display,
                        decision=DisclosureDecisionType.EXCLUDE,
                        reason="Unrelated to the requested imaging service.",
                        phi_category="unrelated_condition",
                    )
                )
        return decisions


class FakePacketGenerator:
    def __init__(self) -> None:
        self.generation_count = 0

    def generate(self, case: AuthLensCase) -> PriorAuthorizationPacket:
        self.generation_count += 1
        claims = [
            PacketClaim(
                claim_id=f"claim-{assessment.criterion_id}",
                text=assessment.rationale,
                claim_type=ClaimType.CLINICAL,
                criterion_id=assessment.criterion_id,
                evidence_ids=[item.evidence_id for item in assessment.evidence],
            )
            for assessment in case.assessments
            if assessment.evidence
        ]
        claims.append(
            PacketClaim(
                claim_id="claim-policy",
                text=f"Policy {case.policy.policy_id} criteria addressed above.",
                claim_type=ClaimType.POLICY,
            )
        )
        return PriorAuthorizationPacket(
            packet_id=f"packet-{case.case_id}-{self.generation_count}",
            case_id=case.case_id,
            status=PacketStatus.DRAFT,
            sections=[
                PacketSection(
                    section_id="sec-1",
                    title="Clinical Summary",
                    body="Source-grounded summary of the documented criteria.",
                    claim_ids=[claim.claim_id for claim in claims],
                )
            ],
            claims=claims,
            generated_at=_now(),
        )


class SelfVerifyingPacketGenerator(FakePacketGenerator):
    """Illegally marks its own packet verified; the gate must reject it."""

    def generate(self, case: AuthLensCase) -> PriorAuthorizationPacket:
        packet = super().generate(case)
        packet.status = PacketStatus.VERIFIED
        return packet


class GhostEvidencePacketGenerator(FakePacketGenerator):
    """Cites an evidence id that does not exist on the case."""

    def generate(self, case: AuthLensCase) -> PriorAuthorizationPacket:
        packet = super().generate(case)
        packet.claims[0].evidence_ids = ["ev-ghost"]
        return packet


class FakePacketVerifier:
    """Deterministic verifier. ``fail_times`` first calls report a blocking
    issue; ``hang_seconds`` simulates a stuck verifier for timeout tests."""

    def __init__(self, fail_times: int = 0, hang_seconds: float = 0.0) -> None:
        self.fail_times = fail_times
        self.hang_seconds = hang_seconds
        self.calls = 0

    def verify(
        self, packet: PriorAuthorizationPacket, case: AuthLensCase
    ) -> VerificationResult:
        self.calls += 1
        if self.hang_seconds:
            time.sleep(self.hang_seconds)
        failing = self.calls <= self.fail_times
        issues = (
            [
                VerificationIssue(
                    issue_id="issue-1",
                    severity=VerificationSeverity.BLOCKING,
                    claim_id=packet.claims[0].claim_id if packet.claims else None,
                    description="Claim overstates the cited evidence.",
                    suggested_resolution="Restate the claim to match the excerpt.",
                )
            ]
            if failing
            else []
        )
        return VerificationResult(
            verification_id=f"verif-{packet.packet_id}-{self.calls}",
            packet_id=packet.packet_id,
            passed=not failing,
            checked_claim_count=len(packet.claims),
            issues=issues,
            verified_at=_now(),
        )


class FakeFormDrafter:
    """Honors the port's MUST rules: verified packet + passing verification only."""

    def draft(
        self,
        packet: PriorAuthorizationPacket,
        verification: VerificationResult,
        case: AuthLensCase,
    ) -> PriorAuthorizationFormDraft:
        if packet.status is not PacketStatus.VERIFIED:
            raise ValueError("form drafter requires a VERIFIED packet")
        if verification.packet_id != packet.packet_id:
            raise ValueError("verification does not match the packet")
        if not verification.passed:
            raise ValueError("form drafter requires a passing verification")
        first_claim = packet.claims[0]
        return PriorAuthorizationFormDraft(
            form_id=f"form-{case.case_id}",
            case_id=case.case_id,
            packet_id=packet.packet_id,
            payer_form_name="Meridian Health Plan Prior Authorization (MOCK)",
            fields=[
                FormDraftField(
                    field_id="f-service",
                    label="Requested service",
                    value=case.requested_service.service_name,
                    source_claim_ids=[],
                ),
                FormDraftField(
                    field_id="f-summary",
                    label="Clinical summary",
                    value=first_claim.text,
                    source_claim_ids=[first_claim.claim_id],
                ),
            ],
            attestation=(
                "Draft for clinician review. Nothing has been submitted to any "
                "payer, and documentation readiness is not a prediction or "
                "guarantee of approval."
            ),
            generated_at=_now(),
        )
