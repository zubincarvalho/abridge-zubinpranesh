import './PriorAuthFormDraft.css';
import {
  FORM_DRAFT_FIELDS_AFTER,
  ASSESSMENTS,
} from '../data/mockCase';
import type { ApiFormDraft, ApiCriterionAssessment } from '../api/client';

type Props = {
  hasClarification: boolean;
  onSourceClick: (sourceId: string, excerpt?: string) => void;
  formDraft?: ApiFormDraft;
  assessments?: ApiCriterionAssessment[];
};

const STATUS_LABEL: Record<string, string> = {
  met: 'Supported',
  weak: 'Needs clarification',
  missing: 'Not supported',
};

const ATTESTATION_BEFORE =
  'DRAFT FOR CLINICIAN REVIEW — generated from cited chart evidence. One required clarification is still pending. Not submitted to any payer.';

const ATTESTATION_AFTER =
  'DRAFT FOR CLINICIAN REVIEW — updated from cited chart evidence and recorded clinician clarification. Not submitted to any payer. Not a guarantee of approval.';

export default function PriorAuthFormDraft({ hasClarification, onSourceClick, formDraft, assessments: liveAssessments }: Props) {
  const activeAssessments = liveAssessments ?? ASSESSMENTS;

  // Use live form draft fields when available, fall back to mock
  const liveFields = formDraft?.fields;
  const fields = liveFields
    ? liveFields
    : hasClarification
      ? FORM_DRAFT_FIELDS_AFTER
      : FORM_DRAFT_FIELDS_AFTER.filter((f) => f.field_id !== 'f-conservative');

  const gapFields = (!liveFields && !hasClarification) ? ['f-conservative'] : [];

  // Has open gaps when no form draft yet and not clarified
  const hasOpenGap = !formDraft && !hasClarification;

  const attestation = formDraft?.attestation
    ?? (hasClarification ? ATTESTATION_AFTER : ATTESTATION_BEFORE);

  const formName = formDraft?.payer_form_name
    ?? 'Meridian Health Plans — Advanced Imaging Prior Authorization Request (MOCK)';

  return (
    <div className="pa-form panel">
      <div className="panel-header">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span className="panel-header-title">Prior Authorization Form Draft</span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
            {formName}
          </span>
        </div>
        <span className={`chip ${(hasClarification || formDraft) ? 'chip-met' : 'chip-weak'}`}>
          {(hasClarification || formDraft) ? 'Ready for Human Review' : 'Needs Clarification'}
        </span>
      </div>

      <div className="pa-form-body">
        {hasOpenGap && (
          <div className="pa-gap-warning">
            <span>⚠</span> LM-3 (Conservative therapy) needs clinician clarification to document
            completion of conservative treatment. Add a response to complete the form.
          </div>
        )}

        <div className="pa-fields-grid">
          {fields.map((f) => {
            // Find a source to link to from live assessments
            const firstEv = liveAssessments
              ? liveAssessments.flatMap((a) => a.evidence).find(
                  (_ev) => f.source_claim_ids.length > 0
                )
              : ASSESSMENTS.find((a) =>
                  f.source_claim_ids.length > 0 &&
                  a.evidence_after.some(() => true)
                )?.evidence_after[0];

            return (
              <div key={f.field_id} className="pa-field-row">
                <div className="pa-field-label">{f.label}</div>
                <div className="pa-field-value-row">
                  <span className="pa-field-value">{f.value}</span>
                  {f.source_claim_ids.length > 0 && firstEv && (
                    <button
                      className="pa-cite-btn"
                      onClick={() => onSourceClick(firstEv.source_id, firstEv.excerpt)}
                      title="View source"
                    >
                      ↗
                    </button>
                  )}
                </div>
              </div>
            );
          })}

          {gapFields.map((fid) => {
            const orig = FORM_DRAFT_FIELDS_AFTER.find((f) => f.field_id === fid);
            return orig ? (
              <div key={fid} className="pa-field-row pa-field-row--missing">
                <div className="pa-field-label">{orig.label}</div>
                <div className="pa-field-value-row">
                  <span className="pa-field-missing">Missing — awaiting clinician clarification</span>
                </div>
              </div>
            ) : null;
          })}
        </div>

        <div className="pa-criteria-summary">
          <div className="pa-cs-title">Criteria status at submission</div>
          <div className="pa-cs-rows">
            {activeAssessments.map((a) => {
              const status = liveAssessments
                ? a.status
                : (hasClarification ? (a as any).status_after ?? a.status : a.status);
              return (
                <div key={a.criterion_id} className={`pa-cs-row pa-cs-${status}`}>
                  <span className="pa-cs-id">{a.criterion_id}</span>
                  <span className="pa-cs-status">{STATUS_LABEL[status] ?? status}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="pa-attestation">
          <div className="pa-attestation-icon">⚠</div>
          <div className="pa-attestation-text">{attestation}</div>
        </div>

        {(hasClarification || formDraft) && (
          <div className="pa-final-status pa-final-ready animate-fade-in">
            <div className="pa-final-icon">✓</div>
            <div className="pa-final-content">
              <div className="pa-final-title">Ready for Human Review</div>
              <div className="pa-final-note">
                AuthLens does not auto-submit prior authorizations. A clinician must review and
                attest before submission to the payer.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
