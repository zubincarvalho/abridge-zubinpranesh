import './PriorAuthFormDraft.css';

type Props = {
  hasClarification: boolean;
  onSourceClick: (source: { type: 'note' | 'transcript' | 'fhir' | 'clarification'; title: string; excerpt: string }) => void;
};

type ChecklistItem = { label: string; status: 'complete' | 'needs' | 'missing' };

function StatusIcon({ status }: { status: ChecklistItem['status'] }) {
  if (status === 'complete') return <span className="form-check-icon check-complete">✓</span>;
  if (status === 'needs') return <span className="form-check-icon check-needs">!</span>;
  return <span className="form-check-icon check-missing">✕</span>;
}

export default function PriorAuthFormDraft({ hasClarification, onSourceClick }: Props) {
  const checklistBefore: ChecklistItem[] = [
    { label: 'Diagnosis documented', status: 'complete' },
    { label: 'Symptoms > 6 weeks', status: 'needs' },
    { label: 'Conservative therapy failed', status: 'missing' },
    { label: 'Neurologic findings', status: 'complete' },
    { label: 'Red flags screened', status: 'needs' },
  ];

  const checklistAfter: ChecklistItem[] = checklistBefore.map((c) => ({ ...c, status: 'complete' as const }));
  const checklist = hasClarification ? checklistAfter : checklistBefore;

  const rationaleText = hasClarification
    ? 'Patient has over 8 weeks of low back pain with left-sided radicular symptoms and positive straight-leg raise. Symptoms persisted despite six weeks of physical therapy and NSAID therapy without meaningful improvement. No fever, trauma, cancer history, progressive weakness, or bowel/bladder dysfunction reported. MRI lumbar spine is requested to evaluate possible nerve root compression.'
    : 'Patient has chronic low back pain with left-sided radicular symptoms and positive straight-leg raise. MRI is requested to evaluate possible nerve root compression. Additional documentation is needed for symptom duration, conservative therapy outcome, and complete red-flag screening.';

  const evidenceChips = [
    { label: 'Encounter Note / HPI', type: 'note' as const, excerpt: '47-year-old male with low back pain radiating to left leg for several months.' },
    { label: 'Encounter Note / Exam', type: 'note' as const, excerpt: 'Positive straight-leg raise on the left. Strength grossly intact.' },
    { label: 'FHIR MedicationRequest', type: 'fhir' as const, excerpt: 'Ibuprofen 600 mg tablet, 1 tab PO q6h PRN pain — Active.' },
    { label: 'FHIR ServiceRequest', type: 'fhir' as const, excerpt: 'MRI Lumbar Spine without contrast — prior authorization required.' },
    ...(hasClarification ? [{ label: 'Clinician Clarification', type: 'clarification' as const, excerpt: 'Patient reports over 8 weeks of symptoms. Six weeks of PT and NSAID therapy without improvement. No red flags.' }] : []),
    { label: 'Disclosure Summary', type: 'note' as const, excerpt: 'Included: diagnosis, symptom duration, conservative therapy, neurologic exam, red-flag screen. Excluded: unrelated hypertension and preventive-care details.' },
  ];

  return (
    <div className="pa-form panel">
      <div className="panel-header">
        <span className="panel-header-title">Prior Authorization Request Details</span>
        <span className={`chip ${hasClarification ? 'chip-met' : 'chip-orange'}`}>
          {hasClarification ? 'Ready for Human Review' : 'Needs Clarification'}
        </span>
      </div>

      <div className="pa-form-body">
        <div className="pa-grid">

          {/* Request block */}
          <div className="pa-section-block">
            <div className="pa-section-title">Request</div>
            <div className="pa-field-grid">
              <div className="pa-field"><span className="pa-field-label">Requested Service</span><span className="pa-field-value pa-field-value--bold">MRI Lumbar Spine without contrast</span></div>
              <div className="pa-field"><span className="pa-field-label">Place of Service</span><span className="pa-field-value">Outpatient</span></div>
              <div className="pa-field"><span className="pa-field-label">Priority</span><span className="pa-field-value">Routine</span></div>
              <div className="pa-field"><span className="pa-field-label">Ordering Provider</span><span className="pa-field-value">Kelsey Morris, MD</span></div>
              <div className="pa-field"><span className="pa-field-label">Payer</span><span className="pa-field-value">BlueCross PPO</span></div>
              <div className="pa-field"><span className="pa-field-label">Policy</span><span className="pa-field-value">Lumbar Spine MRI Medical Necessity · 2024-L07</span></div>
            </div>
          </div>

          {/* Patient block */}
          <div className="pa-section-block">
            <div className="pa-section-title">Patient</div>
            <div className="pa-field-grid">
              <div className="pa-field"><span className="pa-field-label">Name</span><span className="pa-field-value pa-field-value--bold">John Smith</span></div>
              <div className="pa-field"><span className="pa-field-label">DOB</span><span className="pa-field-value">05/12/1978</span></div>
              <div className="pa-field"><span className="pa-field-label">Sex</span><span className="pa-field-value">Male</span></div>
              <div className="pa-field"><span className="pa-field-label">MRN</span><span className="pa-field-value">12345678</span></div>
              <div className="pa-field"><span className="pa-field-label">Member ID</span><span className="pa-field-value">BCBS-902184</span></div>
            </div>
          </div>

          {/* Diagnosis block */}
          <div className="pa-section-block">
            <div className="pa-section-title">Diagnosis</div>
            <div className="pa-diagnosis-row">
              <div className="pa-diagnosis-text">Chronic low back pain with left-sided radicular symptoms</div>
              <div className="pa-icd-tag">ICD-10: M54.16</div>
            </div>
          </div>

          {/* Medical necessity checklist */}
          <div className="pa-section-block">
            <div className="pa-section-title">Medical Necessity Checklist</div>
            <div className="pa-checklist">
              {checklist.map((item, i) => (
                <div key={i} className={`pa-checklist-item pa-check-${item.status}`}>
                  <StatusIcon status={item.status} />
                  <span className="pa-check-label">{item.label}</span>
                  {item.status !== 'complete' && (
                    <span className="pa-check-status-text">
                      {item.status === 'needs' ? 'needs clarification' : 'missing'}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Clinical rationale */}
          <div className="pa-section-block pa-section-block--full">
            <div className="pa-section-title">Clinical Rationale</div>
            <div className={`pa-rationale ${hasClarification ? 'pa-rationale--complete' : 'pa-rationale--partial'}`}>
              {rationaleText}
            </div>
            {!hasClarification && (
              <div className="pa-rationale-warning">
                ⚠ Rationale is incomplete. Add clinician clarification to finalize.
              </div>
            )}
          </div>

          {/* Supporting evidence */}
          <div className="pa-section-block pa-section-block--full">
            <div className="pa-section-title">Supporting Evidence</div>
            <div className="pa-evidence-chips">
              {evidenceChips.map((chip, i) => (
                <button
                  key={i}
                  className="pa-evidence-chip"
                  onClick={() => onSourceClick({ type: chip.type, title: chip.label, excerpt: chip.excerpt })}
                >
                  {chip.label} ↗
                </button>
              ))}
            </div>
            <div className="pa-disclosure">
              <div className="pa-disclosure-row">
                <span className="pa-disclosure-label included">Included:</span>
                <span className="pa-disclosure-text">diagnosis, symptom duration, conservative therapy, neurologic exam, red-flag screen</span>
              </div>
              <div className="pa-disclosure-row">
                <span className="pa-disclosure-label excluded">Excluded:</span>
                <span className="pa-disclosure-text">unrelated hypertension history and unrelated preventive-care details</span>
              </div>
            </div>
          </div>

        </div>

        {/* Final status */}
        <div className={`pa-final-status ${hasClarification ? 'pa-final-ready' : 'pa-final-pending'}`}>
          {hasClarification ? (
            <>
              <div className="pa-final-icon">✓</div>
              <div className="pa-final-content">
                <div className="pa-final-title">Ready for Human Review</div>
                <div className="pa-final-note">AuthLens does not auto-submit prior authorizations.</div>
              </div>
            </>
          ) : (
            <>
              <div className="pa-final-icon pa-final-icon--pending">!</div>
              <div className="pa-final-content">
                <div className="pa-final-title">Needs Clarification Before Submission</div>
                <div className="pa-final-note">Complete gaps in the evidence matrix to finalize this request.</div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
