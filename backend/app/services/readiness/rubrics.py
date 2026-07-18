"""Deterministic category rubrics: criterion + evidence → CriterionAssessment.

Every classification here is derived only from the supplied evidence items
and verbatim clinician clarifications. When nothing bears on a criterion the
honest output is ``missing`` — never an inference. Hard rules encoded:

- Referral/prescription-only evidence never satisfies completed-therapy.
- Completion without a documented outcome is not failure.
- Vague temporal language never proves an explicit duration.
- Silence on red flags is not a completed negative screen.
- A diagnosis code is not a physical-examination finding.
- Patient-reported support is labeled and classified weak.
- Conflicting documentation stays conflicting until a clinician's
  clarification resolves it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.contracts import (
    ClinicianClarification,
    CriterionAssessment,
    CriterionStatus,
    DenialRisk,
    EvidenceItem,
    EvidenceSource,
    PolicyCriterion,
    SourceType,
)
from app.services.evidence import rules
from app.services.evidence.duration import (
    has_vague_temporal_language,
    is_scheduling_statement,
    parse_durations_days,
    required_days_from_requirement,
)

_CONDITIONAL_MARKERS = ("only if", "applies only", "only when", "conditional")


def _is_conditional(criterion: PolicyCriterion) -> bool:
    note = (criterion.applicability_note or "").lower()
    return any(marker in note for marker in _CONDITIONAL_MARKERS)


def _quote(items: Sequence[EvidenceItem], limit: int = 2) -> str:
    return "; ".join(f'"{item.excerpt}"' for item in items[:limit])


def _assessment(
    criterion: PolicyCriterion,
    status: CriterionStatus,
    risk: DenialRisk,
    rationale: str,
    evidence: Sequence[EvidenceItem],
) -> CriterionAssessment:
    return CriterionAssessment(
        criterion_id=criterion.criterion_id,
        status=status,
        denial_risk=risk,
        rationale=rationale,
        evidence=list(evidence),
    )


def assess_criterion(
    criterion: PolicyCriterion,
    evidence: Sequence[EvidenceItem],
    clarifications: Sequence[ClinicianClarification] = (),
    sources: Mapping[str, EvidenceSource] | None = None,
) -> CriterionAssessment:
    """Classify one criterion deterministically from cited evidence only."""
    if not evidence:
        if _is_conditional(criterion):
            return _assessment(
                criterion,
                CriterionStatus.NOT_APPLICABLE,
                DenialRisk.LOW,
                "The documentation does not establish this conditional criterion's "
                "triggering condition, so it is assessed as not applicable. Subject "
                "to clinician review.",
                [],
            )
        return _assessment(
            criterion,
            CriterionStatus.MISSING,
            DenialRisk.HIGH,
            f"Nothing in the supplied documentation bears on this criterion "
            f"({criterion.label}). Absent documentation is reported as missing, "
            f"never inferred.",
            [],
        )

    rubric = _CATEGORY_RUBRICS.get(criterion.category, _assess_generic)
    return rubric(criterion, list(evidence), sources or {})


# --- category rubrics -------------------------------------------------------


def _assess_duration(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    threshold = required_days_from_requirement(criterion.requirement)
    clarification_items = [
        item for item in evidence if item.source_type == SourceType.CLINICIAN_CLARIFICATION
    ]
    chart_items = [
        item for item in evidence if item.source_type != SourceType.CLINICIAN_CLARIFICATION
    ]

    # A follow-up interval ("return in 4 weeks") is a scheduling instruction,
    # not a symptom duration — exclude it from the duration decision.
    duration_items = [
        item for item in chart_items if not is_scheduling_statement(item.excerpt)
    ]
    chart_durations = [d for item in duration_items for d in parse_durations_days(item.excerpt)]
    meets = [d for d in chart_durations if d >= threshold]
    below = [d for d in chart_durations if d < threshold]

    # A clinician's verbatim clarification is the human review that can
    # resolve a documented discrepancy.
    clar_durations = [
        d for item in clarification_items for d in parse_durations_days(item.excerpt)
    ]
    if clar_durations:
        if min(clar_durations) >= threshold:
            return _assessment(
                criterion,
                CriterionStatus.MET,
                DenialRisk.LOW,
                f"The clinician's clarification documents the symptom duration "
                f"({_quote(clarification_items)}), meeting the documented "
                f"threshold of {threshold / 7:.0f} weeks.",
                evidence,
            )
        return _assessment(
            criterion,
            CriterionStatus.WEAK,
            DenialRisk.HIGH,
            f"The clinician's clarification documents a duration below the "
            f"threshold of {threshold / 7:.0f} weeks ({_quote(clarification_items)}).",
            evidence,
        )

    if meets and below:
        return _assessment(
            criterion,
            CriterionStatus.CONFLICTING,
            DenialRisk.HIGH,
            f"Documented duration statements conflict ({_quote(duration_items, limit=4)}): "
            f"at least one meets the {threshold / 7:.0f}-week threshold and at least "
            f"one does not. The conflict is reported as documented and is left for "
            f"clinician review.",
            evidence,
        )
    if meets:
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"Duration is explicitly documented ({_quote(chart_items)}), meeting "
            f"the {threshold / 7:.0f}-week requirement.",
            evidence,
        )
    if below:
        return _assessment(
            criterion,
            CriterionStatus.WEAK,
            DenialRisk.HIGH,
            f"The documented duration ({_quote(chart_items)}) is below the "
            f"{threshold / 7:.0f}-week threshold in the policy.",
            evidence,
        )
    vague = any(has_vague_temporal_language(item.excerpt) for item in evidence)
    if vague:
        return _assessment(
            criterion,
            CriterionStatus.WEAK,
            DenialRisk.MEDIUM,
            f"The record uses temporal language without an explicit duration "
            f"({_quote(evidence)}). Words like 'persistent' or 'chronic' do not "
            f"document the required number of weeks.",
            evidence,
        )
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"Cited text ({_quote(evidence)}) relates to the symptoms but does not "
        f"document an explicit duration.",
        evidence,
    )


def _assess_conservative_therapy(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    per_item = [(item, rules.therapy_signals(item.excerpt)) for item in evidence]
    failure_items = [item for item, s in per_item if s.completion_and_failure]
    improvement_items = [item for item, s in per_item if s.improvement]
    completion_only_items = [
        item for item, s in per_item if s.completion and not s.failure and not s.improvement
    ]

    if failure_items and improvement_items:
        return _assessment(
            criterion,
            CriterionStatus.CONFLICTING,
            DenialRisk.HIGH,
            f"The documentation conflicts: {_quote(failure_items)} documents "
            f"therapy without sufficient improvement, while "
            f"{_quote(improvement_items)} documents improvement. The conflict is "
            f"left for clinician review.",
            evidence,
        )
    if failure_items:
        attribution = (
            "the clinician's clarification"
            if any(
                item.source_type == SourceType.CLINICIAN_CLARIFICATION
                for item in failure_items
            )
            else "the record"
        )
        below = [
            d
            for item in failure_items
            for d in parse_durations_days(item.excerpt)
        ]
        threshold = required_days_from_requirement(criterion.requirement)
        if below and max(below) < threshold:
            return _assessment(
                criterion,
                CriterionStatus.WEAK,
                DenialRisk.HIGH,
                f"Completion and lack of improvement are documented "
                f"({_quote(failure_items)}), but the documented course is shorter "
                f"than the {threshold / 7:.0f} weeks the policy text requires.",
                evidence,
            )
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"Completion of conservative treatment without sufficient improvement "
            f"is documented in {attribution} ({_quote(failure_items)}).",
            evidence,
        )
    if completion_only_items:
        return _assessment(
            criterion,
            CriterionStatus.WEAK,
            DenialRisk.HIGH,
            f"Completion of conservative treatment is documented "
            f"({_quote(completion_only_items)}), but the outcome is not: completed "
            f"therapy is not, by itself, failed therapy.",
            evidence,
        )
    # Referral / prescription-only support: the criterion's substance —
    # completion and failure — is documented nowhere.
    return _assessment(
        criterion,
        CriterionStatus.MISSING,
        DenialRisk.HIGH,
        f"The record shows conservative-treatment orders ({_quote(evidence, limit=4)}), "
        f"but neither establishes that the treatment was completed without "
        f"sufficient improvement. A referral is not completed therapy and a "
        f"prescription is not treatment failure; completion and outcome are not "
        f"documented anywhere in the supplied sources.",
        evidence,
    )


def _split_patient_reported(
    evidence: list[EvidenceItem], sources: Mapping[str, EvidenceSource]
) -> tuple[list[EvidenceItem], list[EvidenceItem]]:
    patient_reported: list[EvidenceItem] = []
    clinician_documented: list[EvidenceItem] = []
    for item in evidence:
        source = sources.get(item.source_id)
        content = source.content if source else None
        if rules.is_patient_reported(item.excerpt, content, item.source_type):
            patient_reported.append(item)
        else:
            clinician_documented.append(item)
    return patient_reported, clinician_documented


def _assess_exam_findings(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    diagnosis_only = [
        item
        for item in evidence
        if rules.contains_diagnosis_code(item.excerpt)
        and not _has_exam_language(item.excerpt)
    ]
    objective = [
        item
        for item in evidence
        if item not in diagnosis_only and _has_exam_language(item.excerpt)
    ]
    patient_reported, _ = _split_patient_reported(objective, sources)
    objective = [item for item in objective if item not in patient_reported]

    if objective:
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"Examination findings are documented ({_quote(objective)}), consistent "
            f"with the stated indication.",
            evidence,
        )
    if diagnosis_only:
        return _assessment(
            criterion,
            CriterionStatus.WEAK,
            DenialRisk.MEDIUM,
            f"The cited text ({_quote(diagnosis_only)}) is a diagnosis, and a "
            f"diagnosis code is not a physical-examination finding.",
            evidence,
        )
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"The cited text ({_quote(evidence)}) is patient-reported or indirect; no "
        f"clinician-documented examination finding is cited.",
        evidence,
    )


_EXAM_LANGUAGE = (
    "straight-leg",
    "straight leg",
    "sensation",
    "strength",
    "reflex",
    "motor",
    "dermatomal",
    "tenderness",
    "range of motion",
)


def _has_exam_language(text: str) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in _EXAM_LANGUAGE)


def _assess_red_flags(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    screened = [item for item in evidence if rules.documents_red_flag_screening(item.excerpt)]
    if screened:
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"Red-flag screening is explicitly documented with findings noted "
            f"({_quote(screened)}).",
            evidence,
        )
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"The cited text ({_quote(evidence)}) does not document an explicit "
        f"red-flag screening result. Absence of red-flag documentation is not a "
        f"completed negative screen.",
        evidence,
    )


def _assess_functional_limitation(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    patient_reported, clinician_documented = _split_patient_reported(evidence, sources)
    if clinician_documented:
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"A functional limitation attributable to the symptoms is documented "
            f"({_quote(clinician_documented)}).",
            evidence,
        )
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"Functional impact is documented only as a patient-reported statement "
        f"({_quote(patient_reported)}), without further characterization of "
        f"frequency or severity.",
        evidence,
    )


def _assess_indication(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    coded = [item for item in evidence if rules.contains_diagnosis_code(item.excerpt)]
    if coded:
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"An appropriate clinical indication with a diagnosis code is "
            f"documented ({_quote(coded)}).",
            evidence,
        )
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"An indication is described ({_quote(evidence)}) but no corresponding "
        f"diagnosis code is cited.",
        evidence,
    )


_MANAGEMENT_CHANGE_LANGUAGE = (
    "evaluate",
    "assess",
    "candidacy",
    "guide",
    "inform",
    "surgical",
    "injection",
    "change management",
    "treatment planning",
)


def _assess_rationale(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    lowered = [(item, item.excerpt.lower()) for item in evidence]
    supported = [
        item
        for item, text in lowered
        if any(term in text for term in _MANAGEMENT_CHANGE_LANGUAGE)
    ]
    if supported:
        return _assessment(
            criterion,
            CriterionStatus.MET,
            DenialRisk.LOW,
            f"The record documents how the results are expected to change "
            f"management ({_quote(supported)}).",
            evidence,
        )
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"The cited text ({_quote(evidence)}) does not document why the study is "
        f"expected to change management.",
        evidence,
    )


def _assess_generic(
    criterion: PolicyCriterion,
    evidence: list[EvidenceItem],
    sources: Mapping[str, EvidenceSource],
) -> CriterionAssessment:
    return _assessment(
        criterion,
        CriterionStatus.WEAK,
        DenialRisk.MEDIUM,
        f"Evidence is cited ({_quote(evidence)}) but this criterion's category "
        f"has no specific rubric; support is graded as weak pending clinician "
        f"review.",
        evidence,
    )


_CATEGORY_RUBRICS = {
    "indication": _assess_indication,
    "duration": _assess_duration,
    "conservative_therapy": _assess_conservative_therapy,
    "exam_findings": _assess_exam_findings,
    "red_flags": _assess_red_flags,
    "functional_limitation": _assess_functional_limitation,
    "rationale": _assess_rationale,
}
