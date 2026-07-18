"""Evidence-grounded packet generator (implements the PacketGenerator port).

The packet is assembled deterministically from typed case artifacts:

- Clinical claims come from criterion assessments (their rationale is
  already required to be grounded in cited evidence) and carry the
  assessment's evidence ids, filtered to INCLUDE'd sources only.
- Policy claims restate parsed criteria verbatim — never new requirements.
- Section bodies are composed only from those claims, the case intake
  fields, and focused verbatim evidence excerpts with source labels.

The generator refuses to run before disclosure review, never quotes an
excluded source, never marks its own output verified, and always ends the
packet with the fixed human-review sentence.
"""

from datetime import datetime, timezone

from app.contracts import (
    AuthLensCase,
    ClaimType,
    CriterionStatus,
    DisclosureDecisionType,
    PacketClaim,
    PacketSection,
    PacketStatus,
    PriorAuthorizationPacket,
)
from app.services.disclosure.sources import resolve_sources

HUMAN_REVIEW_SENTENCE = "Requires clinician review before submission."

_ATTESTATION_PLACEHOLDER = (
    "Clinician attestation (placeholder — to be completed by the reviewing "
    "clinician): I have personally reviewed this draft, the cited evidence, "
    "and the remaining gaps, and I confirm the clinical statements are "
    "accurate. Signature: ______________  Date: __________. This draft is "
    "not a payer submission and is not a guarantee of approval."
)

_CLAIMABLE_STATUSES = frozenset(
    {CriterionStatus.MET, CriterionStatus.WEAK, CriterionStatus.CONFLICTING}
)


class PacketGenerationError(RuntimeError):
    """Raised when the packet cannot be generated safely."""


