"""Clarification-question generation for weak and missing criteria.

At most one focused question per gapped criterion. A question is raised for
every missing or conflicting criterion and for weak criteria whose
documentation gap carries high denial risk; a weak-but-honest criterion at
low/medium risk is surfaced in the readiness matrix without interrupting
the clinician (matches the frozen demo payloads, where LM-3 gets the only
question). Questions ask what was documented or done — never what should be
done (no treatment recommendations, docs/SAFETY_AND_HUMAN_REVIEW.md rule 2).
"""

from __future__ import annotations

from collections.abc import Sequence

from app.contracts import (
    ClarificationQuestion,
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    PolicyCriterion,
)

# The demo-critical LM-3 wording, fixed by the fixture's
# expected_demo_clarification (data/fixtures/lumbar_mri_prior_auth.json).
LM3_QUESTION = (
    "Have you completed at least six weeks of physical therapy, "
    "anti-inflammatory medication, or a home-exercise program without "
    "sufficient improvement?"
)

def needs_question(assessment: CriterionAssessment) -> bool:
    if assessment.status in (CriterionStatus.MISSING, CriterionStatus.CONFLICTING):
        return True
    return (
        assessment.status == CriterionStatus.WEAK
        and assessment.denial_risk == DenialRisk.HIGH
    )

_CATEGORY_QUESTIONS: dict[str, tuple[str, str, str]] = {
    # category -> (question, why_needed, suggested_action)
    "conservative_therapy": (
        LM3_QUESTION,
        "The chart shows an NSAID on the medication list and a physical-therapy "
        "referral, but the policy requires documentation that at least six weeks "
        "of conservative treatment were completed without sufficient improvement. "
        "A referral or a prescription alone does not establish completion or "
        "failure.",
        "Confirm completion and outcome of conservative therapy; AuthLens will "
        "record your answer verbatim and re-evaluate.",
    ),
    "duration": (
        "How long have the symptoms been present, and where is that duration "
        "documented?",
        "The policy requires the symptom duration to be explicitly documented; "
        "the record does not currently state a specific duration that satisfies "
        "the threshold.",
        "State the symptom duration explicitly; AuthLens will record your answer "
        "verbatim and re-evaluate.",
    ),
    "indication": (
        "What clinical indication and diagnosis code were documented for this "
        "study?",
        "The policy requires an appropriate indication with a corresponding "
        "diagnosis code, and the record does not currently document one.",
        "Document the indication and diagnosis code; AuthLens will record your "
        "answer verbatim and re-evaluate.",
    ),
    "exam_findings": (
        "What neurologic or physical-examination findings were observed at this "
        "or a prior visit?",
        "The policy requires clinician-documented examination findings consistent "
        "with the indication; the record does not currently cite one.",
        "Document the examination findings observed; AuthLens will record your "
        "answer verbatim and re-evaluate.",
    ),
    "red_flags": (
        "Was red-flag screening performed, and what were the findings "
        "(present or absent)?",
        "The policy requires documented red-flag screening with findings noted; "
        "absence of red-flag documentation is not a completed negative screen.",
        "Document the screening performed and its findings; AuthLens will record "
        "your answer verbatim and re-evaluate.",
    ),
    "functional_limitation": (
        "What functional limitation (work, activities of daily living, or sleep) "
        "has the patient experienced from these symptoms?",
        "The policy requires a documented functional limitation attributable to "
        "the symptoms; the current documentation does not fully characterize one.",
        "Describe the functional limitation; AuthLens will record your answer "
        "verbatim and re-evaluate.",
    ),
    "rationale": (
        "How are the results of this study expected to change management?",
        "The policy requires documentation of why the study results are expected "
        "to change management, and the record does not currently state this.",
        "Document the management decision the results will inform; AuthLens will "
        "record your answer verbatim and re-evaluate.",
    ),
}

_GENERIC_QUESTION = (
    "What documentation exists for this requirement: {label}?",
    "The policy criterion '{label}' is not fully supported by the current "
    "documentation.",
    "Document what was done or observed; AuthLens will record your answer "
    "verbatim and re-evaluate.",
)


def question_id_for(criterion_id: str) -> str:
    return f"q-{criterion_id.lower().replace('-', '')}-001"


def generate_clarifications(
    assessments: Sequence[CriterionAssessment],
    criteria: Sequence[PolicyCriterion],
) -> list[ClarificationQuestion]:
    """At most one open question per weak/missing criterion, in criterion order."""
    by_id = {c.criterion_id: c for c in criteria}
    questions: list[ClarificationQuestion] = []
    for assessment in assessments:
        if not needs_question(assessment):
            continue
        criterion = by_id.get(assessment.criterion_id)
        if criterion is None:
            continue
        template = _CATEGORY_QUESTIONS.get(criterion.category)
        if template is not None:
            question, why_needed, suggested_action = template
        else:
            question, why_needed, suggested_action = (
                part.format(label=criterion.label) for part in _GENERIC_QUESTION
            )
        questions.append(
            ClarificationQuestion(
                question_id=question_id_for(criterion.criterion_id),
                criterion_ids=[criterion.criterion_id],
                question=question,
                why_needed=why_needed,
                suggested_action=suggested_action,
                status="open",
            )
        )
    return questions
