"""Deterministic AuthLens workflow orchestrator (implements the frozen
``app.ports.workflow_orchestrator.WorkflowOrchestrator`` protocol).

Plain Python control flow: fixed stage order per operation, every status
change validated against the frozen ``ALLOWED_TRANSITIONS`` table, paired
started/completed/failed AgentEvent records around every stage, and
programmatic gates between stages (app.orchestration.gates). No prompts, no
LLM calls, no submission path — ``ready_for_review`` is terminal.

Failure posture (docs/SAFETY_AND_HUMAN_REVIEW.md): a stage failure or
timeout records a ``failed`` event and rolls the case back to its
pre-operation state, so retries re-run every stage and every safety gate.
"""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from app.config import REPO_ROOT
from app.contracts import (
    AgentEvent,
    AgentStage,
    AuthLensCase,
    CaseStatus,
    ClarificationSubmission,
    ClinicianClarification,
    CriterionAssessment,
    DisclosureDecisionType,
    EvidenceCandidate,
    EvidenceItem,
    PacketStatus,
    PayerPolicy,
    PolicyCriterion,
)
from app.events import EventRecorder, utc_now
from app.ports import (
    CaseRepository,
    DisclosureFilter,
    EvidenceMapper,
    EvidenceRetriever,
    FormDrafter,
    GapDetector,
    PacketGenerator,
    PacketVerifier,
    PolicyParser,
)

from app.orchestration import gates
from app.orchestration.errors import (
    PacketNotVerifiedError,
    QuestionAlreadyAnsweredError,
    QuestionNotFoundError,
    StageExecutionError,
)
from app.orchestration.stage_runner import call_with_timeout
from app.services.cases import (
    CaseOperationError,
    CaseService,
    apply_transition,
    require_status,
    validate_intake,
)

T = TypeVar("T")

# Per docs/AGENT_WORKFLOWS.md §5 the retriever's internal reformulation loop
# is bounded at 3 iterations; the orchestrator additionally bounds its own
# invocation attempts per criterion at the same number.
MAX_RETRIEVAL_ATTEMPTS = 3


def _default_policy_text_loader(policy: PayerPolicy) -> str:
    path = Path(policy.source_document)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.read_text(encoding="utf-8")


def _public_error(exc: Exception) -> str:
    """Timeline-safe error description: our own messages, or just a type name."""
    if isinstance(exc, CaseOperationError):
        return str(exc)
    return f"unexpected {type(exc).__name__}; details withheld from the timeline"