class EvidenceGroundedPacketGenerator:
    """Deterministic packet builder over INCLUDE'd, criterion-linked content."""

    def generate(self, case: AuthLensCase) -> PriorAuthorizationPacket:
        """Return a packet with status DRAFT. Never marks its own work verified."""
        if not case.disclosure_decisions:
            raise PacketGenerationError(
                "Disclosure review must complete before packet generation: "
                "no disclosure decisions are recorded on the case."
            )
        if not case.criteria or not case.assessments:
            raise PacketGenerationError(
                "Policy criteria and assessments are required to generate a packet."
            )

        included_ids = {
            d.source_id
            for d in case.disclosure_decisions
            if d.decision is DisclosureDecisionType.INCLUDE
        }
        sources = resolve_sources(case)
        assessments = {a.criterion_id: a for a in case.assessments}

        claims: list[PacketClaim] = []
        clinical_by_criterion: dict[str, list[PacketClaim]] = {}
        counter = 0

        for criterion in case.criteria:
            assessment = assessments.get(criterion.criterion_id)
            if assessment is None or assessment.status not in _CLAIMABLE_STATUSES:
                continue
            usable_evidence = [
                e for e in assessment.evidence if e.source_id in included_ids
            ]
            if not usable_evidence:
                continue
            counter += 1
            claim = PacketClaim(
                claim_id=f"clm-{counter:03d}",
                text=assessment.rationale,
                claim_type=ClaimType.CLINICAL,
                criterion_id=criterion.criterion_id,
                evidence_ids=[e.evidence_id for e in usable_evidence],
            )
            claims.append(claim)
            clinical_by_criterion.setdefault(criterion.criterion_id, []).append(claim)

        for criterion in case.criteria:
            counter += 1
            claims.append(
                PacketClaim(
                    claim_id=f"clm-{counter:03d}",
                    text=(
                        f"Policy {criterion.policy_id} criterion "
                        f'{criterion.criterion_id} ("{criterion.label}") requires: '
                        f"{criterion.requirement}"
                    ),
                    claim_type=ClaimType.POLICY,
                    criterion_id=criterion.criterion_id,
                    evidence_ids=[],
                )
            )

        sections = self._build_sections(
            case, claims, clinical_by_criterion, included_ids, sources
        )

        return PriorAuthorizationPacket(
            packet_id=f"pkt-{case.case_id}",
            case_id=case.case_id,
            status=PacketStatus.DRAFT,
            sections=sections,
            claims=claims,
            generated_at=datetime.now(timezone.utc),
        )

    def _build_sections(
        self,
        case: AuthLensCase,
        claims: list[PacketClaim],
        clinical_by_criterion: dict[str, list[PacketClaim]],
        included_ids: set[str],
        sources,
    ) -> list[PacketSection]:
        assessments = {a.criterion_id: a for a in case.assessments}
        evidence_index = {
            e.evidence_id: e for a in case.assessments for e in a.evidence
        }
        clinical_claims = [c for c in claims if c.claim_type is ClaimType.CLINICAL]

        patient_body = (
            f"{case.patient.display_name} (patient id {case.patient.patient_id}, "
            f"born {case.patient.birth_date}, sex {case.patient.sex}) — request for "
            f"{case.requested_service.service_name} "
            f"({case.requested_service.code_system} {case.requested_service.code}) "
            f"under policy {case.policy.policy_id} ({case.policy.payer_name}). "
            "All statements below are drawn from cited chart evidence approved "
            "for disclosure."
        )

        service_body = (
            f"{case.requested_service.service_name} — "
            f"{case.requested_service.code_system} {case.requested_service.code}."
        )
        if case.requested_service.modality:
            service_body += f" Modality: {case.requested_service.modality}."
        if case.requested_service.body_site:
            service_body += f" Body site: {case.requested_service.body_site}."

        codes = ", ".join(case.indication_codes) if case.indication_codes else "none recorded"
        indication_body = (
            f"{case.clinical_indication} (clinician-stated indication; "
            f"ICD-10 codes as provided by the clinician: {codes})."
        )

        narrative_body = (
            " ".join(c.text for c in clinical_claims)
            or "No evidence-backed clinical statements are available."
        )

        matrix_lines: list[str] = []
        for criterion in case.criteria:
            assessment = assessments.get(criterion.criterion_id)
            status = assessment.status.value if assessment else "not assessed"
            line = f"{criterion.criterion_id} — {criterion.label} [{status}]"
            quotes = []
            if assessment:
                for evidence in assessment.evidence:
                    if evidence.source_id not in included_ids:
                        continue
                    source = sources.get(evidence.source_id)
                    label = source.label if source else evidence.source_id
                    quotes.append(f'"{evidence.excerpt}" ({label})')
            if quotes:
                line += ": " + "; ".join(quotes)
            else:
                line += ": no disclosed evidence on file — see Remaining gaps."
            matrix_lines.append(line)

        citation_lines: list[str] = []
        for claim in clinical_claims:
            for evidence_id in claim.evidence_ids:
                evidence = evidence_index.get(evidence_id)
                if evidence is None:
                    continue
                location = (
                    f"chars {evidence.span.start}-{evidence.span.end}"
                    if evidence.span
                    else (evidence.fhir_path or "structured entry")
                )
                citation_lines.append(
                    f'{claim.claim_id} ← {evidence_id}: "{evidence.excerpt}" '
                    f"— source {evidence.source_id} ({evidence.source_type.value}, {location})"
                )
        citations_body = "\n".join(citation_lines) or "No citations recorded."

        gap_lines: list[str] = []
        for criterion in case.criteria:
            assessment = assessments.get(criterion.criterion_id)
            if assessment is None:
                gap_lines.append(
                    f"{criterion.criterion_id} ({criterion.label}): not assessed."
                )
                continue
            if assessment.status is CriterionStatus.MISSING:
                gap_lines.append(
                    f"{criterion.criterion_id} ({criterion.label}): documentation "
                    "missing — clarification required before this criterion can be supported."
                )
            elif assessment.status is CriterionStatus.WEAK:
                gap_lines.append(
                    f"{criterion.criterion_id} ({criterion.label}): support is weak — "
                    "additional documentation is recommended."
                )
            elif assessment.status is CriterionStatus.CONFLICTING:
                gap_lines.append(
                    f"{criterion.criterion_id} ({criterion.label}): conflicting "
                    "evidence remains on file and must be resolved by the clinician; "
                    "the conflict is intentionally left visible in this packet."
                )
        gaps_body = (
            "\n".join(gap_lines)
            if gap_lines
            else "No outstanding documentation gaps identified."
        )

        included_count = sum(
            1
            for d in case.disclosure_decisions
            if d.decision is DisclosureDecisionType.INCLUDE
        )
        excluded_count = len(case.disclosure_decisions) - included_count
        flagged_count = sum(
            1 for d in case.disclosure_decisions if d.phi_category is not None
        )
        disclosure_body = (
            f"Minimum-necessary review recorded {len(case.disclosure_decisions)} "
            f"decisions: {included_count} item(s) included as necessary for the "
            f"policy criteria, {excluded_count} item(s) excluded as unrelated to "
            "this request. Excluded items are withheld from this packet and "
            "listed only in the case's disclosure review. "
            f"{flagged_count} item(s) carry a sensitive-category flag for "
            "clinician review of the disclosure decision."
        )

        review_body = (
            "WARNING — human review required. This packet is a machine-generated "
            "draft assembled from cited chart evidence. It has not been sent to "
            "any payer and cannot be sent by this system; documentation "
            "readiness is not a prediction of payer approval. A clinician must "
            "review every statement, resolve the remaining gaps, and complete "
            f"the attestation. {HUMAN_REVIEW_SENTENCE}"
        )

        all_claim_ids = [c.claim_id for c in claims]
        clinical_claim_ids = [c.claim_id for c in clinical_claims]
        return [
            PacketSection(
                section_id="sec-patient",
                title="Patient and request summary",
                body=patient_body,
                claim_ids=[],
            ),
            PacketSection(
                section_id="sec-service",
                title="Requested service",
                body=service_body,
                claim_ids=[],
            ),
            PacketSection(
                section_id="sec-indication",
                title="Clinical indication",
                body=indication_body,
                claim_ids=[],
            ),
            PacketSection(
                section_id="sec-necessity",
                title="Medical-necessity narrative",
                body=narrative_body,
                claim_ids=clinical_claim_ids,
            ),
            PacketSection(
                section_id="sec-matrix",
                title="Criterion-by-criterion evidence",
                body="\n".join(matrix_lines),
                claim_ids=all_claim_ids,
            ),
            PacketSection(
                section_id="sec-citations",
                title="Citations",
                body=citations_body,
                claim_ids=clinical_claim_ids,
            ),
            PacketSection(
                section_id="sec-gaps",
                title="Remaining gaps",
                body=gaps_body,
                claim_ids=[],
            ),
            PacketSection(
                section_id="sec-disclosure",
                title="Disclosure summary",
                body=disclosure_body,
                claim_ids=[],
            ),
            PacketSection(
                section_id="sec-attestation",
                title="Clinician attestation",
                body=_ATTESTATION_PLACEHOLDER,
                claim_ids=[],
            ),
            PacketSection(
                section_id="sec-review",
                title="Human review",
                body=review_body,
                claim_ids=[],
            ),
        ]
