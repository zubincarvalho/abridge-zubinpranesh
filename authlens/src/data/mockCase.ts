// Types mirroring Python Pydantic contracts (contracts/contracts.py)

export type CriterionStatus = "met" | "weak" | "missing" | "conflicting" | "not_applicable";
export type DenialRisk = "low" | "medium" | "high";
export type SourceType =
  | "encounter_note"
  | "encounter_transcript"
  | "fhir_resource"
  | "clinician_clarification"
  | "payer_policy";
export type EvidenceConfidence = "high" | "moderate" | "low";
export type CaseStatus =
  | "draft"
  | "intake_ready"
  | "analyzing"
  | "awaiting_clarification"
  | "reanalyzing"
  | "packet_drafted"
  | "verification_failed"
  | "verified"
  | "ready_for_review";

export type AgentStage =
  | "intake"
  | "policy_parsing"
  | "evidence_retrieval"
  | "evidence_mapping"
  | "gap_detection"
  | "clarification"
  | "disclosure_review"
  | "packet_generation"
  | "verification"
  | "form_drafting"
  | "human_review";

export type EventStatus = "started" | "completed" | "failed" | "skipped";

export type TextSpan = { start: number; end: number };

export type EvidenceItem = {
  evidence_id: string;
  source_id: string;
  source_type: SourceType;
  excerpt: string;
  span: TextSpan | null;
  fhir_path: string | null;
  confidence: EvidenceConfidence;
  note: string | null;
};

export type PolicyCriterion = {
  criterion_id: string;
  policy_id: string;
  label: string;
  requirement: string;
  category: string;
};

export type CriterionAssessment = {
  criterion_id: string;
  status: CriterionStatus;
  status_after: CriterionStatus;
  denial_risk: DenialRisk;
  rationale: string;
  evidence: EvidenceItem[];
  evidence_after: EvidenceItem[];
  clarification_question_id: string | null;
};

export type ClarificationQuestion = {
  question_id: string;
  criterion_ids: string[];
  question: string;
  why_needed: string;
  suggested_action: string;
  status: "open" | "answered";
};

export type ClinicianClarification = {
  clarification_id: string;
  question_id: string;
  response: string;
  recorded_at: string;
};

export type ReadinessSummary = {
  label: string;
  score: number;
  criteria_met: number;
  criteria_weak: number;
  criteria_missing: number;
  criteria_conflicting: number;
  criteria_not_applicable: number;
  overall_denial_risk: DenialRisk;
};

export type DisclosureDecisionRecord = {
  decision_id: string;
  source_id: string;
  item_description: string;
  decision: "include" | "exclude";
  reason: string;
  phi_category: string | null;
};

export type AgentEvent = {
  event_id: string;
  sequence: number;
  stage: AgentStage;
  status: EventStatus;
  title: string;
  detail: string | null;
  related_ids: string[];
  occurred_at: string;
};

export type ChartItem = {
  source_id: string;
  category: string;
  display: string;
  detail: string | null;
};

export type SourceContent = {
  source_id: string;
  title: string;
  content: string;
  source_type: SourceType | "clarification";
};

export type NoteHighlight = {
  id: string;
  start: number;
  end: number;
  criterionId: string;
  sourceId: string;
  label: string;
};

export type FormField = {
  field_id: string;
  label: string;
  value: string;
  source_claim_ids: string[];
};

// ── Raw source texts (character spans reference these strings) ─────────────

export const NOTE_TEXT =
  "SUBJECTIVE: Jordan Rivera is a 47-year-old presenting with low back pain radiating down the left leg, ongoing for approximately 8 weeks. Pain is worse with prolonged sitting and bending. She reports difficulty sitting through a full workday and interrupted sleep due to pain. She denies recent trauma, fever, unexplained weight loss, saddle anesthesia, and bowel or bladder dysfunction. No history of cancer.\n\nOBJECTIVE: Straight-leg raise is positive on the left at 40 degrees. Sensation decreased over the left lateral calf. Strength 5/5 throughout. Reflexes symmetric.\n\nASSESSMENT: Suspected lumbar radiculopathy (M54.16).\n\nPLAN: Naproxen 500 mg twice daily is listed on the medication list. Referral to physical therapy is in place. MRI lumbar spine without contrast ordered to evaluate for nerve root compression and to assess candidacy for epidural steroid injection or surgical referral if conservative measures fail. Return in 4 weeks or sooner if red-flag symptoms develop.";

export const TRANSCRIPT_TEXT =
  "Clinician: How long has the pain been going on now? Patient: It’s been about two months, and it shoots down my left leg. Clinician: Any numbness around the groin, trouble with bladder or bowels, fevers, weight loss? Patient: No, nothing like that. Clinician: Okay. Let’s get an MRI of your lower back to see what’s going on with that nerve.";

