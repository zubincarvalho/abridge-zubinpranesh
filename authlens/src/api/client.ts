// AuthLens API client — mirrors Python contracts in app/contracts/

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

// ── Shared types (mirrors contracts) ──────────────────────────────────────

export type CaseStatus =
  | 'draft'
  | 'intake_ready'
  | 'analyzing'
  | 'awaiting_clarification'
  | 'reanalyzing'
  | 'packet_drafted'
  | 'verification_failed'
  | 'verified'
  | 'ready_for_review';

export type SourceType =
  | 'encounter_note'
  | 'encounter_transcript'
  | 'fhir_resource'
  | 'clinician_clarification'
  | 'payer_policy';

export type EvidenceConfidence = 'high' | 'moderate' | 'low';
export type CriterionStatus = 'met' | 'weak' | 'missing' | 'conflicting' | 'not_applicable';
export type AgentStage =
  | 'intake' | 'policy_parsing' | 'evidence_retrieval' | 'evidence_mapping'
  | 'gap_detection' | 'clarification' | 'disclosure_review' | 'packet_generation'
  | 'verification' | 'form_drafting' | 'human_review';
export type EventStatus = 'started' | 'completed' | 'failed' | 'skipped';

export type TextSpan = { start: number; end: number };

export type ApiEvidenceItem = {
  evidence_id: string;
  source_id: string;
  source_type: SourceType;
  excerpt: string;
  span: TextSpan | null;
  fhir_path: string | null;
  confidence: EvidenceConfidence;
  note: string | null;
};

export type ApiPolicyCriterion = {
  criterion_id: string;
  policy_id: string;
  label: string;
  requirement: string;
  category: string;
  applicability_note?: string | null;
};

export type ApiPayerPolicy = {
  policy_id: string;
  payer_name: string;
  policy_title: string;
  service_description: string;
  source_document: string;
  synthetic: boolean;
};

export type ApiRequestedService = {
  service_name: string;
  code: string;
  code_system: string;
  modality: string | null;
  body_site: string | null;
};

export type ApiEncounterTranscript = {
  source_id: string;
  text: string;
};

export type ApiDisclosureDecision = {
  decision_id: string;
  source_id: string;
  item_description: string;
  decision: 'include' | 'exclude';
  reason: string;
  phi_category: string | null;
};

export type ApiPacketClaim = {
  claim_id: string;
  text: string;
  claim_type: 'clinical' | 'policy';
  criterion_id: string | null;
  evidence_ids: string[];
};

export type ApiPacketSection = {
  section_id: string;
  title: string;
  body: string;
  claim_ids: string[];
};

export type ApiPacket = {
  packet_id: string;
  case_id: string;
  status: string;
  sections: ApiPacketSection[];
  claims: ApiPacketClaim[];
};

export type ApiVerificationIssue = {
  issue_id: string;
  severity: string;
  claim_id: string | null;
  description: string;
  suggested_resolution: string;
};

export type ApiVerification = {
  verification_id: string;
  packet_id: string;
  passed: boolean;
  checked_claim_count: number;
  issues: ApiVerificationIssue[];
};

export type ApiCriterionAssessment = {
  criterion_id: string;
  status: CriterionStatus;
  denial_risk: 'low' | 'medium' | 'high';
  rationale: string;
  evidence: ApiEvidenceItem[];
};

export type ApiClarificationQuestion = {
  question_id: string;
  criterion_ids: string[];
  question: string;
  why_needed: string;
  suggested_action: string;
  status: 'open' | 'answered';
};

export type ApiClinicianClarification = {
  clarification_id: string;
  question_id: string;
  response: string;
  recorded_at: string;
};

export type ApiReadinessSummary = {
  label: string;
  score: number;
  criteria_met: number;
  criteria_weak: number;
  criteria_missing: number;
  criteria_conflicting: number;
  criteria_not_applicable: number;
  overall_denial_risk: 'low' | 'medium' | 'high';
};

export type ApiChartItem = {
  source_id: string;
  category: string;
  display: string;
  detail: string | null;
};

export type ApiEncounterNote = {
  source_id: string;
  title: string;
  text: string;
};

export type ApiFormDraftField = {
  field_id: string;
  label: string;
  value: string;
  source_claim_ids: string[];
};

export type ApiFormDraft = {
  form_id: string;
  case_id: string;
  packet_id: string;
  payer_form_name: string;
  fields: ApiFormDraftField[];
  attestation: string;
  status: string;
};

