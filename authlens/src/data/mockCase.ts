export type CriterionStatus = "met" | "weak" | "missing";

export type SourceDetail = {
  type: "note" | "transcript" | "fhir" | "clarification";
  title: string;
  excerpt: string;
  speaker?: string;
  resourceType?: string;
};

export type EvidenceRow = {
  id: string;
  criterion: string;
  status: CriterionStatus;
  statusAfter: CriterionStatus;
  evidence: string;
  evidenceAfter: string;
  source: string;
  suggestedFix?: string;
  sourceDetail: SourceDetail;
};

export type NotePhrase = {
  id: string;
  text: string;
  sourceDetail: SourceDetail;
};

export type AppState = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  readinessScore: number;
  overallStatus: "Not started" | "Needs clarification" | "Ready for human review";
  selectedSource?: SourceDetail;
};

export const EVIDENCE_ROWS: EvidenceRow[] = [
  {
    id: "diagnosis",
    criterion: "Diagnosis / clinical indication documented",
    status: "met",
    statusAfter: "met",
    evidence: "Chronic low back pain with left-sided radicular symptoms",
    evidenceAfter: "Chronic low back pain with left-sided radicular symptoms",
    source: "Abridge Note / Assessment",
    sourceDetail: {
      type: "note",
      title: "Encounter Note — Assessment",
      excerpt:
        "Assessment: Chronic low back pain with left-sided radicular symptoms.\n\nICD-10: M54.16",
    },
  },
  {
    id: "duration",
    criterion: "Symptoms > 6 weeks",
    status: "weak",
    statusAfter: "met",
    evidence: '"Several months" noted, but exact duration not structured',
    evidenceAfter:
      'Patient confirmed symptoms have persisted for over 8 weeks (clinician clarification)',
    source: "Abridge Note / HPI",
    suggestedFix: "Clarify exact symptom duration",
    sourceDetail: {
      type: "transcript",
      title: "Encounter Transcript — HPI",
      excerpt:
        'Patient: "It\'s been going on for a few months and shoots down my left leg, especially when I sit."\n\nNote: Duration recorded as "several months" — exact weeks not documented.',
      speaker: "Patient",
    },
  },
  {
    id: "conservative",
    criterion: "Conservative therapy attempted and failed",
    status: "missing",
    statusAfter: "met",
    evidence:
      "Ibuprofen trial found; PT referral found, but PT outcome not documented",
    evidenceAfter:
      "Patient completed six weeks of PT and NSAID therapy without meaningful improvement (clinician clarification)",
    source: "Note + FHIR MedicationRequest / ServiceRequest",
    suggestedFix: "Ask about PT/NSAID outcome",
    sourceDetail: {
      type: "fhir",
      title: "FHIR MedicationRequest + ServiceRequest",
      excerpt:
        'MedicationRequest: Ibuprofen 600 mg tablet — status: active\nServiceRequest: Physical therapy referral — status: pending\n\nGap: No therapy completion or outcome documented.',
      resourceType: "MedicationRequest + ServiceRequest",
    },
  },
  {
    id: "neuro",
    criterion: "Neurologic findings documented",
    status: "met",
    statusAfter: "met",
    evidence: "Positive straight-leg raise; radicular symptoms noted",
    evidenceAfter: "Positive straight-leg raise; radicular symptoms noted",
    source: "Abridge Note / Exam",
    sourceDetail: {
      type: "note",
      title: "Encounter Note — Physical Exam",
      excerpt:
        "Exam: Positive straight-leg raise on the left. Strength grossly intact.\n\nRadicular symptoms include left leg pain radiating to the foot with numbness and tingling.",
    },
  },
  {
    id: "redflags",
    criterion: "Red-flag screen complete",
    status: "weak",
    statusAfter: "met",
    evidence:
      "No bowel/bladder changes noted; broader red-flag screen incomplete",
    evidenceAfter:
      "No fever, trauma, cancer history, progressive weakness, or bowel/bladder dysfunction (clinician clarification)",
    source: "Abridge Note / HPI",
    suggestedFix: "Complete red-flag screening",
    sourceDetail: {
      type: "transcript",
      title: "Encounter Transcript — HPI",
      excerpt:
        'Clinician: "Any changes in bowel or bladder?"\nPatient: "No."\n\nGap: Fever, trauma history, cancer history, progressive neurologic weakness not explicitly screened or documented.',
      speaker: "Clinician / Patient",
    },
  },
];

export const NOTE_PHRASES: NotePhrase[] = [
  {
    id: "duration",
    text: "low back pain for several months",
    sourceDetail: {
      type: "transcript",
      title: "Encounter Transcript — HPI",
      excerpt:
        'Patient: "It\'s been going on for a few months and shoots down my left leg, especially when I sit."\n\nConfidence: High',
      speaker: "Patient",
    },
  },
  {
    id: "radiation",
    text: "radiates down the left leg",
    sourceDetail: {
      type: "transcript",
      title: "Encounter Transcript — HPI",
      excerpt:
        'Patient: "The pain shoots down my left leg to my foot. I get numbness and tingling there too."\n\nConfidence: High',
      speaker: "Patient",
    },
  },
  {
    id: "bowelbladder",
    text: "No bowel or bladder changes",
    sourceDetail: {
      type: "transcript",
      title: "Encounter Transcript — Red Flag Screen",
      excerpt:
        'Clinician: "Any changes in bowel or bladder control?"\nPatient: "No changes there."\n\nConfidence: High',
      speaker: "Clinician / Patient",
    },
  },
  {
    id: "nsaid",
    text: "ibuprofen with partial relief",
    sourceDetail: {
      type: "fhir",
      title: "FHIR MedicationRequest",
      excerpt:
        "MedicationRequest: Ibuprofen 600 mg tablet, 1 tab PO q6h PRN pain\nStatus: Active\n\nPatient reported partial relief — full outcome not documented.",
      resourceType: "MedicationRequest",
    },
  },
  {
    id: "slr",
    text: "Positive straight-leg raise",
    sourceDetail: {
      type: "note",
      title: "Encounter Note — Physical Exam",
      excerpt:
        "Exam: Positive straight-leg raise on the left. Strength grossly intact.\n\nClinical significance: Suggests L4–S1 nerve root involvement.",
    },
  },
  {
    id: "order",
    text: "Order lumbar spine MRI",
    sourceDetail: {
      type: "fhir",
      title: "FHIR ServiceRequest",
      excerpt:
        "ServiceRequest: MRI Lumbar Spine without contrast\nStatus: Draft — prior authorization required\nOrdering provider: Kelsey Morris, MD\nPriority: Routine",
      resourceType: "ServiceRequest",
    },
  },
];

export const AGENT_STEPS = [
  {
    id: "policy",
    label: "Policy Agent",
    detail: "Parsed 5 payer criteria",
    icon: "📋",
    status: "completed" as const,
  },
  {
    id: "evidence",
    label: "Evidence Agent",
    detail: "Scanned note + FHIR resources",
    icon: "🔍",
    status: "completed" as const,
  },
  {
    id: "gap",
    label: "Gap Agent",
    detail: "Found 3 weak/missing criteria",
    icon: "⚠️",
    status: "warning" as const,
  },
  {
    id: "disclosure",
    label: "Disclosure Agent",
    detail: "Filtered unrelated patient context",
    icon: "🔒",
    status: "completed" as const,
  },
  {
    id: "form",
    label: "Form Agent",
    detail: "Drafted prior-auth request",
    icon: "📝",
    status: "review" as const,
  },
];