export const CLARIFICATION_RESPONSE =
  "Yes. The patient completed 8 weeks of physical therapy alongside scheduled naproxen and a home-exercise program, without sufficient improvement in pain or function.";

// ── Note highlights (sorted by start; all reference NOTE_TEXT offsets) ─────

export const NOTE_HIGHLIGHTS: NoteHighlight[] = [
  {
    id: "hl-lm2",
    start: 102,
    end: 135,
    criterionId: "LM-2",
    sourceId: "note-001",
    label: "LM-2: Symptom duration ≥ 6 weeks",
  },
  {
    id: "hl-lm6",
    start: 199,
    end: 274,
    criterionId: "LM-6",
    sourceId: "note-001",
    label: "LM-6: Functional limitation",
  },
  {
    id: "hl-lm5",
    start: 276,
    end: 408,
    criterionId: "LM-5",
    sourceId: "note-001",
    label: "LM-5: Red-flag screening",
  },
  {
    id: "hl-lm4-slr",
    start: 421,
    end: 477,
    criterionId: "LM-4",
    sourceId: "note-001",
    label: "LM-4: Positive straight-leg raise",
  },
  {
    id: "hl-lm4-sens",
    start: 479,
    end: 525,
    criterionId: "LM-4",
    sourceId: "note-001",
    label: "LM-4: Decreased sensation",
  },
  {
    id: "hl-lm1",
    start: 585,
    end: 624,
    criterionId: "LM-1",
    sourceId: "note-001",
    label: "LM-1: Diagnosis / indication",
  },
  {
    id: "hl-lm7",
    start: 737,
    end: 923,
    criterionId: "LM-7",
    sourceId: "note-001",
    label: "LM-7: Clinical rationale for MRI",
  },
];

// ── Policy criteria (LM-1 … LM-7, policy MHP-IMG-2201) ──────────────────────

export const POLICY_CRITERIA: PolicyCriterion[] = [
  {
    criterion_id: "LM-1",
    policy_id: "MHP-IMG-2201",
    label: "Appropriate diagnosis or indication",
    requirement:
      "The record documents a clinical indication appropriate for lumbar spine MRI, such as suspected lumbar radiculopathy, with a corresponding diagnosis code.",
    category: "indication",
  },
  {
    criterion_id: "LM-2",
    policy_id: "MHP-IMG-2201",
    label: "Symptom duration of at least six weeks",
    requirement:
      "Symptoms (low back pain and/or radicular symptoms) have persisted for at least six (6) weeks, with the duration explicitly documented.",
    category: "duration",
  },
  {
    criterion_id: "LM-3",
    policy_id: "MHP-IMG-2201",
    label: "Completed and failed conservative treatment",
    requirement:
      "The patient has completed at least six (6) weeks of conservative treatment — such as physical therapy, anti-inflammatory medication, and/or a structured home-exercise program — without sufficient improvement. A referral to therapy or a prescription alone does not satisfy this criterion; completion and failure must both be documented.",
    category: "conservative_therapy",
  },
  {
    criterion_id: "LM-4",
    policy_id: "MHP-IMG-2201",
    label: "Relevant neurologic or examination findings",
    requirement:
      "The record documents neurologic or physical-examination findings consistent with the indication (e.g., positive straight-leg raise, dermatomal sensory change, motor weakness, or reflex asymmetry).",
    category: "exam_findings",
  },
  {
    criterion_id: "LM-5",
    policy_id: "MHP-IMG-2201",
    label: "Red-flag screening",
    requirement:
      "The record documents screening for red-flag conditions (e.g., trauma, cancer history, unexplained weight loss, fever, saddle anesthesia, bowel or bladder dysfunction), with findings noted as present or absent.",
    category: "red_flags",
  },
  {
    criterion_id: "LM-6",
    policy_id: "MHP-IMG-2201",
    label: "Functional limitation",
    requirement:
      "The record documents a functional limitation attributable to the symptoms (e.g., limitation of work, activities of daily living, or sleep).",
    category: "functional_limitation",
  },
  {
    criterion_id: "LM-7",
    policy_id: "MHP-IMG-2201",
    label: "Clinical rationale for MRI",
    requirement:
      "The record documents why MRI results are expected to change management (e.g., evaluation for surgical or interventional candidacy).",
    category: "rationale",
  },
];

// ── Criterion assessments ──────────────────────────────────────────────────
// status = awaiting_clarification state; status_after = ready_for_review state

