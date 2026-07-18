"""Independent packet verifier (implements the PacketVerifier port).

Checks every PacketClaim against the case's cited evidence, the parsed
policy, and the disclosure decisions. Implemented independently of the
packet generator: it trusts nothing in the packet and re-derives every
index it needs from the case. ``passed`` is True only with zero BLOCKING
issues.

Checks:

1.  Every clinical claim cites at least one evidence id.
2.  Every cited evidence id resolves to a known EvidenceItem for that
    claim's criterion.
3.  Every evidence excerpt is a verbatim quote of its source content.
4.  Claims do not overstate evidence: a referral is never presented as
    completed therapy; a prescription is never presented as treatment
    failure.
5.  Every applicable policy criterion is represented by at least one claim.
6.  Policy claims match the parsed criteria — no invented requirements.
7.  Conflicting assessments remain visible in the packet text.
8.  No content from an EXCLUDE disclosure decision appears in the packet.
9.  No approval-guarantee language appears.
10. The packet ends with the fixed human-review sentence.

Issue descriptions for purely presentational problems are prefixed with
"Formatting:" or "Citation placement:" — the only categories the safe
reviser may act on (see revision.py).
"""

import re
from datetime import datetime, timezone

from app.contracts import (
    AuthLensCase,
    ClaimType,
    CriterionStatus,
    DisclosureDecisionType,
    EvidenceItem,
    PacketClaim,
    PriorAuthorizationPacket,
    SourceType,
    VerificationIssue,
    VerificationResult,
    VerificationSeverity,
)
from app.services.disclosure.sources import resolve_sources
from app.services.packet.builder import HUMAN_REVIEW_SENTENCE

# Sources that genuinely document that something happened. FHIR referral /
# medication entries are orders, not outcomes, and never make this list.
_DOCUMENTING_SOURCE_TYPES = frozenset(
    {
        SourceType.ENCOUNTER_NOTE,
        SourceType.ENCOUNTER_TRANSCRIPT,
        SourceType.CLINICIAN_CLARIFICATION,
    }
)

_COMPLETION_WORDS = ("completed", "finished", "underwent", "attended", "adhered")
_FAILURE_WORDS = (
    "failed",
    "failure",
    "did not respond",
    "without improvement",
    "without sufficient improvement",
    "unsuccessful",
    "refractory",
    "not improved",
)
_THERAPY_WORDS = ("therapy", "conservative", "treatment", "medication", "regimen", "course")

# Negated approval idioms are removed before scanning for guarantees so
# "not a guarantee of approval" never trips the check.
_NEGATED_APPROVAL_IDIOMS = (
    "not a guarantee of approval",
    "no guarantee of approval",
    "does not guarantee approval",
    "cannot guarantee approval",
    "is not a prediction of payer approval",
    "not a prediction of approval",
)
_APPROVAL_GUARANTEE_PATTERNS = (
    "guarantee approval",
    "guarantees approval",
    "guaranteed approval",
    "approval is guaranteed",
    "will be approved",
    "will approve",
    "assures approval",
    "assured approval",
    "ensure approval",
    "ensures approval",
    "certain to be approved",
    "approval is certain",
)

_WORD_RE = re.compile(r"[a-z0-9']+")
_STOPWORDS = frozenset(
    "the a an and or of to for with within in on at by is are was were be been has have "
    "had must may can shall requires required require that this these those as from".split()
)


def _content_words(text: str) -> set[str]:
    return {
        w for w in _WORD_RE.findall(text.lower()) if len(w) > 3 and w not in _STOPWORDS
    }


