"""Programmatic (non-LLM) gates the orchestrator runs between stages.

These are the deterministic checks from docs/AGENT_WORKFLOWS.md §1: excerpts
must appear verbatim in their source, every criterion gets exactly one
assessment, packet claims cite known evidence from INCLUDE'd sources only,
and stage outputs must be internally consistent. A gate violation raises
StageExecutionError and rolls the operation back — gates are never skipped
on retries.
"""

from app.contracts import (
    AuthLensCase,
    ClaimType,
    ClarificationQuestion,
    CriterionAssessment,
    DisclosureDecision,
    DisclosureDecisionType,
    EvidenceItem,
    PacketStatus,
    PolicyCriterion,
    PriorAuthorizationPacket,
    ReadinessSummary,
    VerificationResult,
    VerificationSeverity,
)

from app.orchestration.errors import StageExecutionError


def _fail(stage: str, case_id: str, message: str) -> StageExecutionError:
    return StageExecutionError(
        f"{stage} gate failed: {message}", case_id=case_id, stage=stage
    )


def check_criteria(case: AuthLensCase, criteria: list[PolicyCriterion]) -> None:
    if not criteria:
        raise _fail("policy_parsing", case.case_id, "no criteria parsed from policy")
    ids = [c.criterion_id for c in criteria]
    if len(set(ids)) != len(ids):
        raise _fail("policy_parsing", case.case_id, "duplicate criterion ids")
    for criterion in criteria:
        if criterion.policy_id != case.policy.policy_id:
            raise _fail(
                "policy_parsing",
                case.case_id,
                f"criterion {criterion.criterion_id} references a different policy",
            )


def resolvable_source_contents(case: AuthLensCase) -> dict[str, str]:
    """Source contents the orchestrator can resolve locally for verbatim checks.

    FHIR resource content lives behind Agent A's adapters, so unknown
    source ids are skipped here; the independent verifier re-checks all
    citations at the verification stage.
    """
    contents: dict[str, str] = {case.encounter_note.source_id: case.encounter_note.text}
    if case.encounter_transcript is not None:
        contents[case.encounter_transcript.source_id] = case.encounter_transcript.text
    for item in case.patient.chart_items:
        contents[item.source_id] = (
            item.display if item.detail is None else f"{item.display}\n{item.detail}"
        )
    for clarification in case.clarifications:
        contents[clarification.clarification_id] = clarification.response
    return contents


def check_evidence_verbatim(
    case: AuthLensCase, evidence_items: list[EvidenceItem]
) -> None:
    contents = resolvable_source_contents(case)
    seen_ids: set[str] = set()
    for item in evidence_items:
        if item.evidence_id in seen_ids:
            raise _fail(
                "evidence_mapping", case.case_id, f"duplicate evidence id {item.evidence_id}"
            )
        seen_ids.add(item.evidence_id)
        content = contents.get(item.source_id)
        if content is None:
            continue
        if item.excerpt not in content:
            raise _fail(
                "evidence_mapping",
                case.case_id,
                f"evidence {item.evidence_id} excerpt is not a verbatim quote of "
                f"source {item.source_id}",
            )
        if item.span is not None and content[item.span.start : item.span.end] != item.excerpt:
            raise _fail(
                "evidence_mapping",
                case.case_id,
                f"evidence {item.evidence_id} span does not match its excerpt",
            )


def check_assessments(
    case: AuthLensCase,
    criteria: list[PolicyCriterion],
    assessments: list[CriterionAssessment],
) -> None:
    """Every criterion receives exactly one assessment."""
    expected = [c.criterion_id for c in criteria]
    got = [a.criterion_id for a in assessments]
    if sorted(got) != sorted(expected):
        raise _fail(
            "gap_detection",
            case.case_id,
            "assessments do not cover each criterion exactly once",
        )


