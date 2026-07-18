import { useState } from 'react';
import './PacketStatusPanel.css';
import { READINESS_INITIAL, READINESS_POST_CLARIFICATION } from '../data/mockCase';
import type { ApiCriterionAssessment, CaseStatus } from '../api/client';

type Props = {
  hasRunAnalysis: boolean;
  hasClarification: boolean;
  onOpenForm: () => void;
  assessments?: ApiCriterionAssessment[];
  caseStatus?: CaseStatus;
};

type ClinicianDecision = 'approved' | 'rejected' | 'needs_info' | null;

export default function PacketStatusPanel({
  hasRunAnalysis,
  hasClarification,
  onOpenForm,
  assessments: liveAssessments,
  caseStatus,
}: Props) {
  const [decision, setDecision] = useState<ClinicianDecision>(null);

  const mockReadiness = hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL;

  const readiness = liveAssessments
    ? {
        criteria_met:     liveAssessments.filter((a) => a.status === 'met').length,
        criteria_weak:    liveAssessments.filter((a) => a.status === 'weak').length,
        criteria_missing: liveAssessments.filter((a) => a.status === 'missing').length,
      }
    : mockReadiness;

  const totalCriteria = liveAssessments ? liveAssessments.length : 7;
  const isReadyForReview = caseStatus === 'ready_for_review' || caseStatus === 'verified' || hasClarification;

  if (!hasRunAnalysis) {
    return (
      <div className="psp">
        <div className="psp-idle">
          <div className="psp-idle-icon">📄</div>
          <div className="psp-idle-title">Auth Packet</div>
          <div className="psp-idle-body">
            AuthLens will draft the authorization packet once evidence review is complete.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="psp animate-fade-in">
      <div className="psp-header">
        <span className="psp-title">Authorization Packet</span>
        {isReadyForReview ? (
          <span className="chip chip-met">Ready</span>
        ) : (
          <span className="chip chip-weak">Needs Clarification</span>
        )}
      </div>

      <div className="psp-body">
        <div className={`psp-readiness-status ${isReadyForReview ? 'psp-readiness-ready' : 'psp-readiness-pending'}`}>
          {isReadyForReview ? '✓ Ready for clinician review' : '◦ Not ready for review'}
        </div>

        <div className="psp-summary">
          <div className="psp-summary-item psp-summary-met">
            ✓ {readiness.criteria_met} of {totalCriteria} requirements supported
          </div>
          {isReadyForReview ? (
            <div className="psp-summary-item psp-summary-met">
              ✓ All clarifications resolved
            </div>
          ) : (
            <div className="psp-summary-item psp-summary-weak">
              ◦ 1 clinician clarification needed
            </div>
          )}
          <div className="psp-summary-item psp-summary-neutral">
            ✓ Minimum-necessary disclosure passed
          </div>
        </div>

        <div className="psp-detail-list">
          <div className="psp-detail-item">Policy MHP-IMG-2201 matched</div>
          <div className="psp-detail-item">{totalCriteria} criteria evaluated</div>
          <div className="psp-detail-item">Disclosure review complete</div>
          {isReadyForReview ? (
            <div className="psp-detail-item">Clarification recorded</div>
          ) : (
            <div className="psp-detail-item psp-detail-pending">1 clarification pending</div>
          )}
        </div>

        <button className="btn psp-open-btn" onClick={onOpenForm}
          style={{ background: '#f1f5f9', color: '#1e293b', border: '1px solid #cbd5e1' }}>
          View draft form
        </button>

        {/* ── Clinician Decision Section ── */}
        {isReadyForReview && !decision && (
          <div className="psp-decision-section animate-fade-in">
            <div className="psp-decision-label">
              Clinician Decision Required
            </div>
            <div className="psp-decision-sub">
              AuthLens does not submit automatically. You must review and decide below.
            </div>
            <div className="psp-decision-buttons">
              <button
                className="psp-decision-btn psp-decision-approve"
                onClick={() => setDecision('approved')}
              >
                <span>✓</span>
                <span>Approve &amp; Route to Payer</span>
              </button>
              <button
                className="psp-decision-btn psp-decision-info"
                onClick={() => setDecision('needs_info')}
              >
                <span>?</span>
                <span>Request More Information</span>
              </button>
              <button
                className="psp-decision-btn psp-decision-reject"
                onClick={() => setDecision('rejected')}
              >
                <span>✕</span>
                <span>Reject — Do Not Submit</span>
              </button>
            </div>
          </div>
        )}

        {/* ── Decision Confirmation ── */}
        {decision === 'approved' && (
          <div className="psp-decision-result psp-result-approved animate-fade-in">
            <div className="psp-result-icon">✓</div>
            <div className="psp-result-body">
              <div className="psp-result-title">Approved by clinician</div>
              <div className="psp-result-note">
                Packet routed to payer portal. Reference ID: AUTH-{new Date().getFullYear()}-0718-001.
              </div>
            </div>
            <button className="psp-result-undo" onClick={() => setDecision(null)}>Undo</button>
          </div>
        )}

        {decision === 'needs_info' && (
          <div className="psp-decision-result psp-result-info animate-fade-in">
            <div className="psp-result-icon">?</div>
            <div className="psp-result-body">
              <div className="psp-result-title">More information requested</div>
              <div className="psp-result-note">
                Case returned to intake. Additional documentation requested from care team.
              </div>
            </div>
            <button className="psp-result-undo" onClick={() => setDecision(null)}>Undo</button>
          </div>
        )}

        {decision === 'rejected' && (
          <div className="psp-decision-result psp-result-rejected animate-fade-in">
            <div className="psp-result-icon">✕</div>
            <div className="psp-result-body">
              <div className="psp-result-title">Submission rejected by clinician</div>
              <div className="psp-result-note">
                Authorization request will not be submitted. Case closed.
              </div>
            </div>
            <button className="psp-result-undo" onClick={() => setDecision(null)}>Undo</button>
          </div>
        )}

        {!isReadyForReview && (
          <div className="psp-pending-note">
            Clinician decision available after clarification is recorded.
          </div>
        )}
      </div>
    </div>
  );
}
