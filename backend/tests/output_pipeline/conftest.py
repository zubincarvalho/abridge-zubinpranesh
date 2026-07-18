"""Shared synthetic fixtures for the output-pipeline tests (Agent E).

Builds a small, fully synthetic case in the shape upstream stages produce:
criteria, assessments with verbatim-quoted evidence (spans computed from
the actual note text), an answered clarification, and a chart containing
both relevant items and unrelated / sensitive items that must never reach
the packet.
"""

from datetime import datetime, timezone

import pytest

from app.agents.disclosure_agent import DisclosureAgent
from app.agents.packet_generator import PacketGeneratorAgent
from app.agents.verification_agent import VerificationAgent
from app.contracts import (
    AuthLensCase,
    CaseStatus,
    ChartItem,
    ClarificationQuestion,
    ClinicianClarification,
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    EncounterNote,
    EvidenceConfidence,
    EvidenceItem,
    PacketStatus,
    PatientSummary,
    PayerPolicy,
    PolicyCriterion,
    ReadinessSummary,
    RequestedService,
    SourceType,
    TextSpan,
)

FIXED_TIME = datetime(2026, 7, 18, 16, 0, 0, tzinfo=timezone.utc)

NOTE_TEXT = (
    "Follow-up visit for low back pain radiating down the left leg, ongoing "
    "for approximately 8 weeks. She reports difficulty sitting through a full "
    "workday. She denies recent trauma, fever, or unexplained weight loss. "
    "Straight-leg raise is positive on the left at 40 degrees. Plan: MRI "
    "lumbar spine to evaluate for suspected lumbar radiculopathy."
)

CLARIFICATION_TEXT = (
    "The patient completed 8 weeks of physical therapy alongside scheduled "
    "naproxen and a home-exercise program, without sufficient improvement."
)

BACK_CONDITION = "Chronic low back pain with radiation to left leg"
NAPROXEN = "Naproxen 500 mg twice daily"
PT_REFERRAL = "Referral to physical therapy"
UNRELATED_ALLERGY = "Seasonal allergic rhinitis"
UNRELATED_SENSITIVE = "Major depressive disorder, in remission"


def note_evidence(evidence_id: str, excerpt: str) -> EvidenceItem:
    start = NOTE_TEXT.index(excerpt)
    return EvidenceItem(
        evidence_id=evidence_id,
        source_id="note-001",
        source_type=SourceType.ENCOUNTER_NOTE,
        excerpt=excerpt,
        span=TextSpan(start=start, end=start + len(excerpt)),
        confidence=EvidenceConfidence.HIGH,
    )


