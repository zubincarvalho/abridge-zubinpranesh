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

export default function PacketStatusPanel({ hasRunAnalysis, hasClarification, onOpenForm, assessments: liveAssessments, caseStatus }: Props) {
  const mockReadiness = hasClarification ? READINESS_POST_CLARIFICATION : READINESS_INITIAL;

  // Derive readiness counts from live assessments or fall back to mock
  const readiness = liveAssessments
    ? {
        criteria_met:     liveAssessments.filter((a) => a.status === 'met').length,
        criteria_weak:    liveAssessments.filter((a) => a.status === 'weak').length,
        criteria_missing: liveAssessments.filter((a) => a.status === 'missing').length,
      }
    : mockReadiness;

  const totalCriteria = liveAssessments ? liveAssessments.length : 7;
  const isReadyForReview = caseStatus === 'ready_for_review' || caseStatus === 'verified';

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
        {hasClarification ? (
          <span className="chip chip-met">Updated</span>
        ) : (
          <span className="chip chip-weak">Draft</span>
        )}
      </div>
      <div className="psp-body">
        <div className={`psp-readiness-status ${(hasClarification || isReadyForReview) ? 'psp-readiness-ready' : 'psp-readiness-pending'}`}>
          {(hasClarification || isReadyForReview) ? 'Ready for clinician review' : 'Not ready for review'}
        </div>

        <div className="psp-summary">
          <div className="psp-summary-item psp-summary-met">
            ✓ {readiness.criteria_met} of {totalCriteria} requirements supported
          </div>
          {hasClarification ? (
            <div className="psp-summary-item psp-summary-met">
              ✓ Clarification linked to LM-3
            </div>
          ) : (
            <div className="psp-summary-item psp-summary-weak">
              ◦ 1 clinician clarification needed
            </div>
          )}
          <div className="psp-summary-item psp-summary-neutral">
            ✓ Minimum-necessary review passed
          </div>
        </div>

        <div className="psp-detail-list">
          <div className="psp-detail-item">Policy matched</div>
          <div className="psp-detail-item">7 criteria evaluated</div>
          <div className="psp-detail-item">Disclosure review complete</div>
          {hasClarification ? (
            <div className="psp-detail-item">Clarification recorded</div>
          ) : (
            <div className="psp-detail-item psp-detail-pending">1 clarification pending</div>
          )}
        </div>

        {(hasClarification || isReadyForReview) ? (
          <div className="psp-btn-group">
            <button className="btn btn-primary psp-open-btn" onClick={onOpenForm}>
              Review packet
            </button>
            <button className="btn btn-ghost psp-route-btn">
              Route for review
            </button>
          </div>
        ) : (
          <button className="btn btn-primary psp-open-btn" onClick={onOpenForm}>
            Open draft
          </button>
        )}
      </div>
    </div>
  );
}
