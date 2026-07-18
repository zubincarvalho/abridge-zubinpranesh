import './GapResolutionPanel.css';
import {
  CLARIFICATION_QUESTION,
  CLARIFICATION_RESPONSE,
} from '../data/mockCase';

type Props = {
  hasClarification: boolean;
  onAddClarification: () => void;
};

export default function GapResolutionPanel({ hasClarification, onAddClarification }: Props) {
  return (
    <div className="gap-panel panel">
      <div className="panel-header">
        <span className="panel-header-title">Clarification</span>
        {hasClarification ? (
          <span className="chip chip-met">Recorded</span>
        ) : (
          <span className="chip chip-weak">1 item</span>
        )}
      </div>

      <div className="gap-body">
        {!hasClarification ? (
          <>
            <div className="gap-question-item">
              <div className="gap-q-content">
                <div className="gap-q-text">{CLARIFICATION_QUESTION.question}</div>
                <div className="gap-q-ref">LM-3 — Completed and failed conservative treatment</div>
                <div className="gap-q-why">{CLARIFICATION_QUESTION.why_needed}</div>
              </div>
            </div>
            <div className="gap-action-row">
              <button className="btn btn-primary gap-btn-primary" onClick={onAddClarification}>
                Record response
              </button>
              <button className="btn btn-ghost gap-btn-sec">Not completed</button>
              <button className="btn btn-ghost gap-btn-sec">Unknown</button>
            </div>
          </>
        ) : (
          <div className="gap-clarification-card animate-fade-in">
            <div className="gap-clarification-header">
              <span className="gap-clarification-icon">✓</span>
              <span className="gap-clarification-title">Clarification recorded</span>
              <div className="gap-clarification-links">
                <button className="gap-link-btn">View source</button>
                <span className="gap-link-sep">·</span>
                <button className="gap-link-btn">Undo</button>
              </div>
            </div>
            <div className="gap-clarification-text">
              "{CLARIFICATION_RESPONSE}"
            </div>
            <div className="gap-linked-facts">
              <span className="gap-linked-fact gap-linked-fact--met">Added to note draft</span>
              <span className="gap-linked-fact gap-linked-fact--met">Linked to LM-3</span>
              <span className="gap-linked-fact gap-linked-fact--met">Authorization packet updated</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