def check_questions(
    case: AuthLensCase,
    criteria: list[PolicyCriterion],
    questions: list[ClarificationQuestion],
) -> None:
    criterion_ids = {c.criterion_id for c in criteria}
    seen: set[str] = set()
    for question in questions:
        if question.question_id in seen:
            raise _fail(
                "gap_detection", case.case_id, f"duplicate question id {question.question_id}"
            )
        seen.add(question.question_id)
        if not set(question.criterion_ids) <= criterion_ids:
            raise _fail(
                "gap_detection",
                case.case_id,
                f"question {question.question_id} references unknown criteria",
            )


def check_readiness(case: AuthLensCase, readiness: ReadinessSummary, total: int) -> None:
    counted = (
        readiness.criteria_met
        + readiness.criteria_weak
        + readiness.criteria_missing
        + readiness.criteria_conflicting
        + readiness.criteria_not_applicable
    )
    if counted != total:
        raise _fail(
            "gap_detection",
            case.case_id,
            f"readiness counts ({counted}) do not sum to assessment count ({total})",
        )


def check_disclosure_decisions(
    case: AuthLensCase, decisions: list[DisclosureDecision]
) -> None:
    seen: set[str] = set()
    for decision in decisions:
        if decision.decision_id in seen:
            raise _fail(
                "disclosure_review",
                case.case_id,
                f"duplicate decision id {decision.decision_id}",
            )
        seen.add(decision.decision_id)
        if not decision.reason.strip():
            raise _fail(
                "disclosure_review",
                case.case_id,
                f"decision {decision.decision_id} has no stated reason",
            )


def check_packet(case: AuthLensCase, packet: PriorAuthorizationPacket) -> None:
    """Draft-only status, cited clinical claims, no excluded-source citations."""
    stage = "packet_generation"
    if packet.case_id != case.case_id:
        raise _fail(stage, case.case_id, "packet references a different case")
    if packet.status is not PacketStatus.DRAFT:
        raise _fail(
            stage,
            case.case_id,
            "generator returned a non-draft packet; only verification may change "
            "packet status",
        )
    evidence_source = {
        item.evidence_id: item.source_id
        for assessment in case.assessments
        for item in assessment.evidence
    }
    excluded = {
        d.source_id
        for d in case.disclosure_decisions
        if d.decision is DisclosureDecisionType.EXCLUDE
    }
    claim_ids: set[str] = set()
    for claim in packet.claims:
        if claim.claim_id in claim_ids:
            raise _fail(stage, case.case_id, f"duplicate claim id {claim.claim_id}")
        claim_ids.add(claim.claim_id)
        if claim.claim_type is ClaimType.CLINICAL:
            if not claim.evidence_ids:
                raise _fail(
                    stage,
                    case.case_id,
                    f"clinical claim {claim.claim_id} cites no evidence",
                )
            for evidence_id in claim.evidence_ids:
                source_id = evidence_source.get(evidence_id)
                if source_id is None:
                    raise _fail(
                        stage,
                        case.case_id,
                        f"claim {claim.claim_id} cites unknown evidence {evidence_id}",
                    )
                if source_id in excluded:
                    raise _fail(
                        stage,
                        case.case_id,
                        f"claim {claim.claim_id} cites evidence from excluded "
                        f"source {source_id}",
                    )
    for section in packet.sections:
        for claim_id in section.claim_ids:
            if claim_id not in claim_ids:
                raise _fail(
                    stage,
                    case.case_id,
                    f"section {section.section_id} references unknown claim {claim_id}",
                )


def check_verification(
    case: AuthLensCase,
    packet: PriorAuthorizationPacket,
    result: VerificationResult,
) -> None:
    """The verifier's pass/fail flag must be consistent with its own issues."""
    stage = "verification"
    if result.packet_id != packet.packet_id:
        raise _fail(stage, case.case_id, "verification references a different packet")
    blocking = [
        issue for issue in result.issues
        if issue.severity is VerificationSeverity.BLOCKING
    ]
    if result.passed and blocking:
        raise _fail(
            stage, case.case_id, "verifier reported passed=True with blocking issues"
        )
    if not result.passed and not blocking:
        raise _fail(
            stage, case.case_id, "verifier reported passed=False without blocking issues"
        )