class AuthLensOrchestrator:
    def __init__(
        self,
        repository: CaseRepository,
        *,
        policy_parser: PolicyParser,
        evidence_retriever: EvidenceRetriever,
        evidence_mapper: EvidenceMapper,
        gap_detector: GapDetector,
        disclosure_filter: DisclosureFilter,
        packet_generator: PacketGenerator,
        packet_verifier: PacketVerifier,
        form_drafter: FormDrafter,
        policy_text_loader: Callable[[PayerPolicy], str] | None = None,
        clock: Callable[[], datetime] | None = None,
        stage_timeout_seconds: float = 120.0,
        max_parallel_retrievals: int = 8,
    ) -> None:
        self._cases = CaseService(repository, clock=clock)
        self._policy_parser = policy_parser
        self._evidence_retriever = evidence_retriever
        self._evidence_mapper = evidence_mapper
        self._gap_detector = gap_detector
        self._disclosure_filter = disclosure_filter
        self._packet_generator = packet_generator
        self._packet_verifier = packet_verifier
        self._form_drafter = form_drafter
        self._policy_text_loader = policy_text_loader or _default_policy_text_loader
        self._clock = clock or utc_now
        self._recorder = EventRecorder(clock)
        self._stage_timeout_seconds = stage_timeout_seconds
        self._max_parallel_retrievals = max_parallel_retrievals
        self._case_locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    # ------------------------------------------------------------------ reads

    def get_case(self, case_id: str) -> AuthLensCase:
        return self._cases.get_case(case_id)

    def get_events(self, case_id: str) -> list[AgentEvent]:
        case = self._cases.get_case(case_id)
        return sorted(case.events, key=lambda event: event.sequence)

    # ------------------------------------------------------------- operations

    def start_analysis(self, case_id: str) -> AuthLensCase:
        """intake_ready -> analyzing -> awaiting_clarification."""
        with self._case_lock(case_id):
            original = self._cases.get_case(case_id)
            require_status(original, (CaseStatus.INTAKE_READY,), "run")
            case = original.model_copy(deep=True)
            apply_transition(case, CaseStatus.ANALYZING, now=self._clock())
            try:
                self._run_analysis(case)
                apply_transition(
                    case, CaseStatus.AWAITING_CLARIFICATION, now=self._clock()
                )
                return self._cases.save_case(case)
            except Exception:
                self._rollback(original, case)
                raise

    def submit_clarification(
        self, case_id: str, submission: ClarificationSubmission
    ) -> AuthLensCase:
        """awaiting_clarification -> reanalyzing -> awaiting_clarification."""
        with self._case_lock(case_id):
            original = self._cases.get_case(case_id)
            require_status(
                original, (CaseStatus.AWAITING_CLARIFICATION,), "clarifications"
            )
            case = original.model_copy(deep=True)
            question = next(
                (
                    q
                    for q in case.clarification_questions
                    if q.question_id == submission.question_id
                ),
                None,
            )
            if question is None:
                raise QuestionNotFoundError(case_id, submission.question_id)
            if question.status == "answered":
                raise QuestionAlreadyAnsweredError(case_id, submission.question_id)
            apply_transition(case, CaseStatus.REANALYZING, now=self._clock())
            try:
                self._run_reanalysis(case, question.question_id, submission.response)
                apply_transition(
                    case, CaseStatus.AWAITING_CLARIFICATION, now=self._clock()
                )
                return self._cases.save_case(case)
            except Exception:
                self._rollback(original, case)
                raise

    def generate_packet(self, case_id: str) -> AuthLensCase:
        """awaiting_clarification | verification_failed -> packet_drafted."""
        with self._case_lock(case_id):
            original = self._cases.get_case(case_id)
            require_status(
                original,
                (CaseStatus.AWAITING_CLARIFICATION, CaseStatus.VERIFICATION_FAILED),
                "generate-packet",
            )
            case = original.model_copy(deep=True)
            regenerating = case.status is CaseStatus.VERIFICATION_FAILED
            try:
                self._run_packet_pipeline(case, regenerating)
                apply_transition(case, CaseStatus.PACKET_DRAFTED, now=self._clock())
                return self._cases.save_case(case)
            except Exception:
                self._rollback(original, case)
                raise

    def verify_packet(self, case_id: str) -> AuthLensCase:
        """packet_drafted -> verified | verification_failed."""
        with self._case_lock(case_id):
            original = self._cases.get_case(case_id)
            require_status(original, (CaseStatus.PACKET_DRAFTED,), "verify")
            case = original.model_copy(deep=True)
            packet = case.packet
            if packet is None:
                raise StageExecutionError(
                    "no packet to verify", case_id=case_id, stage="verification"
                )
            try:
                result = self._stage(
                    case,
                    AgentStage.VERIFICATION,
                    "Verification Agent",
                    lambda: self._verify_checked(case, packet),
                    related_ids=[packet.packet_id],
                    detail_on_complete=lambda r: (
                        f"Checked {r.checked_claim_count} claim(s); "
                        f"{len(r.issues)} issue(s); passed={r.passed}"
                    ),
                )
                case.verification = result
                if result.passed:
                    packet.status = PacketStatus.VERIFIED
                    apply_transition(case, CaseStatus.VERIFIED, now=self._clock())
                else:
                    packet.status = PacketStatus.VERIFICATION_FAILED
                    apply_transition(
                        case, CaseStatus.VERIFICATION_FAILED, now=self._clock()
                    )
                return self._cases.save_case(case)
            except Exception:
                self._rollback(original, case)
                raise

    def draft_form(self, case_id: str) -> AuthLensCase:
        """verified -> ready_for_review. Requires a passing verification."""
        with self._case_lock(case_id):
            original = self._cases.get_case(case_id)
            if original.status in (
                CaseStatus.PACKET_DRAFTED,
                CaseStatus.VERIFICATION_FAILED,
            ):
                raise PacketNotVerifiedError(
                    case_id,
                    f"case is {original.status.value!r}; a passing verification "
                    "is required before form drafting",
                )
            require_status(original, (CaseStatus.VERIFIED,), "form-draft")
            case = original.model_copy(deep=True)
            packet, verification = case.packet, case.verification
            if (
                packet is None
                or verification is None
                or not verification.passed
                or verification.packet_id != packet.packet_id
                or packet.status is not PacketStatus.VERIFIED
            ):
                raise PacketNotVerifiedError(
                    case_id, "stored packet/verification pair is not a passing one"
                )
            try:
                form = self._stage(
                    case,
                    AgentStage.FORM_DRAFTING,
                    "Form Agent",
                    lambda: self._form_drafter.draft(packet, verification, case),
                    related_ids=[packet.packet_id],
                    detail_on_complete=lambda f: (
                        f"Drafted {len(f.fields)} field(s) for {f.payer_form_name}"
                    ),
                )
                if form.case_id != case.case_id or form.packet_id != packet.packet_id:
                    raise StageExecutionError(
                        "form draft references a different case or packet",
                        case_id=case_id,
                        stage="form_drafting",
                    )
                case.form_draft = form
                apply_transition(case, CaseStatus.READY_FOR_REVIEW, now=self._clock())
                self._recorder.started(
                    case,
                    AgentStage.HUMAN_REVIEW,
                    "Ready for Clinician Review",
                    detail=(
                        "Terminal state. A human clinician reviews and acts outside "
                        "AuthLens; nothing is submitted by the system."
                    ),
                    related_ids=[form.form_id],
                )
                return self._cases.save_case(case)
            except Exception:
                self._rollback(original, case)
                raise

    # -------------------------------------------------------------- pipelines

    def _run_analysis(self, case: AuthLensCase) -> None:
        # 1. Intake validation
        self._stage(
            case,
            AgentStage.INTAKE,
            "Intake validation",
            lambda: validate_intake(case),
            related_ids=[case.encounter_note.source_id],
            detail_on_complete=lambda _: "Required intake inputs are present",
        )

        # 2. Policy parsing
        policy_text = self._policy_text_loader(case.policy)
        criteria = self._stage(
            case,
            AgentStage.POLICY_PARSING,
            "Policy Agent",
            lambda: self._parse_policy_checked(case, policy_text),
            related_ids=[case.policy.policy_id],
            detail_on_complete=lambda cs: (
                f"Parsed {len(cs)} criteria from policy {case.policy.policy_id}"
            ),
            related_on_complete=lambda cs: [c.criterion_id for c in cs],
        )
        case.criteria = criteria

        # 3. Parallel evidence retrieval
        candidates_by_criterion = self._stage(
            case,
            AgentStage.EVIDENCE_RETRIEVAL,
            "Evidence Retrieval",
            lambda: self._retrieve_parallel(case, criteria),
            related_ids=[c.criterion_id for c in criteria],
            detail_on_complete=lambda by: (
                f"{sum(len(v) for v in by.values())} candidate(s) across "
                f"{len(by)} criteria (parallel, bounded at "
                f"{MAX_RETRIEVAL_ATTEMPTS} iterations per criterion)"
            ),
        )

        # 4. Evidence mapping
        evidence_by_criterion = self._stage(
            case,
            AgentStage.EVIDENCE_MAPPING,
            "Evidence Mapper",
            lambda: self._map_evidence(case, criteria, candidates_by_criterion),
            detail_on_complete=lambda by: (
                f"Accepted {sum(len(v) for v in by.values())} evidence item(s); "
                "excerpts verified verbatim against resolvable sources"
            ),
        )

        # 5. Gap detection + clarification questions
        assessments, questions = self._stage(
            case,
            AgentStage.GAP_DETECTION,
            "Gap Detector",
            lambda: self._assess_all(case, criteria, evidence_by_criterion),
            detail_on_complete=lambda pair: self._assessment_summary(pair[0]),
            related_on_complete=lambda pair: [a.criterion_id for a in pair[0]],
        )
        case.assessments = assessments
        case.clarification_questions = questions

        # 6. Documentation readiness (deterministic)
        self._append_readiness(case, label="initial")

        # 7. Pause for clarification
        open_questions = [q for q in questions if q.status == "open"]
        if open_questions:
            self._recorder.started(
                case,
                AgentStage.CLARIFICATION,
                "Clinician Clarification",
                detail=(
                    f"Paused: {len(open_questions)} open question(s) await the "
                    "clinician"
                ),
                related_ids=[q.question_id for q in open_questions],
            )
        else:
            self._recorder.skipped(
                case,
                AgentStage.CLARIFICATION,
                "Clinician Clarification",
                detail="No documentation gaps require clarification",
            )

    def _run_reanalysis(
        self, case: AuthLensCase, question_id: str, response: str
    ) -> None:
        question = next(
            q for q in case.clarification_questions if q.question_id == question_id
        )
        # 8. Resume after clarification: record the answer verbatim.
        clarification = ClinicianClarification(
            clarification_id=f"clar-{question_id}",
            question_id=question_id,
            response=response,
            recorded_at=self._clock(),
        )
        case.clarifications.append(clarification)
        question.status = "answered"
        self._recorder.completed(
            case,
            AgentStage.CLARIFICATION,
            "Clinician Clarification",
            detail=f"Answer to {question_id} recorded verbatim; workflow resumed",
            related_ids=[question_id, clarification.clarification_id],
        )

        # 9. Re-retrieve, re-map, and re-assess only the affected criteria.
        affected_ids = set(question.criterion_ids)
        affected = [c for c in case.criteria if c.criterion_id in affected_ids]
        before = {
            a.criterion_id: a.status.value
            for a in case.assessments
            if a.criterion_id in affected_ids
        }
        candidates_by_criterion = self._stage(
            case,
            AgentStage.EVIDENCE_RETRIEVAL,
            "Evidence Retrieval (re-run)",
            lambda: self._retrieve_parallel(case, affected),
            related_ids=sorted(affected_ids),
            detail_on_complete=lambda by: (
                f"{sum(len(v) for v in by.values())} candidate(s) for "
                f"{len(by)} affected criteria (clarifications searched)"
            ),
        )
        evidence_by_criterion = self._stage(
            case,
            AgentStage.EVIDENCE_MAPPING,
            "Evidence Mapper (re-run)",
            lambda: self._map_evidence(case, affected, candidates_by_criterion),
            detail_on_complete=lambda by: (
                f"Accepted {sum(len(v) for v in by.values())} evidence item(s) "
                "for affected criteria"
            ),
        )
        reassessed, _ = self._stage(
            case,
            AgentStage.GAP_DETECTION,
            "Gap Detector (re-run)",
            lambda: self._assess_all(case, affected, evidence_by_criterion),
            detail_on_complete=lambda pair: self._before_after_summary(
                before, pair[0]
            ),
            related_on_complete=lambda pair: [a.criterion_id for a in pair[0]],
        )
        by_id = {a.criterion_id: a for a in reassessed}
        case.assessments = [
            by_id.get(a.criterion_id, a) for a in case.assessments
        ]

        # 10 (readiness update). Prior snapshots are preserved in the history.
        self._append_readiness(
            case, label=f"post_clarification_{len(case.clarifications)}"
        )

        remaining = [
            q for q in case.clarification_questions if q.status == "open"
        ]
        if remaining:
            self._recorder.started(
                case,
                AgentStage.CLARIFICATION,
                "Clinician Clarification",
                detail=f"Paused again: {len(remaining)} question(s) still open",
                related_ids=[q.question_id for q in remaining],
            )

    def _run_packet_pipeline(self, case: AuthLensCase, regenerating: bool) -> None:
        # 10. Disclosure minimization
        decisions = self._stage(
            case,
            AgentStage.DISCLOSURE_REVIEW,
            "Disclosure Agent",
            lambda: self._review_disclosure_checked(case),
            detail_on_complete=lambda ds: (
                f"{sum(1 for d in ds if d.decision is DisclosureDecisionType.INCLUDE)}"
                " included, "
                f"{sum(1 for d in ds if d.decision is DisclosureDecisionType.EXCLUDE)}"
                " excluded (default is exclusion)"
            ),
            related_on_complete=lambda ds: [d.source_id for d in ds],
        )
        case.disclosure_decisions = decisions

        # 11. Packet generation (on regeneration, the generator sees the prior
        # verification issues on the case before we clear them).
        packet = self._stage(
            case,
            AgentStage.PACKET_GENERATION,
            "Packet Agent" + (" (regeneration)" if regenerating else ""),
            lambda: self._generate_packet_checked(case),
            detail_on_complete=lambda p: (
                f"Drafted {len(p.claims)} claim(s) across {len(p.sections)} "
                "section(s); every clinical claim cites evidence"
            ),
            related_on_complete=lambda p: [p.packet_id],
        )
        case.packet = packet
        case.verification = None  # a fresh draft is unverified by definition

    # -------------------------------------------------------------- internals

    def _case_lock(self, case_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._case_locks.setdefault(case_id, threading.Lock())

    def _rollback(self, original: AuthLensCase, working: AuthLensCase) -> None:
        """Restore the pre-operation case state, keeping the timeline events."""
        restored = original.model_copy(deep=True)
        restored.events = [event.model_copy(deep=True) for event in working.events]
        restored.updated_at = self._clock()
        self._cases.save_case(restored)

    def _stage(
        self,
        case: AuthLensCase,
        stage: AgentStage,
        title: str,
        fn: Callable[[], T],
        *,
        related_ids: list[str] | None = None,
        detail_on_complete: Callable[[T], str] | None = None,
        related_on_complete: Callable[[T], list[str]] | None = None,
    ) -> T:
        """Run one stage with paired events and a wall-clock budget."""
        self._recorder.started(case, stage, f"{title} started", related_ids=related_ids)
        try:
            result = call_with_timeout(
                fn,
                timeout_seconds=self._stage_timeout_seconds,
                stage=stage.value,
                case_id=case.case_id,
            )
        except Exception as exc:
            self._recorder.failed(
                case,
                stage,
                f"{title} failed",
                detail=_public_error(exc),
                related_ids=related_ids,
            )
            if isinstance(exc, CaseOperationError):
                raise
            raise StageExecutionError(
                f"{stage.value} stage failed", case_id=case.case_id, stage=stage.value
            ) from exc
        completed_related = (
            related_on_complete(result) if related_on_complete else related_ids
        )
        self._recorder.completed(
            case,
            stage,
            f"{title} completed",
            detail=detail_on_complete(result) if detail_on_complete else None,
            related_ids=completed_related,
        )
        return result

    def _retrieve_parallel(
        self, case: AuthLensCase, criteria: list[PolicyCriterion]
    ) -> dict[str, list[EvidenceCandidate]]:
        results: dict[str, list[EvidenceCandidate]] = {}
        if not criteria:
            return results
        executor = ThreadPoolExecutor(
            max_workers=min(len(criteria), self._max_parallel_retrievals),
            thread_name_prefix="retrieval",
        )
        try:
            futures = {
                criterion.criterion_id: executor.submit(
                    self._retrieve_one, case, criterion
                )
                for criterion in criteria
            }
            for criterion_id, future in futures.items():
                results[criterion_id] = future.result()
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
        return results

    def _retrieve_one(
        self, case: AuthLensCase, criterion: PolicyCriterion
    ) -> list[EvidenceCandidate]:
        last_error: Exception | None = None
        for _ in range(MAX_RETRIEVAL_ATTEMPTS):
            try:
                candidates = self._evidence_retriever.retrieve(case, criterion)
                break
            except Exception as exc:  # bounded retry, then honest failure
                last_error = exc
        else:
            raise StageExecutionError(
                f"evidence retrieval failed for criterion {criterion.criterion_id} "
                f"after {MAX_RETRIEVAL_ATTEMPTS} attempts",
                case_id=case.case_id,
                stage="evidence_retrieval",
            ) from last_error
        for candidate in candidates:
            if candidate.criterion_id != criterion.criterion_id:
                raise StageExecutionError(
                    f"retriever returned a candidate for the wrong criterion "
                    f"({candidate.criterion_id!r} != {criterion.criterion_id!r})",
                    case_id=case.case_id,
                    stage="evidence_retrieval",
                )
        return candidates

    def _map_evidence(
        self,
        case: AuthLensCase,
        criteria: list[PolicyCriterion],
        candidates_by_criterion: dict[str, list[EvidenceCandidate]],
    ) -> dict[str, list[EvidenceItem]]:
        evidence_by_criterion: dict[str, list[EvidenceItem]] = {}
        for criterion in criteria:
            items = self._evidence_mapper.map_evidence(
                criterion, candidates_by_criterion.get(criterion.criterion_id, [])
            )
            evidence_by_criterion[criterion.criterion_id] = items
        gates.check_evidence_verbatim(
            case, [item for items in evidence_by_criterion.values() for item in items]
        )
        return evidence_by_criterion

    def _assess_all(
        self,
        case: AuthLensCase,
        criteria: list[PolicyCriterion],
        evidence_by_criterion: dict[str, list[EvidenceItem]],
    ) -> tuple[list[CriterionAssessment], list]:
        assessments = [
            self._gap_detector.assess(
                criterion,
                evidence_by_criterion.get(criterion.criterion_id, []),
                case.clarifications,
            )
            for criterion in criteria
        ]
        gates.check_assessments(case, criteria, assessments)
        questions = self._gap_detector.generate_clarifications(
            assessments, case.criteria
        )
        gates.check_questions(case, case.criteria, questions)
        return assessments, questions

    def _append_readiness(self, case: AuthLensCase, *, label: str) -> None:
        readiness = self._stage(
            case,
            AgentStage.GAP_DETECTION,
            "Documentation readiness",
            lambda: self._compute_readiness_checked(case, label),
            detail_on_complete=lambda r: (
                f"Readiness {r.score}/100 ({label}); documentation "
                "completeness only — not an approval prediction"
            ),
        )
        case.readiness_history.append(readiness)

    # Stage bodies with their programmatic gates, so a gate violation surfaces
    # as a failed event on the timeline before the operation rolls back.

    def _parse_policy_checked(
        self, case: AuthLensCase, policy_text: str
    ) -> list[PolicyCriterion]:
        criteria = self._policy_parser.parse(case.policy, policy_text)
        gates.check_criteria(case, criteria)
        return criteria

    def _review_disclosure_checked(self, case: AuthLensCase):
        decisions = self._disclosure_filter.review(case)
        gates.check_disclosure_decisions(case, decisions)
        return decisions

    def _generate_packet_checked(self, case: AuthLensCase):
        packet = self._packet_generator.generate(case)
        gates.check_packet(case, packet)
        return packet

    def _verify_checked(self, case: AuthLensCase, packet):
        result = self._packet_verifier.verify(packet, case)
        gates.check_verification(case, packet, result)
        return result

    def _compute_readiness_checked(self, case: AuthLensCase, label: str):
        readiness = self._gap_detector.compute_readiness(case.assessments, label)
        gates.check_readiness(case, readiness, len(case.assessments))
        return readiness

    @staticmethod
    def _assessment_summary(assessments: list[CriterionAssessment]) -> str:
        counts: dict[str, int] = {}
        for assessment in assessments:
            counts[assessment.status.value] = counts.get(assessment.status.value, 0) + 1
        summary = ", ".join(f"{v} {k}" for k, v in sorted(counts.items()))
        return f"Assessed {len(assessments)} criteria: {summary}"

    @staticmethod
    def _before_after_summary(
        before: dict[str, str], reassessed: list[CriterionAssessment]
    ) -> str:
        changes = ", ".join(
            f"{a.criterion_id}: {before.get(a.criterion_id, 'unassessed')} → "
            f"{a.status.value}"
            for a in reassessed
        )
        return f"Re-evaluated affected criteria — {changes}"
