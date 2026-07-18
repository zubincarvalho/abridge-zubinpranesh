import './GapResolutionPanel.css';
import {
  CLARIFICATION_QUESTION,
  CLARIFICATION_RESPONSE,
  ASSESSMENTS,
} from '../data/mockCase';

type Props = {
  hasClarification: boolean;
  onAddClarification: () => void;
};

export default function GapResolutionPanel({ hasClarification, onAddClarification }: Props) {
  const missingCount = ASSESSMENTS.filter((a) => a.status === 'missing').length;
  const weakCount = ASSESSMENTS.filter((a) => a.status === 'weak').length;
  const gapLabel = `${missingCount} missing, ${weakCount} weak`;

  return (
    <div className="gap-panel panel">
      <div className="panel-header">
        <span className="panel-header-title">AuthLens Point-of-Capture Clarification</span>
        {hasClarification ? (
          <span className="chip chip-met">Answered</span>
        ) : (
          <span className="chip chip-orange">{gapLabel}</span>
        )}
      </div>

      <div className="gap-body">
        <div className="gap-questions">
          <div className="gap-question-item">
            <div className="gap-q-num">q-lm3-001</div>
            <div className="gap-q-content">
              <div className="gap-q-text">{CLARIFICATION_QUESTION.question}</div>
              <span className="gap-q-ref">Re: LM-3 — Completed and failed conservative treatment</span>
              <div className="gap-q-why">{CLARIFICATION_QUESTION.why_needed}</div>
            </div>
          </div>
        </div>

        <div className="gap-action-row">
          {!hasClarification ? (
            <button className="btn btn-teal" onClick={onAddClarification}>
              <span>✚</span> Add Clinician Clarification
            </button>
          ) : (
            <div className="gap-clarification-card animate-fade-in">
              <div className="gap-clarification-header">
                <span className="gap-clarification-icon">✓</span>
                <span className="gap-clarification-title">Clinician Clarification Recorded</span>
                <span className="chip chip-met">Verified</span>
              </div>
              <div className="gap-clarification-text">
                {CLARIFICATION_RESPONSE}
              </div>
              <div className="gap-clarification-meta">
                <span>Recorded verbatim</span>
                <span>·</span>
                <span>2026-07-18T16:10:00Z</span>
                <span className="fhir-tag" style={{ marginLeft: '4px' }}>
                  source: clar-001
                </span>
              </div>
              <div className="gap-clarification-note">
                LM-3 → <strong>Met</strong> · LM-6 remains <strong>Weak</strong> (functional limitation not quantified).
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