export const ASSESSMENTS: CriterionAssessment[] = [
  {
    criterion_id: "LM-1",
    status: "met",
    status_after: "met",
    denial_risk: "low",
    rationale:
      "The note and problem list document suspected lumbar radiculopathy with ICD-10 M54.16, an appropriate indication for lumbar MRI.",
    evidence: [
      {
        evidence_id: "ev-lm1-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "Suspected lumbar radiculopathy (M54.16)",
        span: { start: 585, end: 624 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
      {
        evidence_id: "ev-lm1-fhir",
        source_id: "fhir-cond-001",
        source_type: "fhir_resource",
        excerpt: "Chronic low back pain with radiation to left leg",
        span: null,
        fhir_path: "Bundle.entry[fhir-cond-001].display",
        confidence: "high",
        note: null,
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm1-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "Suspected lumbar radiculopathy (M54.16)",
        span: { start: 585, end: 624 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
      {
        evidence_id: "ev-lm1-fhir",
        source_id: "fhir-cond-001",
        source_type: "fhir_resource",
        excerpt: "Chronic low back pain with radiation to left leg",
        span: null,
        fhir_path: "Bundle.entry[fhir-cond-001].display",
        confidence: "high",
        note: null,
      },
    ],
    clarification_question_id: null,
  },
  {
    criterion_id: "LM-2",
    status: "met",
    status_after: "met",
    denial_risk: "low",
    rationale:
      "Duration is explicitly documented as approximately 8 weeks in the note and about two months in the transcript, exceeding the six-week requirement.",
    evidence: [
      {
        evidence_id: "ev-lm2-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "ongoing for approximately 8 weeks",
        span: { start: 102, end: 135 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
      {
        evidence_id: "ev-lm2-tx",
        source_id: "transcript-001",
        source_type: "encounter_transcript",
        excerpt: "It’s been about two months",
        span: { start: 61, end: 87 },
        fhir_path: null,
        confidence: "moderate",
        note: null,
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm2-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "ongoing for approximately 8 weeks",
        span: { start: 102, end: 135 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
      {
        evidence_id: "ev-lm2-tx",
        source_id: "transcript-001",
        source_type: "encounter_transcript",
        excerpt: "It’s been about two months",
        span: { start: 61, end: 87 },
        fhir_path: null,
        confidence: "moderate",
        note: null,
      },
    ],
    clarification_question_id: null,
  },
  {
    criterion_id: "LM-3",
    status: "missing",
    status_after: "met",
    denial_risk: "high",
    rationale:
      "The record shows an NSAID on the medication list and a physical-therapy referral, but neither establishes that six weeks of conservative treatment were completed without sufficient improvement.",
    evidence: [
      {
        evidence_id: "ev-lm3-med",
        source_id: "fhir-med-001",
        source_type: "fhir_resource",
        excerpt: "Naproxen 500 mg twice daily (NSAID)",
        span: null,
        fhir_path: "MedicationRequest.medicationCodeableConcept.text",
        confidence: "low",
        note: "A listed prescription is not evidence that treatment was completed or failed.",
      },
      {
        evidence_id: "ev-lm3-ref",
        source_id: "fhir-ref-pt-001",
        source_type: "fhir_resource",
        excerpt: "Referral to physical therapy",
        span: null,
        fhir_path: "ServiceRequest.code.text",
        confidence: "low",
        note: "A referral is not evidence that therapy was completed.",
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm3-clar",
        source_id: "clar-001",
        source_type: "clinician_clarification",
        excerpt:
          "Yes. The patient completed 8 weeks of physical therapy alongside scheduled naproxen and a home-exercise program, without sufficient improvement in pain or function.",
        span: { start: 0, end: 164 },
        fhir_path: null,
        confidence: "high",
        note: "Clinician attestation recorded verbatim at point of capture.",
      },
      {
        evidence_id: "ev-lm3-med",
        source_id: "fhir-med-001",
        source_type: "fhir_resource",
        excerpt: "Naproxen 500 mg twice daily (NSAID)",
        span: null,
        fhir_path: "MedicationRequest.medicationCodeableConcept.text",
        confidence: "low",
        note: "A listed prescription is not evidence that treatment was completed or failed.",
      },
      {
        evidence_id: "ev-lm3-ref",
        source_id: "fhir-ref-pt-001",
        source_type: "fhir_resource",
        excerpt: "Referral to physical therapy",
        span: null,
        fhir_path: "ServiceRequest.code.text",
        confidence: "low",
        note: "A referral is not evidence that therapy was completed.",
      },
    ],
    clarification_question_id: "q-lm3-001",
  },
  {
    criterion_id: "LM-4",
    status: "met",
    status_after: "met",
    denial_risk: "low",
    rationale:
      "Positive left straight-leg raise at 40 degrees and decreased sensation over the left lateral calf are documented examination findings consistent with the indication.",
    evidence: [
      {
        evidence_id: "ev-lm4-slr",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "Straight-leg raise is positive on the left at 40 degrees",
        span: { start: 421, end: 477 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
      {
        evidence_id: "ev-lm4-sens",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "Sensation decreased over the left lateral calf",
        span: { start: 479, end: 525 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm4-slr",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "Straight-leg raise is positive on the left at 40 degrees",
        span: { start: 421, end: 477 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
      {
        evidence_id: "ev-lm4-sens",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "Sensation decreased over the left lateral calf",
        span: { start: 479, end: 525 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
    ],
    clarification_question_id: null,
  },
  {
    criterion_id: "LM-5",
    status: "met",
    status_after: "met",
    denial_risk: "low",
    rationale:
      "The note documents explicit negative screening for trauma, fever, weight loss, saddle anesthesia, bowel/bladder dysfunction, and cancer history.",
    evidence: [
      {
        evidence_id: "ev-lm5-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt:
          "She denies recent trauma, fever, unexplained weight loss, saddle anesthesia, and bowel or bladder dysfunction. No history of cancer.",
        span: { start: 276, end: 408 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm5-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt:
          "She denies recent trauma, fever, unexplained weight loss, saddle anesthesia, and bowel or bladder dysfunction. No history of cancer.",
        span: { start: 276, end: 408 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
    ],
    clarification_question_id: null,
  },
  {
    criterion_id: "LM-6",
    status: "weak",
    status_after: "weak",
    denial_risk: "medium",
    rationale:
      "Work and sleep impact are mentioned, but the limitation is not characterized in enough detail (frequency, severity) to fully satisfy the criterion.",
    evidence: [
      {
        evidence_id: "ev-lm6-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "difficulty sitting through a full workday and interrupted sleep due to pain",
        span: { start: 199, end: 274 },
        fhir_path: null,
        confidence: "moderate",
        note: null,
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm6-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt: "difficulty sitting through a full workday and interrupted sleep due to pain",
        span: { start: 199, end: 274 },
        fhir_path: null,
        confidence: "moderate",
        note: null,
      },
    ],
    clarification_question_id: null,
  },
  {
    criterion_id: "LM-7",
    status: "met",
    status_after: "met",
    denial_risk: "low",
    rationale:
      "The plan documents that MRI results will guide evaluation for epidural steroid injection or surgical referral, i.e., results are expected to change management.",
    evidence: [
      {
        evidence_id: "ev-lm7-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt:
          "MRI lumbar spine without contrast ordered to evaluate for nerve root compression and to assess candidacy for epidural steroid injection or surgical referral if conservative measures fail",
        span: { start: 737, end: 923 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
    ],
    evidence_after: [
      {
        evidence_id: "ev-lm7-note",
        source_id: "note-001",
        source_type: "encounter_note",
        excerpt:
          "MRI lumbar spine without contrast ordered to evaluate for nerve root compression and to assess candidacy for epidural steroid injection or surgical referral if conservative measures fail",
        span: { start: 737, end: 923 },
        fhir_path: null,
        confidence: "high",
        note: null,
      },
    ],
    clarification_question_id: null,
  },
];

// ── Readiness summaries ────────────────────────────────────────────────────

export const READINESS_INITIAL: ReadinessSummary = {
  label: "initial",
  score: 79,
  criteria_met: 5,
  criteria_weak: 1,
  criteria_missing: 1,
  criteria_conflicting: 0,
  criteria_not_applicable: 0,
  overall_denial_risk: "high",
};

export const READINESS_POST_CLARIFICATION: ReadinessSummary = {
  label: "post_clarification",
  score: 93,
  criteria_met: 6,
  criteria_weak: 1,
  criteria_missing: 0,
  criteria_conflicting: 0,
  criteria_not_applicable: 0,
  overall_denial_risk: "medium",
};

// ── Clarification Q&A ──────────────────────────────────────────────────────

export const CLARIFICATION_QUESTION: ClarificationQuestion = {
  question_id: "q-lm3-001",
  criterion_ids: ["LM-3"],
  question:
    "Have you completed at least six weeks of physical therapy, anti-inflammatory medication, or a home-exercise program without sufficient improvement?",
  why_needed:
    "The chart shows an NSAID on the medication list and a physical-therapy referral, but the policy requires documentation that at least six weeks of conservative treatment were completed without sufficient improvement. A referral or a prescription alone does not establish completion or failure.",
  suggested_action:
    "Confirm completion and outcome of conservative therapy; AuthLens will record your answer verbatim and re-evaluate.",
  status: "open",
};

// ── Disclosure decisions (8 total: 7 include, 1 exclude) ──────────────────

export const DISCLOSURE_DECISIONS: DisclosureDecisionRecord[] = [
  {
    decision_id: "dd-001",
    source_id: "note-001",
    item_description: "Encounter note (low back pain follow-up)",
    decision: "include",
    reason: "Primary documentation of the indication, exam findings, and plan for the requested MRI.",
    phi_category: null,
  },
  {
    decision_id: "dd-002",
    source_id: "fhir-cond-001",
    item_description: "Chronic low back pain with radiation to left leg",
    decision: "include",
    reason: "The condition under evaluation; directly supports criteria LM-1 and LM-2.",
    phi_category: null,
  },
  {
    decision_id: "dd-003",
    source_id: "fhir-obs-slr-001",
    item_description: "Positive straight-leg raise observation",
    decision: "include",
    reason: "Examination finding required by criterion LM-4.",
    phi_category: null,
  },
  {
    decision_id: "dd-004",
    source_id: "fhir-med-001",
    item_description: "Naproxen 500 mg twice daily",
    decision: "include",
    reason: "Part of the conservative-treatment history for criterion LM-3.",
    phi_category: null,
  },
  {
    decision_id: "dd-005",
    source_id: "fhir-ref-pt-001",
    item_description: "Physical therapy referral",
    decision: "include",
    reason: "Part of the conservative-treatment history for criterion LM-3.",
    phi_category: null,
  },
  {
    decision_id: "dd-006",
    source_id: "fhir-sr-mri-001",
    item_description: "MRI lumbar spine order",
    decision: "include",
    reason: "The requested service itself.",
    phi_category: null,
  },
  {
    decision_id: "dd-007",
    source_id: "clar-001",
    item_description: "Clinician clarification on conservative therapy",
    decision: "include",
    reason: "Documents completion and failure of conservative treatment (criterion LM-3).",
    phi_category: null,
  },
  {
    decision_id: "dd-008",
    source_id: "fhir-cond-002",
    item_description: "Seasonal allergic rhinitis",
    decision: "exclude",
    reason: "Unrelated to the lumbar MRI request; excluding under minimum-necessary disclosure.",
    phi_category: "unrelated_condition",
  },
];

// ── Agent events ───────────────────────────────────────────────────────────

export const EVENTS_PRE_CLARIFICATION: AgentEvent[] = [
  {
    event_id: "evt-001",
    sequence: 1,
    stage: "intake",
    status: "completed",
    title:
      "Intake complete: note, transcript, chart, requested service, and payer policy loaded",
    detail: "Synthetic demo fixture ‘lumbar_mri_prior_auth’ loaded.",
    related_ids: [],
    occurred_at: "2026-07-18T16:00:30Z",
  },
  {
    event_id: "evt-002",
    sequence: 2,
    stage: "policy_parsing",
    status: "completed",
    title: "Parsed policy MHP-IMG-2201 into 7 medical-necessity criteria",
    detail: null,
    related_ids: ["LM-1", "LM-2", "LM-3", "LM-4", "LM-5", "LM-6", "LM-7"],
    occurred_at: "2026-07-18T16:01:00Z",
  },
  {
    event_id: "evt-003",
    sequence: 3,
    stage: "evidence_retrieval",
    status: "completed",
    title: "Searched note, transcript, and chart for all 7 criteria in parallel",
    detail: null,
    related_ids: [],
    occurred_at: "2026-07-18T16:02:00Z",
  },
  {
    event_id: "evt-004",
    sequence: 4,
    stage: "evidence_mapping",
    status: "completed",
    title: "Mapped 11 cited evidence excerpts to criteria",
    detail: null,
    related_ids: [],
    occurred_at: "2026-07-18T16:03:00Z",
  },
  {
    event_id: "evt-005",
    sequence: 5,
    stage: "gap_detection",
    status: "completed",
    title: "Classified criteria: 5 met, 1 weak, 1 missing (LM-3 conservative therapy)",
    detail: "Referral and prescription found but neither proves completed/failed therapy.",
    related_ids: ["LM-3", "LM-6"],
    occurred_at: "2026-07-18T16:04:00Z",
  },
  {
    event_id: "evt-006",
    sequence: 6,
    stage: "clarification",
    status: "started",
    title: "Generated 1 point-of-capture clarification question; awaiting clinician",
    detail: null,
    related_ids: ["q-lm3-001"],
    occurred_at: "2026-07-18T16:04:30Z",
  },
];

export const EVENTS_POST_CLARIFICATION: AgentEvent[] = [
  ...EVENTS_PRE_CLARIFICATION.map((e) =>
    e.event_id === "evt-006" ? { ...e, status: "completed" as EventStatus } : e
  ),
  {
    event_id: "evt-007",
    sequence: 7,
    stage: "clarification",
    status: "completed",
    title: "Clinician clarification recorded verbatim for LM-3",
    detail: null,
    related_ids: ["q-lm3-001", "clar-001"],
    occurred_at: "2026-07-18T16:10:00Z",
  },
  {
    event_id: "evt-008",
    sequence: 8,
    stage: "gap_detection",
    status: "completed",
    title: "Re-evaluated criteria after clarification: 6 met, 1 weak, 0 missing; readiness 79 → 93",
    detail: null,
    related_ids: ["LM-3"],
    occurred_at: "2026-07-18T16:11:00Z",
  },
  {
    event_id: "evt-009",
    sequence: 9,
    stage: "disclosure_review",
    status: "completed",
    title: "Disclosure review: 7 items included, 1 unrelated item excluded",
    detail: null,
    related_ids: ["dd-008"],
    occurred_at: "2026-07-18T16:11:30Z",
  },
  {
    event_id: "evt-010",
    sequence: 10,
    stage: "packet_generation",
    status: "completed",
    title: "Generated focused packet with 3 sections and 7 cited claims",
    detail: null,
    related_ids: ["pkt-001"],
    occurred_at: "2026-07-18T16:12:00Z",
  },
  {
    event_id: "evt-011",
    sequence: 11,
    stage: "verification",
    status: "completed",
    title: "Verified all 7 claims against cited sources and policy: passed",
    detail: null,
    related_ids: ["ver-001"],
    occurred_at: "2026-07-18T16:13:00Z",
  },
  {
    event_id: "evt-012",
    sequence: 12,
    stage: "form_drafting",
    status: "completed",
    title: "Populated mock payer form from verified packet",
    detail: null,
    related_ids: ["form-001"],
    occurred_at: "2026-07-18T16:14:00Z",
  },
  {
    event_id: "evt-013",
    sequence: 13,
    stage: "human_review",
    status: "started",
    title: "Ready for Clinician Review — AuthLens stops here; nothing is submitted",
    detail: null,
    related_ids: [],
    occurred_at: "2026-07-18T16:14:30Z",
  },
];

// ── FHIR chart items ───────────────────────────────────────────────────────

export const CHART_ITEMS: ChartItem[] = [
  {
    source_id: "fhir-cond-001",
    category: "condition",
    display: "Chronic low back pain with radiation to left leg",
    // ICD-10-CM M54.16 (Radiculopathy, lumbar region); SNOMED 279039007
    detail: "ICD-10-CM M54.16 · Onset ~8 weeks; suspected lumbar radiculopathy",
  },
  {
    source_id: "fhir-obs-slr-001",
    category: "observation",
    display: "Straight-leg raise: positive on left at 40 degrees",
    // SNOMED 279372000 (Straight leg raising test); Observation.valueCodeableConcept: positive lateralized left
    detail: "SNOMED 279372000 · Physical exam — positive finding, left at 40°",
  },
  {
    source_id: "fhir-med-001",
    category: "medication",
    display: "Naproxen 500 mg twice daily (NSAID)",
    // RxNorm 849727 (naproxen 500 MG Oral Tablet); ATC M01AE02
    detail: "RxNorm 849727 · Active; start date not documented",
  },
  {
    source_id: "fhir-ref-pt-001",
    category: "referral",
    display: "Referral to physical therapy",
    // SNOMED 91251008 (Physical therapy procedure); ServiceRequest.intent = proposal
    detail: "SNOMED 91251008 · Referral present; completion not documented — key LM-3 gap",
  },
  {
    source_id: "fhir-sr-mri-001",
    category: "service_request",
    display: "MRI lumbar spine without contrast (CPT 72148)",
    // CPT 72148; SNOMED 241612008; reasons: M54.16 + M54.41
    detail: "CPT 72148 · SNOMED 241612008 · Indication: M54.16 + M54.41",
  },
  {
    source_id: "fhir-cond-002",
    category: "condition",
    display: "Seasonal allergic rhinitis",
    // ICD-10-CM J30.1; SNOMED 367498001 — excluded under minimum-necessary PHI
    detail: "ICD-10-CM J30.1 · Unrelated — excluded from PA packet (phi_category: unrelated_condition)",
  },
];

// ── Source content lookup (keyed by source_id, for citation drawer) ────────

export const SOURCE_LOOKUP: Record<string, SourceContent> = {
  "note-001": {
    source_id: "note-001",
    title: "Clinic note — low back pain follow-up (synthetic, Abridge-style)",
    content: NOTE_TEXT,
    source_type: "encounter_note",
  },
  "transcript-001": {
    source_id: "transcript-001",
    title: "Encounter transcript",
    content: TRANSCRIPT_TEXT,
    source_type: "encounter_transcript",
  },
  "fhir-cond-001": {
    source_id: "fhir-cond-001",
    title: "FHIR R4 Condition — Chronic low back pain with radiculopathy",
    content: `{
  "resourceType": "Condition",
  "id": "fhir-cond-001",
  "clinicalStatus": {
    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
  },
  "verificationStatus": {
    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "provisional"}]
  },
  "code": {
    "coding": [
      {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M54.16", "display": "Radiculopathy, lumbar region"},
      {"system": "http://snomed.info/sct", "code": "279039007", "display": "Low back pain (finding)"}
    ],
    "text": "Chronic low back pain with radiation to left leg"
  },
  "subject": {"reference": "Patient/pt-demo-001"},
  "onsetString": "Approximately 8 weeks prior to encounter",
  "note": [{"text": "Suspected lumbar radiculopathy. Pain radiates to left leg, worse with sitting and bending."}]
}`,
    source_type: "fhir_resource",
  },
  "fhir-obs-slr-001": {
    source_id: "fhir-obs-slr-001",
    title: "FHIR R4 Observation — Straight-leg raise (positive, left, 40°)",
    content: `{
  "resourceType": "Observation",
  "id": "fhir-obs-slr-001",
  "status": "final",
  "category": [
    {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "exam", "display": "Exam"}]}
  ],
  "code": {
    "coding": [{"system": "http://snomed.info/sct", "code": "279372000", "display": "Straight leg raising test (procedure)"}],
    "text": "Straight-leg raise"
  },
  "subject": {"reference": "Patient/pt-demo-001"},
  "valueCodeableConcept": {
    "coding": [{"system": "http://snomed.info/sct", "code": "10828004", "display": "Positive (qualifier value)"}],
    "text": "Positive on left at 40 degrees"
  },
  "component": [
    {
      "code": {"coding": [{"system": "http://snomed.info/sct", "code": "272741003", "display": "Laterality"}]},
      "valueCodeableConcept": {"coding": [{"system": "http://snomed.info/sct", "code": "7771000", "display": "Left (qualifier value)"}]}
    },
    {
      "code": {"text": "Angle at onset of pain"},
      "valueQuantity": {"value": 40, "unit": "deg", "system": "http://unitsofmeasure.org", "code": "deg"}
    }
  ]
}`,
    source_type: "fhir_resource",
  },
  "fhir-med-001": {
    source_id: "fhir-med-001",
    title: "FHIR R4 MedicationRequest — Naproxen 500 mg twice daily",
    content: `{
  "resourceType": "MedicationRequest",
  "id": "fhir-med-001",
  "status": "active",
  "intent": "order",
  "medicationCodeableConcept": {
    "coding": [
      {"system": "http://www.nlm.nih.gov/research/umls/rxnorm", "code": "849727", "display": "naproxen 500 MG Oral Tablet"},
      {"system": "http://www.whocc.no/atc", "code": "M01AE02", "display": "Naproxen"}
    ],
    "text": "Naproxen 500 mg twice daily"
  },
  "subject": {"reference": "Patient/pt-demo-001"},
  "dosageInstruction": [{
    "text": "500 mg orally twice daily",
    "timing": {"repeat": {"frequency": 2, "period": 1, "periodUnit": "d"}},
    "doseAndRate": [{"doseQuantity": {"value": 500, "unit": "mg", "system": "http://unitsofmeasure.org", "code": "mg"}}]
  }],
  "note": [{"text": "Active medication on list; start date not documented. Present as conservative treatment evidence but does not confirm completion or failure (LM-3)."}]
}`,
    source_type: "fhir_resource",
  },
  "fhir-ref-pt-001": {
    source_id: "fhir-ref-pt-001",
    title: "FHIR R4 ServiceRequest — Physical therapy referral",
    content: `{
  "resourceType": "ServiceRequest",
  "id": "fhir-ref-pt-001",
  "status": "active",
  "intent": "proposal",
  "code": {
    "coding": [{"system": "http://snomed.info/sct", "code": "91251008", "display": "Physical therapy procedure (regime/therapy)"}],
    "text": "Referral to physical therapy"
  },
  "subject": {"reference": "Patient/pt-demo-001"},
  "reasonCode": [
    {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M54.16", "display": "Radiculopathy, lumbar region"}]}
  ],
  "note": [{"text": "Referral order present; completion and outcome not documented. This is the critical LM-3 gap — presence of a referral does not satisfy the criterion without documentation of completion and failure."}]
}`,
    source_type: "fhir_resource",
  },
  "fhir-sr-mri-001": {
    source_id: "fhir-sr-mri-001",
    title: "FHIR R4 ServiceRequest — MRI lumbar spine w/o contrast (CPT 72148)",
    content: `{
  "resourceType": "ServiceRequest",
  "id": "fhir-sr-mri-001",
  "status": "active",
  "intent": "order",
  "code": {
    "coding": [
      {"system": "http://www.ama-assn.org/go/cpt", "code": "72148", "display": "MRI lumbar spine without contrast"},
      {"system": "http://snomed.info/sct", "code": "241612008", "display": "MRI of lumbar spine"}
    ],
    "text": "MRI lumbar spine without contrast (CPT 72148)"
  },
  "subject": {"reference": "Patient/pt-demo-001"},
  "reasonCode": [
    {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M54.16", "display": "Radiculopathy, lumbar region"}]},
    {"coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "M54.41", "display": "Lumbago with sciatica, left side"}]}
  ],
  "reasonReference": [{"reference": "Condition/fhir-cond-001"}]
}`,
    source_type: "fhir_resource",
  },
  "fhir-cond-002": {
    source_id: "fhir-cond-002",
    title: "FHIR R4 Condition — Seasonal allergic rhinitis (EXCLUDED from packet)",
    content: `{
  "resourceType": "Condition",
  "id": "fhir-cond-002",
  "clinicalStatus": {
    "coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]
  },
  "code": {
    "coding": [
      {"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": "J30.1", "display": "Allergic rhinitis due to pollen"},
      {"system": "http://snomed.info/sct", "code": "367498001", "display": "Seasonal allergic rhinitis (disorder)"}
    ],
    "text": "Seasonal allergic rhinitis"
  },
  "subject": {"reference": "Patient/pt-demo-001"},
  "extension": [
    {
      "url": "http://authlens.abridge.com/fhir/StructureDefinition/packet-exclusion",
      "valueBoolean": true
    },
    {
      "url": "http://authlens.abridge.com/fhir/StructureDefinition/exclusion-reason",
      "valueString": "Unrelated condition — excluded under minimum-necessary PHI disclosure (phi_category: unrelated_condition)"
    }
  ]
}`,
    source_type: "fhir_resource",
  },
  "clar-001": {
    source_id: "clar-001",
    title: "Clinician clarification — conservative therapy (q-lm3-001)",
    content: CLARIFICATION_RESPONSE,
    source_type: "clinician_clarification",
  },
};

// ── Form fields (10 fields, from ready_for_review.json) ───────────────────

export const FORM_DRAFT_FIELDS_AFTER: FormField[] = [
  {
    field_id: "f-patient",
    label: "Patient name",
    value: "Jordan Rivera (synthetic)",
    source_claim_ids: [],
  },
  {
    field_id: "f-dob",
    label: "Date of birth",
    value: "1979-04-02",
    source_claim_ids: [],
  },
  {
    field_id: "f-service",
    label: "Requested service",
    value: "MRI lumbar spine without contrast (CPT 72148)",
    source_claim_ids: [],
  },
  {
    field_id: "f-indication",
    label: "Clinical indication",
    value:
      "Suspected lumbar radiculopathy (M54.16); chronic low back pain with radicular symptoms (M54.41)",
    source_claim_ids: [],
  },
  {
    field_id: "f-duration",
    label: "Symptom duration",
    value: "Approximately 8 weeks",
    source_claim_ids: ["clm-001"],
  },
  {
    field_id: "f-conservative",
    label: "Conservative treatment completed and outcome",
    value:
      "8 weeks of physical therapy, scheduled naproxen, and home-exercise program completed without sufficient improvement (clinician attestation)",
    source_claim_ids: ["clm-004"],
  },
  {
    field_id: "f-exam",
    label: "Relevant examination findings",
    value:
      "Positive left straight-leg raise at 40 degrees; decreased sensation left lateral calf",
    source_claim_ids: ["clm-002"],
  },
  {
    field_id: "f-redflags",
    label: "Red-flag screening",
    value: "Documented and negative",
    source_claim_ids: ["clm-003"],
  },
  {
    field_id: "f-function",
    label: "Functional limitation",
    value: "Difficulty sitting through a full workday; interrupted sleep",
    source_claim_ids: ["clm-005"],
  },
  {
    field_id: "f-rationale",
    label: "How results will change management",
    value: "Evaluation for epidural steroid injection or surgical referral",
    source_claim_ids: ["clm-006"],
  },
];

export const FORM_ATTESTATION =
  "DRAFT FOR CLINICIAN REVIEW - generated by AuthLens from cited chart evidence and a recorded clinician clarification. Not submitted to any payer. Not a guarantee of approval.";
