import './GapResolutionPanel.css';
import {
  CLARIFICATION_QUESTION,
  CLARIFICATION_RESPONSE,
} from '../data/mockCase';
import type { ApiClarificationQuestion } from '../api/client';

type Props = {
  hasClarification: boolean;
  onAddClarification: () => void;
  question?: ApiClarificationQuestion;
  clarificationResponse?: string;
};

export default function GapResolutionPanel({ hasClarification, onAddClarification, question: liveQuestion, clarificationResponse: liveResponse }: Props) {
  const activeQuestion = liveQuestion ?? CLARIFICATION_QUESTION;
  const activeResponse = liveResponse ?? CLARIFICATION_RESPONSE;
  const linkedCriterion = activeQuestion.criterion_ids[0] ?? 'LM-3';

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
                <div className="gap-q-text">{activeQuestion.question}</div>
                <div className="gap-q-ref">{linkedCriterion} — Completed and failed conservative treatment</div>
                <div className="gap-q-why">{activeQuestion.why_needed}</div>
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
              "{activeResponse}"
            </div>
            <div className="gap-linked-facts">
              <span className="gap-linked-fact gap-linked-fact--met">Added to note draft</span>
              <span className="gap-linked-fact gap-linked-fact--met">Linked to {linkedCriterion}</span>
              <span className="gap-linked-fact gap-linked-fact--met">Authorization packet updated</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