export type ApiAgentEvent = {
  event_id: string;
  sequence: number;
  stage: AgentStage;
  status: EventStatus;
  title: string;
  detail: string | null;
  related_ids: string[];
  occurred_at: string;
};

export type ApiCase = {
  case_id: string;
  status: CaseStatus;
  created_at: string;
  updated_at: string;
  synthetic: boolean;
  patient: {
    patient_id: string;
    display_name: string;
    birth_date: string;
    sex: string;
    chart_items: ApiChartItem[];
  };
  encounter_note: ApiEncounterNote;
  encounter_transcript: ApiEncounterTranscript | null;
  requested_service: ApiRequestedService;
  clinical_indication: string;
  indication_codes: string[];
  policy: ApiPayerPolicy;
  criteria: ApiPolicyCriterion[];
  assessments: ApiCriterionAssessment[];
  clarification_questions: ApiClarificationQuestion[];
  clarifications: ApiClinicianClarification[];
  readiness_history: ApiReadinessSummary[];
  disclosure_decisions: ApiDisclosureDecision[];
  packet: ApiPacket | null;
  verification: ApiVerification | null;
  form_draft: ApiFormDraft | null;
  events: ApiAgentEvent[];
};

export type ApiEvidenceSource = {
  source_id: string;
  source_type: SourceType;
  label: string;
  content: string;
  fhir_resource_type: string | null;
};

export type DemoScenario = {
  scenario_id: string;
  fixture_id: string;
  title: string;
  patient_display: string;
  visit_summary: string;
  requested_service: string;
  payer: string;
  policy_id: string;
  expected_outcome: 'gap' | 'high_risk' | 'approved';
  expected_outcome_label: string;
  risk_level: 'low' | 'medium' | 'high';
  description: string;
  is_real_data: boolean;
};

// ── HTTP helper ────────────────────────────────────────────────────────────

async function api<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    // Backend error envelope is flat ApiError: {error_code, message, detail?, case_id?}.
    const err = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(err?.message ?? err?.error?.message ?? `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Public API functions ───────────────────────────────────────────────────

export function listScenarios(): Promise<DemoScenario[]> {
  return api<DemoScenario[]>('GET', '/scenarios');
}

export function createCase(fixtureId: string): Promise<ApiCase> {
  return api<ApiCase>('POST', '/cases', { fixture_id: fixtureId });
}

export function getDemoCase(): Promise<ApiCase> {
  return api<ApiCase>('GET', '/demo-case');
}

export function runAnalysis(caseId: string): Promise<ApiCase> {
  return api<ApiCase>('POST', `/cases/${caseId}/run`);
}

export function submitClarification(
  caseId: string,
  questionId: string,
  response: string,
): Promise<ApiCase> {
  return api<ApiCase>('POST', `/cases/${caseId}/clarifications`, {
    question_id: questionId,
    response,
  });
}

export function generatePacket(caseId: string): Promise<ApiCase> {
  return api<ApiCase>('POST', `/cases/${caseId}/generate-packet`);
}

export function verifyPacket(caseId: string): Promise<ApiCase> {
  return api<ApiCase>('POST', `/cases/${caseId}/verify`);
}

export function draftForm(caseId: string): Promise<ApiCase> {
  return api<ApiCase>('POST', `/cases/${caseId}/form-draft`);
}

export function getEvents(caseId: string): Promise<ApiAgentEvent[]> {
  return api<ApiAgentEvent[]>('GET', `/cases/${caseId}/events`);
}

export function getEvidenceSource(caseId: string, sourceId: string): Promise<ApiEvidenceSource> {
  return api<ApiEvidenceSource>('GET', `/cases/${caseId}/evidence/${sourceId}`);
}

export function resetDemo(): Promise<{ demo_case_id: string }> {
  return api<{ demo_case_id: string }>('POST', '/demo/reset');
}

// ── Helpers for UI ─────────────────────────────────────────────────────────

export function latestReadiness(c: ApiCase): ApiReadinessSummary | null {
  return c.readiness_history.length > 0
    ? c.readiness_history[c.readiness_history.length - 1]
    : null;
}

export function openQuestion(c: ApiCase): ApiClarificationQuestion | null {
  return c.clarification_questions.find((q) => q.status === 'open') ?? null;
}

export function hasRunAnalysis(c: ApiCase): boolean {
  return c.status !== 'intake_ready';
}

export function hasClarificationRecorded(c: ApiCase): boolean {
  return c.clarifications.length > 0;
}

export function isReadyForReview(c: ApiCase): boolean {
  return c.status === 'ready_for_review' || c.status === 'verified';
}
