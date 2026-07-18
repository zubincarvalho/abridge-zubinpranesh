import './GapResolutionPanel.css';

type Props = {
  hasClarification: boolean;
  onAddClarification: () => void;
};

const QUESTIONS = [
  { id: 1, text: 'Can you confirm the symptom duration?', criterionRef: 'Symptoms > 6 weeks' },
  {
    id: 2,
    text: 'Has the patient completed at least six weeks of physical therapy, NSAIDs, or home exercise therapy without meaningful improvement?',
    criterionRef: 'Conservative therapy',
  },
  {
    id: 3,
    text: 'Any red flags such as fever, trauma, cancer history, progressive weakness, or bowel/bladder dysfunction?',
    criterionRef: 'Red-flag screen',
  },
];

const CLARIFICATION_TEXT =
  'Patient reports symptoms have persisted for over 8 weeks and completed six weeks of physical therapy and NSAID therapy without meaningful improvement. No fever, trauma, cancer history, progressive weakness, or bowel/bladder dysfunction reported.';

export default function GapResolutionPanel({ hasClarification, onAddClarification }: Props) {
  return (
    <div className="gap-panel panel">
      <div className="panel-header">
        <span className="panel-header-title">AuthLens Suggested Follow-up Questions</span>
        <span className="chip chip-orange">3 gaps identified</span>
      </div>

      <div className="gap-body">
        <div className="gap-questions">
          {QUESTIONS.map((q) => (
            <div key={q.id} className="gap-question-item">
              <div className="gap-q-num">{q.id}</div>
              <div className="gap-q-content">
                <div className="gap-q-text">{q.text}</div>
                <span className="gap-q-ref">Re: {q.criterionRef}</span>
              </div>
            </div>
          ))}
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
                <span className="gap-clarification-title">Clinician Clarification Added</span>
                <span className="chip chip-met">Verified</span>
              </div>
              <div className="gap-clarification-text">
                {CLARIFICATION_TEXT}
              </div>
              <div className="gap-clarification-meta">
                <span>Kelsey Morris, MD</span>
                <span>·</span>
                <span>07/18/2026 · Today's encounter</span>
                <span className="fhir-tag" style={{ marginLeft: '4px' }}>type: clarification</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
