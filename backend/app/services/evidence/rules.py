"""Deterministic clinical-documentation rules for evidence semantics.

Encodes the hard rules from docs/SAFETY_AND_HUMAN_REVIEW.md as code:

- A referral is never proof of completed therapy.
- A prescription is never proof of adherence or treatment failure.
- Completion of therapy is not automatically failure of therapy.
- A diagnosis code is not a physical-examination finding.
- Patient-reported statements must be labeled as patient-reported.

These signal detectors operate only on the supplied text; they never infer
facts that are not written down.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.contracts import EvidenceItem, SourceType

REFERRAL_PATTERN = re.compile(r"\breferr(?:al|als|ed|ing)\b|\brefer\b", re.IGNORECASE)

PRESCRIPTION_PATTERN = re.compile(
    r"\bprescri\w*\b|\b\d+\s?mg\b|\bmedication list\b|\bnsaid\b|\btwice daily\b|\bonce daily\b",
    re.IGNORECASE,
)

COMPLETION_PATTERN = re.compile(
    r"\bcomplet(?:ed|ion|ing)\b|\bfinished\b|\bunderwent\b|\battended\b", re.IGNORECASE
)

_FAILURE_PHRASES = (
    "without sufficient improvement",
    "without significant improvement",
    "without meaningful improvement",
    "without improvement",
    "no sufficient improvement",
    "no significant improvement",
    "no meaningful improvement",
    "no improvement",
    "not improved",
    "failed to improve",
    "minimal improvement",
    "no relief",
    "without relief",
)

_IMPROVEMENT_PATTERN = re.compile(
    r"\b(?:significant|substantial|marked|good|sufficient)\s+improvement\b"
    r"|\bimproved\s+(?:significantly|substantially|markedly)\b"
    r"|\bsymptoms\s+resolved\b",
    re.IGNORECASE,
)

ICD_CODE_PATTERN = re.compile(r"\b[A-Z]\d{2}(?:\.\d{1,4})?\b")

NEGATIVE_SCREEN_PATTERN = re.compile(
    r"\bdenies\b|\bdenied\b|\bno history of\b|\bnegative for\b|\bnone reported\b"
    r"|\bscreen(?:ed|ing)\b|\bwithout red[- ]flag\b",
    re.IGNORECASE,
)

_PATIENT_REPORTED_PATTERN = re.compile(
    r"\b(?:patient|she|he|they)\s+(?:reports?|states?|describes?|endorses?)\b",
    re.IGNORECASE,
)

REFERRAL_LIMITATION_NOTE = "A referral is not evidence that therapy was completed."
PRESCRIPTION_LIMITATION_NOTE = (
    "A listed prescription is not evidence that treatment was completed or failed."
)
PATIENT_REPORTED_NOTE = "Patient-reported statement."


@dataclass(frozen=True)
class TherapySignals:
    """What a piece of text documents about conservative therapy — no more."""

    referral: bool
    prescription: bool
    completion: bool
    failure: bool
    improvement: bool

    @property
    def completion_and_failure(self) -> bool:
        return self.completion and self.failure

    @property
    def referral_or_prescription_only(self) -> bool:
        return (self.referral or self.prescription) and not (self.completion or self.failure)


def therapy_signals(text: str) -> TherapySignals:
    lowered = text.lower()
    failure = any(phrase in lowered for phrase in _FAILURE_PHRASES)
    # A negated phrase like "no significant improvement" must never read as
    # improvement, so failure wins within one statement.
    improvement = bool(_IMPROVEMENT_PATTERN.search(text)) and not failure
    return TherapySignals(
        referral=bool(REFERRAL_PATTERN.search(text)),
        prescription=bool(PRESCRIPTION_PATTERN.search(text)),
        completion=bool(COMPLETION_PATTERN.search(text)),
        failure=failure,
        improvement=improvement,
    )


def contains_diagnosis_code(text: str) -> bool:
    return bool(ICD_CODE_PATTERN.search(text))


def documents_red_flag_screening(text: str) -> bool:
    return bool(NEGATIVE_SCREEN_PATTERN.search(text))


def is_patient_reported(
    excerpt: str, source_content: str | None = None, source_type: SourceType | None = None
) -> bool:
    """True when a statement is attributable to the patient, not the clinician.

    Detection is structural where possible: position inside the SUBJECTIVE
    section of a note, or inside a "Patient:" turn of a transcript. Falls
    back to explicit "patient reports"-style phrasing in the excerpt.
    """
    if source_type == SourceType.CLINICIAN_CLARIFICATION:
        return False
    if source_content:
        index = source_content.find(excerpt)
        if index >= 0:
            if _within_subjective_section(source_content, index):
                return True
            if _within_patient_turn(source_content, index):
                return True
    return bool(_PATIENT_REPORTED_PATTERN.search(excerpt))


def _within_subjective_section(content: str, index: int) -> bool:
    subjective = content.find("SUBJECTIVE:")
    if subjective < 0 or index < subjective:
        return False
    for header in ("OBJECTIVE:", "ASSESSMENT:", "PLAN:"):
        end = content.find(header, subjective)
        if end >= 0:
            return index < end
    return True


def _within_patient_turn(content: str, index: int) -> bool:
    patient = content.rfind("Patient:", 0, index)
    if patient < 0:
        return False
    clinician = content.rfind("Clinician:", 0, index)
    return patient > clinician


def evidence_text(item: EvidenceItem) -> str:
    """The text an EvidenceItem contributes to rule evaluation (excerpt only)."""
    return item.excerpt
