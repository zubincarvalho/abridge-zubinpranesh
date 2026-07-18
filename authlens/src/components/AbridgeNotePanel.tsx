import './AbridgeNotePanel.css';
import { NOTE_PHRASES } from '../data/mockCase';
import type { SourceDetail } from '../data/mockCase';

type Props = {
  hasClarification: boolean;
  onPhraseClick: (source: SourceDetail) => void;
};

function HighlightedText({
  text,
  onPhraseClick,
}: {
  text: string;
  onPhraseClick: (source: SourceDetail) => void;
}) {
  let remaining = text;
  const parts: React.ReactNode[] = [];
  let keyIdx = 0;

  while (remaining.length > 0) {
    let earliest: { index: number; phrase: (typeof NOTE_PHRASES)[0] } | null = null;

    for (const phrase of NOTE_PHRASES) {
      const idx = remaining.toLowerCase().indexOf(phrase.text.toLowerCase());
      if (idx !== -1 && (earliest === null || idx < earliest.index)) {
        earliest = { index: idx, phrase };
      }
    }

    if (earliest === null) {
      parts.push(<span key={keyIdx++}>{remaining}</span>);
      break;
    }

    if (earliest.index > 0) {
      parts.push(<span key={keyIdx++}>{remaining.slice(0, earliest.index)}</span>);
    }

    const matchedText = remaining.slice(earliest.index, earliest.index + earliest.phrase.text.length);
    const ph = earliest.phrase;
    parts.push(
      <button
        key={keyIdx++}
        className="note-highlight"
        onClick={() => onPhraseClick(ph.sourceDetail)}
        title="View linked evidence"
      >
        {matchedText}
        <span className="note-highlight-indicator">🔗</span>
      </button>
    );

    remaining = remaining.slice(earliest.index + earliest.phrase.text.length);
  }

  return <>{parts}</>;
}

export default function AbridgeNotePanel({ hasClarification, onPhraseClick }: Props) {
  return (
    <div className="abridge-panel panel">
      <div className="panel-header">
        <div className="abridge-header-left">
          <div className="abridge-logo">
            <span className="abridge-logo-a">A</span>
            <span className="abridge-logo-text">bridge</span>
          </div>
          <div>
            <div className="abridge-title">Encounter Note</div>
            <div className="abridge-subtitle">Draft · AI Generated · 07/18/2026</div>
          </div>
        </div>
        <div className="abridge-header-chips">
          <span className="chip chip-purple">AI Generated</span>
          <span className="chip chip-blue">Linked Evidence</span>
        </div>
      </div>

      <div className="note-body">
        <section className="note-section">
          <div className="note-section-label">Chief Complaint</div>
          <p className="note-text">
            <HighlightedText text="Low back pain" onPhraseClick={onPhraseClick} />
          </p>
        </section>

        <section className="note-section">
          <div className="note-section-label">History of Present Illness</div>
          <p className="note-text">
            <HighlightedText
              text={
                "47-year-old male presents with low back pain for several months. " +
                "Pain radiates down the left leg to the foot with numbness and tingling. " +
                "Worse with sitting and bending. No bowel or bladder changes. " +
                "Has tried ibuprofen with partial relief."
              }
              onPhraseClick={onPhraseClick}
            />
          </p>
        </section>

        <section className="note-section">
          <div className="note-section-label">Physical Exam</div>
          <p className="note-text">
            <HighlightedText
              text="Positive straight-leg raise on the left. Strength grossly intact."
              onPhraseClick={onPhraseClick}
            />
          </p>
        </section>

        <section className="note-section">
          <div className="note-section-label">Assessment</div>
          <p className="note-text">
            Chronic low back pain with left-sided radicular symptoms.{' '}
            <span className="icd-tag">ICD-10: M54.16</span>
          </p>
        </section>

        <section className="note-section">
          <div className="note-section-label">Plan</div>
          <ul className="note-plan-list">
            <li>
              <HighlightedText
                text="Order lumbar spine MRI without contrast."
                onPhraseClick={onPhraseClick}
              />
              {' '}<span className="pa-inline-tag">PA Required</span>
            </li>
            <li>Refer to physical therapy.</li>
            <li>Continue NSAID as needed.</li>
            <li>Follow up after imaging or sooner if worsening.</li>
          </ul>
        </section>

        {hasClarification && (
          <section className="note-section note-section--clarification animate-fade-in">
            <div className="note-section-label">
              <span className="clarification-badge">Clinician Clarification Added</span>
            </div>
            <p className="note-text note-clarification-text">
              Patient reports symptoms have persisted for over 8 weeks and completed
              six weeks of physical therapy and NSAID therapy without meaningful
              improvement. No fever, trauma, cancer history, progressive weakness,
              or bowel/bladder dysfunction reported.
            </p>
          </section>
        )}

        <div className="note-footer">
          <span className="note-footer-item">🤖 Generated by Abridge AI</span>
          <span className="note-footer-sep">·</span>
          <span className="note-footer-item">Requires clinician attestation</span>
          <span className="note-footer-sep">·</span>
          <span className="note-footer-item highlight-hint">🔗 Highlighted phrases = linked evidence</span>
        </div>
      </div>
    </div>
  );
}