def build_case() -> AuthLensCase:
    criteria = [
        PolicyCriterion(
            criterion_id="LM-1",
            policy_id="MHP-IMG-2201",
            label="Appropriate clinical indication",
            requirement=(
                "Documented clinical indication of suspected lumbar radiculopathy "
                "or chronic low back pain appropriate for advanced imaging."
            ),
            category="indication",
        ),
        PolicyCriterion(
            criterion_id="LM-2",
            policy_id="MHP-IMG-2201",
            label="Symptom duration at least six weeks",
            requirement="Symptoms documented as present for at least six weeks.",
            category="duration",
        ),
        PolicyCriterion(
            criterion_id="LM-3",
            policy_id="MHP-IMG-2201",
            label="Conservative therapy completed and failed",
            requirement=(
                "At least six weeks of conservative treatment (physical therapy "
                "and scheduled medication) completed and failed to relieve symptoms."
            ),
            category="conservative_therapy",
        ),
    ]

    assessments = [
        CriterionAssessment(
            criterion_id="LM-1",
            status=CriterionStatus.MET,
            denial_risk=DenialRisk.LOW,
            rationale=(
                "The note documents low back pain radiating down the left leg "
                "with suspected lumbar radiculopathy, an appropriate indication "
                "for lumbar MRI."
            ),
            evidence=[
                note_evidence("ev-lm1-note", "low back pain radiating down the left leg"),
                EvidenceItem(
                    evidence_id="ev-lm1-fhir",
                    source_id="fhir-cond-back",
                    source_type=SourceType.FHIR_RESOURCE,
                    excerpt=BACK_CONDITION,
                    fhir_path="Bundle.entry[fhir-cond-back].display",
                    confidence=EvidenceConfidence.HIGH,
                ),
            ],
        ),
        CriterionAssessment(
            criterion_id="LM-2",
            status=CriterionStatus.MET,
            denial_risk=DenialRisk.LOW,
            rationale=(
                "Symptom duration is documented as approximately 8 weeks, "
                "exceeding the six-week requirement."
            ),
            evidence=[note_evidence("ev-lm2-note", "ongoing for approximately 8 weeks")],
        ),
        CriterionAssessment(
            criterion_id="LM-3",
            status=CriterionStatus.MET,
            denial_risk=DenialRisk.LOW,
            rationale=(
                "Per clinician attestation, the patient completed 8 weeks of "
                "physical therapy and scheduled naproxen without sufficient "
                "improvement."
            ),
            evidence=[
                EvidenceItem(
                    evidence_id="ev-lm3-clar",
                    source_id="clar-001",
                    source_type=SourceType.CLINICIAN_CLARIFICATION,
                    excerpt=CLARIFICATION_TEXT,
                    span=TextSpan(start=0, end=len(CLARIFICATION_TEXT)),
                    confidence=EvidenceConfidence.HIGH,
                    note="Clinician attestation recorded verbatim.",
                ),
                EvidenceItem(
                    evidence_id="ev-lm3-ref",
                    source_id="fhir-ref-pt",
                    source_type=SourceType.FHIR_RESOURCE,
                    excerpt=PT_REFERRAL,
                    fhir_path="Bundle.entry[fhir-ref-pt].display",
                    confidence=EvidenceConfidence.LOW,
                    note="A referral is not evidence that therapy was completed.",
                ),
                EvidenceItem(
                    evidence_id="ev-lm3-med",
                    source_id="fhir-med-naproxen",
                    source_type=SourceType.FHIR_RESOURCE,
                    excerpt=NAPROXEN,
                    fhir_path="Bundle.entry[fhir-med-naproxen].display",
                    confidence=EvidenceConfidence.LOW,
                    note="A prescription is not evidence that treatment failed.",
                ),
            ],
            clarification_question_id="q-lm3",
        ),
    ]

    return AuthLensCase(
        case_id="case-test-001",
        status=CaseStatus.AWAITING_CLARIFICATION,
        created_at=FIXED_TIME,
        updated_at=FIXED_TIME,
        patient=PatientSummary(
            patient_id="pat-001",
            display_name="Jordan Rivera",
            birth_date="1979-04-02",
            sex="female",
            chart_items=[
                ChartItem(source_id="fhir-cond-back", category="condition", display=BACK_CONDITION),
                ChartItem(source_id="fhir-med-naproxen", category="medication", display=NAPROXEN),
                ChartItem(source_id="fhir-ref-pt", category="referral", display=PT_REFERRAL),
                ChartItem(source_id="fhir-sr-mri", category="service_request", display="MRI lumbar spine order"),
                ChartItem(source_id="fhir-cond-allergy", category="condition", display=UNRELATED_ALLERGY),
                ChartItem(source_id="fhir-cond-mh", category="condition", display=UNRELATED_SENSITIVE),
            ],
        ),
        requested_service=RequestedService(
            service_name="MRI lumbar spine without contrast",
            code="72148",
            modality="MRI",
            body_site="lumbar spine",
        ),
        clinical_indication=(
            "Chronic low back pain with radicular symptoms; suspected lumbar "
            "radiculopathy"
        ),
        indication_codes=["M54.16"],
        encounter_note=EncounterNote(
            source_id="note-001", title="Low back pain follow-up", text=NOTE_TEXT
        ),
        policy=PayerPolicy(
            policy_id="MHP-IMG-2201",
            payer_name="Meridian Health Plans",
            policy_title="Advanced Imaging: Lumbar Spine MRI",
            service_description="MRI lumbar spine",
            source_document="data/policies/lumbar_mri_policy.md",
        ),
        criteria=criteria,
        assessments=assessments,
        clarification_questions=[
            ClarificationQuestion(
                question_id="q-lm3",
                criterion_ids=["LM-3"],
                question=(
                    "Was the physical therapy course completed, and what was "
                    "the outcome?"
                ),
                why_needed="Documents completion and outcome of conservative therapy.",
                status="answered",
            )
        ],
        clarifications=[
            ClinicianClarification(
                clarification_id="clar-001",
                question_id="q-lm3",
                response=CLARIFICATION_TEXT,
                recorded_at=FIXED_TIME,
            )
        ],
        readiness_history=[
            ReadinessSummary(
                label="post_clarification",
                score=100,
                criteria_met=3,
                criteria_weak=0,
                criteria_missing=0,
                criteria_conflicting=0,
                criteria_not_applicable=0,
                overall_denial_risk=DenialRisk.LOW,
                computed_at=FIXED_TIME,
            )
        ],
    )


def with_disclosure(case: AuthLensCase) -> AuthLensCase:
    return case.model_copy(update={"disclosure_decisions": DisclosureAgent().review(case)})


def generate_packet(case: AuthLensCase):
    disclosed = with_disclosure(case)
    return disclosed, PacketGeneratorAgent().generate(disclosed)


def verified_pipeline(case: AuthLensCase):
    """Run disclosure → packet → verification; mark the packet verified."""
    disclosed, packet = generate_packet(case)
    result = VerificationAgent().verify(packet, disclosed)
    assert result.passed, [i.description for i in result.issues]
    verified = packet.model_copy(update={"status": PacketStatus.VERIFIED})
    return disclosed, verified, result


@pytest.fixture
def case() -> AuthLensCase:
    return build_case()


@pytest.fixture
def disclosed_case(case) -> AuthLensCase:
    return with_disclosure(case)