class IndependentPacketVerifier:
    """Deterministic, generator-independent claim-by-claim verification."""

    def verify(
        self, packet: PriorAuthorizationPacket, case: AuthLensCase
    ) -> VerificationResult:
        issues: list[VerificationIssue] = []
        counter = [0]

        def add(
            severity: VerificationSeverity,
            description: str,
            claim_id: str | None = None,
            resolution: str | None = None,
        ) -> None:
            counter[0] += 1
            issues.append(
                VerificationIssue(
                    issue_id=f"vi-{counter[0]:03d}",
                    severity=severity,
                    claim_id=claim_id,
                    description=description,
                    suggested_resolution=resolution,
                )
            )

        sources = resolve_sources(case)
        evidence_by_criterion: dict[str, dict[str, EvidenceItem]] = {}
        for assessment in case.assessments:
            evidence_by_criterion[assessment.criterion_id] = {
                e.evidence_id: e for e in assessment.evidence
            }
        all_evidence = {
            eid: ev
            for per_criterion in evidence_by_criterion.values()
            for eid, ev in per_criterion.items()
        }
        criteria = {c.criterion_id: c for c in case.criteria}
        assessments = {a.criterion_id: a for a in case.assessments}
        packet_text = "\n".join(
            [s.title + "\n" + s.body for s in packet.sections]
            + [c.text for c in packet.claims]
        )
        packet_text_lower = packet_text.lower()

        if packet.case_id != case.case_id:
            add(
                VerificationSeverity.BLOCKING,
                f"Packet {packet.packet_id} belongs to case {packet.case_id}, "
                f"not {case.case_id}.",
            )

        for claim in packet.claims:
            self._check_claim(claim, case, all_evidence, evidence_by_criterion,
                              criteria, sources, add)

        self._check_coverage(packet, criteria, assessments, add)
        self._check_conflicts_visible(packet, assessments, criteria, add)
        self._check_exclusions(packet, case, sources, packet_text_lower, add)
        self._check_no_approval_guarantee(packet_text_lower, add)
        self._check_human_review(packet, add)
        self._check_section_references(packet, add)

        passed = not any(
            i.severity is VerificationSeverity.BLOCKING for i in issues
        )
        return VerificationResult(
            verification_id=f"ver-{packet.packet_id}",
            packet_id=packet.packet_id,
            passed=passed,
            checked_claim_count=len(packet.claims),
            issues=issues,
            verified_at=datetime.now(timezone.utc),
        )

    # --- per-claim checks -------------------------------------------------

    def _check_claim(
        self, claim, case, all_evidence, evidence_by_criterion, criteria, sources, add
    ) -> None:
        if claim.claim_type is ClaimType.POLICY:
            self._check_policy_claim(claim, criteria, add)
            return

        if not claim.evidence_ids:
            add(
                VerificationSeverity.BLOCKING,
                f"Clinical claim {claim.claim_id} cites no evidence; every "
                "clinical claim must be source-grounded.",
                claim.claim_id,
                "Remove the claim or map it to cited evidence via re-assessment.",
            )
            return

        criterion_evidence = evidence_by_criterion.get(claim.criterion_id or "", {})
        cited: list[EvidenceItem] = []
        for evidence_id in claim.evidence_ids:
            evidence = all_evidence.get(evidence_id)
            if evidence is None:
                add(
                    VerificationSeverity.BLOCKING,
                    f"Claim {claim.claim_id} cites unknown evidence id "
                    f"{evidence_id}; the citation does not resolve.",
                    claim.claim_id,
                    "Remove the invalid citation or regenerate the packet.",
                )
                continue
            if evidence_id not in criterion_evidence:
                add(
                    VerificationSeverity.BLOCKING,
                    f"Claim {claim.claim_id} cites evidence {evidence_id}, which "
                    f"was mapped to a different criterion than {claim.criterion_id}; "
                    "the cited source does not support this claim.",
                    claim.claim_id,
                    "Cite evidence mapped to the claim's own criterion.",
                )
                continue
            cited.append(evidence)
            self._check_verbatim(claim, evidence, sources, add)

        if cited:
            self._check_overstatement(claim, cited, sources, add)

    def _check_verbatim(self, claim, evidence, sources, add) -> None:
        source = sources.get(evidence.source_id)
        if source is None:
            add(
                VerificationSeverity.BLOCKING,
                f"Evidence {evidence.evidence_id} (claim {claim.claim_id}) cites "
                f"unknown source {evidence.source_id}.",
                claim.claim_id,
            )
            return
        if evidence.excerpt not in source.content:
            add(
                VerificationSeverity.BLOCKING,
                f"Evidence {evidence.evidence_id} (claim {claim.claim_id}) is not "
                f"a verbatim quote of source {evidence.source_id}; excerpts must "
                "match the source exactly.",
                claim.claim_id,
                "Re-extract the excerpt verbatim from the source.",
            )

    def _check_overstatement(self, claim, cited, sources, add) -> None:
        """Referral is not completion; prescription is not failure."""
        text = claim.text.lower()
        if not any(w in text for w in _THERAPY_WORDS):
            return
        asserts_completion = any(w in text for w in _COMPLETION_WORDS)
        asserts_failure = any(w in text for w in _FAILURE_WORDS)
        if not (asserts_completion or asserts_failure):
            return
        if any(e.source_type in _DOCUMENTING_SOURCE_TYPES for e in cited):
            return

        categories = {
            (sources.get(e.source_id).chart_category if sources.get(e.source_id) else None)
            for e in cited
        }
        if asserts_completion and {"referral", "service_request"} & categories:
            add(
                VerificationSeverity.BLOCKING,
                f"Claim {claim.claim_id} presents completed therapy but cites "
                "only a referral/order; a referral is never proof of completed "
                "therapy (safety rule #5).",
                claim.claim_id,
                "Obtain a clinician clarification documenting completion, or "
                "soften the claim to what the referral shows.",
            )
        if asserts_failure and "medication" in categories:
            add(
                VerificationSeverity.BLOCKING,
                f"Claim {claim.claim_id} presents treatment failure but cites "
                "only a prescription; a prescription is never proof of "
                "treatment failure (safety rule #6).",
                claim.claim_id,
                "Obtain documentation of the treatment outcome, or soften the "
                "claim to what the prescription shows.",
            )
        if (asserts_completion or asserts_failure) and not (
            {"referral", "service_request", "medication"} & categories
        ):
            add(
                VerificationSeverity.BLOCKING,
                f"Claim {claim.claim_id} asserts a treatment outcome without any "
                "documenting source (note, transcript, or clinician clarification).",
                claim.claim_id,
            )

    def _check_policy_claim(self, claim, criteria, add) -> None:
        criterion = criteria.get(claim.criterion_id or "")
        if criterion is None:
            add(
                VerificationSeverity.BLOCKING,
                f"Policy claim {claim.claim_id} references criterion "
                f"{claim.criterion_id!r}, which does not exist in the parsed "
                "policy; no policy requirement may be invented.",
                claim.claim_id,
                "Remove the claim; only parsed criteria may be restated.",
            )
            return
        reference = _content_words(
            f"{criterion.requirement} {criterion.label} {criterion.policy_id} "
            f"{criterion.criterion_id}"
        )
        stated = _content_words(claim.text)
        overlap = len(stated & reference) / len(stated) if stated else 0.0
        if overlap < 0.5:
            add(
                VerificationSeverity.BLOCKING,
                f"Policy claim {claim.claim_id} does not match the parsed text of "
                f"criterion {criterion.criterion_id}; requirements must be "
                "restated from the policy, not invented.",
                claim.claim_id,
                "Restate the criterion requirement verbatim.",
            )

    # --- packet-level checks ----------------------------------------------

    def _check_coverage(self, packet, criteria, assessments, add) -> None:
        represented = {c.criterion_id for c in packet.claims if c.criterion_id}
        for criterion_id, criterion in criteria.items():
            assessment = assessments.get(criterion_id)
            if assessment is not None and assessment.status is CriterionStatus.NOT_APPLICABLE:
                continue
            if criterion_id not in represented:
                add(
                    VerificationSeverity.BLOCKING,
                    f"Required criterion {criterion_id} ({criterion.label}) is not "
                    "represented by any packet claim.",
                    None,
                    "Regenerate the packet so every applicable criterion appears.",
                )

    def _check_conflicts_visible(self, packet, assessments, criteria, add) -> None:
        bodies_lower = [s.body.lower() for s in packet.sections]
        for criterion_id, assessment in assessments.items():
            if assessment.status is not CriterionStatus.CONFLICTING:
                continue
            visible = any(
                criterion_id.lower() in body and "conflict" in body
                for body in bodies_lower
            )
            if not visible:
                label = criteria[criterion_id].label if criterion_id in criteria else ""
                add(
                    VerificationSeverity.BLOCKING,
                    f"Criterion {criterion_id} ({label}) has conflicting evidence "
                    "but the conflict is not visible anywhere in the packet; "
                    "conflicts must remain visible to the reviewer.",
                    None,
                    "Restore the conflict to the Remaining gaps section.",
                )

    def _check_exclusions(self, packet, case, sources, packet_text_lower, add) -> None:
        excluded = [
            d
            for d in case.disclosure_decisions
            if d.decision is DisclosureDecisionType.EXCLUDE
        ]
        cited_source_ids = set()
        all_evidence = {
            e.evidence_id: e for a in case.assessments for e in a.evidence
        }
        for claim in packet.claims:
            for evidence_id in claim.evidence_ids:
                evidence = all_evidence.get(evidence_id)
                if evidence is not None:
                    cited_source_ids.add(evidence.source_id)

        for decision in excluded:
            if decision.source_id in cited_source_ids:
                add(
                    VerificationSeverity.BLOCKING,
                    f"Packet cites source {decision.source_id}, which was "
                    "EXCLUDED by disclosure review; excluded content must not "
                    "appear in the packet.",
                    None,
                    "Regenerate the packet from INCLUDE'd content only.",
                )
            source = sources.get(decision.source_id)
            for needle in filter(None, (decision.item_description, source.content if source else None)):
                if len(needle) > 6 and needle.lower() in packet_text_lower:
                    add(
                        VerificationSeverity.BLOCKING,
                        f"Text of excluded item {decision.source_id} "
                        f"({decision.item_description}) appears in the packet; "
                        "unrelated patient information leaked into the output.",
                        None,
                        "Remove the excluded content and regenerate.",
                    )
                    break

    def _check_no_approval_guarantee(self, packet_text_lower, add) -> None:
        scrubbed = packet_text_lower
        for idiom in _NEGATED_APPROVAL_IDIOMS:
            scrubbed = scrubbed.replace(idiom, "")
        for pattern in _APPROVAL_GUARANTEE_PATTERNS:
            if pattern in scrubbed:
                add(
                    VerificationSeverity.BLOCKING,
                    f'Packet contains approval-guarantee language ("{pattern}"); '
                    "AuthLens never predicts or guarantees payer approval.",
                    None,
                    "Remove the guarantee language.",
                )

    def _check_human_review(self, packet, add) -> None:
        last_body = packet.sections[-1].body.rstrip() if packet.sections else ""
        if not last_body.endswith(HUMAN_REVIEW_SENTENCE):
            add(
                VerificationSeverity.BLOCKING,
                "Formatting: the packet must end with the fixed human-review "
                f'sentence "{HUMAN_REVIEW_SENTENCE}"; human review must be explicit.',
                None,
                "Append the fixed human-review sentence to the final section.",
            )

    def _check_section_references(self, packet, add) -> None:
        known = {c.claim_id for c in packet.claims}
        for section in packet.sections:
            for claim_id in section.claim_ids:
                if claim_id not in known:
                    add(
                        VerificationSeverity.WARNING,
                        f"Citation placement: section {section.section_id} "
                        f"references unknown claim {claim_id}.",
                        None,
                        "Remove the dangling claim reference.",
                    )
