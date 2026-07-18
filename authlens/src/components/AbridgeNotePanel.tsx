import './AbridgeNotePanel.css';
import { NOTE_TEXT, NOTE_HIGHLIGHTS, CLARIFICATION_RESPONSE } from '../data/mockCase';
import type { NoteHighlight } from '../data/mockCase';
import type { ApiCriterionAssessment, ApiPolicyCriterion } from '../api/client';

type Props = {
  hasClarification: boolean;
  onPhraseClick: (sourceId: string, excerpt?: string) => void;
  noteText?: string;
  noteSourceId?: string;
  assessments?: ApiCriterionAssessment[];
  criteria?: ApiPolicyCriterion[];
};

type Segment = { text: string; highlight?: NoteHighlight };

function buildSegments(text: string, globalOffset: number, highlights: NoteHighlight[]): Segment[] {
  const relevant = highlights
    .filter((h) => h.start < globalOffset + text.length && h.end > globalOffset)
    .map((h) => ({
      ...h,
      localStart: Math.max(0, h.start - globalOffset),
      localEnd: Math.min(text.length, h.end - globalOffset),
    }))
    .sort((a, b) => a.localStart - b.localStart);

  const segments: Segment[] = [];
  let cursor = 0;

  for (const h of relevant) {
    if (h.localStart > cursor) {
      segments.push({ text: text.slice(cursor, h.localStart) });
    }
    segments.push({ text: text.slice(h.localStart, h.localEnd), highlight: h });
    cursor = h.localEnd;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor) });
  }

  return segments;
}

function deriveHighlights(
  assessments: ApiCriterionAssessment[],
  criteria: ApiPolicyCriterion[],
  noteSourceId: string,
): NoteHighlight[] {
  const labelMap = Object.fromEntries(criteria.map((c) => [c.criterion_id, c.label]));
  const highlights: NoteHighlight[] = [];
  for (const a of assessments) {
    for (const ev of a.evidence) {
      if (ev.source_id === noteSourceId && ev.span) {
        highlights.push({
          id: ev.evidence_id,
          start: ev.span.start,
          end: ev.span.end,
          criterionId: a.criterion_id,
          sourceId: ev.source_id,
          label: `${a.criterion_id}: ${labelMap[a.criterion_id] ?? a.criterion_id}`,
        });
      }
    }
  }
  return highlights.sort((a, b) => a.start - b.start);
}

function Noteparagraph({
  text,
  globalOffset,
  highlights,
  onPhraseClick,
}: {
  text: string;
  globalOffset: number;
  highlights: NoteHighlight[];
  onPhraseClick: (sourceId: string, excerpt?: string) => void;
}) {
  const segments = buildSegments(text, globalOffset, highlights);

  return (
    <p className="note-text">
      {segments.map((seg, i) =>
        seg.highlight ? (
          <button
            key={i}
            className={`note-highlight note-highlight--${seg.highlight.criterionId.toLowerCase()}`}
            onClick={() => onPhraseClick(seg.highlight!.sourceId, seg.text)}
            title={seg.highlight.label}
          >
            {seg.text}
            <span className="note-highlight-indicator" aria-hidden>
              {seg.highlight.criterionId}
            </span>
          </button>
        ) : (
          <span key={i}>{seg.text}</span>
        )
      )}
    </p>
  );
}

export default function AbridgeNotePanel({ hasClarification, onPhraseClick, noteText, noteSourceId, assessments, criteria }: Props) {
  const activeNoteText = noteText ?? NOTE_TEXT;

  // Derive highlights from live assessments when available
  const highlights =
    assessments && criteria && noteSourceId
      ? deriveHighlights(assessments, criteria, noteSourceId)
      : NOTE_HIGHLIGHTS;

  // Find recorded clarification from live data
  const clarificationText = hasClarification
    ? (assessments?.flatMap((a) => a.evidence).find(
        (ev) => ev.source_type === 'clinician_clarification'
      )?.excerpt ?? CLARIFICATION_RESPONSE)
    : null;

  const paragraphs = activeNoteText.split('\n\n');
  let offset = 0;

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
            <div className="abridge-subtitle">Draft · AI Generated · 07/18/2026 · SYNTHETIC</div>
          </div>
        </div>
        <div className="abridge-header-chips">
          <span className="chip chip-purple">AI Generated</span>
          <span className="chip chip-blue">Linked Evidence</span>
        </div>
      </div>

      <div className="note-body">
        <div className="note-highlight-legend">
          <span className="legend-label">Highlighted =</span>
          <span className="legend-item legend-item--criteria">evidence cited by AuthLens</span>
          <span className="legend-sep">·</span>
          <span className="legend-hint">click to view source</span>
        </div>

        {paragraphs.map((para, i) => {
          const go = offset;
          offset += para.length + 2; // +2 for '\n\n'
          return (
            <Noteparagraph
              key={i}
              text={para}
              globalOffset={go}
              highlights={highlights}
              onPhraseClick={onPhraseClick}
            />
          );
        })}

        {hasClarification && clarificationText && (
          <section className="note-section note-section--clarification animate-fade-in">
            <div className="note-section-label">
              <span className="clarification-badge">Clinician Clarification Added</span>
            </div>
            <p className="note-text note-clarification-text">{clarificationText}</p>
          </section>
        )}

        <div className="note-footer">
          <span className="note-footer-item">Generated by Abridge AI</span>
          <span className="note-footer-sep">·</span>
          <span className="note-footer-item">Requires clinician attestation</span>
          <span className="note-footer-sep">·</span>
          <span className="note-footer-item highlight-hint">
            Highlighted phrases = evidence cited by AuthLens
          </span>
        </div>
      </div>
    </div>
  );
}
